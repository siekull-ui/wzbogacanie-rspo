import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Wyszukiwarka RSPO CRM", layout="wide")
st.title("🏫 Auto-Uzupełniacz Danych CRM z RSPO")
st.write("Wgraj eksport z CRM (lista szans sprzedaży). Algorytm rygorystycznie weryfikuje adresy, uzupełnia braki i odrzuca dopasowania poniżej 80%.")

# --- FUNKCJE POMOCNICZE ---
def normalizuj(tekst):
    if pd.isna(tekst): return ""
    tekst = str(tekst).lower()
    zamiany = {
        r'\bsp\b': 'szkoła podstawowa', r'\bzs\b': 'zespół szkół', r'\blo\b': 'liceum ogólnokształcące',
        r'\bzso\b': 'zespół szkół ogólnokształcących', r'\bzsz\b': 'zespół szkół zawodowych'
    }
    for wzorzec, zamiennik in zamiany.items():
        tekst = re.sub(wzorzec, zamiennik, tekst)
    tekst = re.sub(r'[^\w\s]', ' ', tekst)
    return re.sub(r'\s+', ' ', tekst).strip()

@st.cache_data
def load_baza():
    try:
        df = pd.read_csv("baza.csv", sep=None, engine='python', encoding='utf-8')
        # Zapisujemy wyczyszczone wersje kolumn, żeby nie robić tego w locie dla 20k wierszy
        df['Znormalizowana_Nazwa'] = df['Nazwa'].apply(normalizuj)
        df['Znormalizowany_Adres'] = df['Adres full'].apply(normalizuj)
        # Połączona fraza tylko do pierwszego, szybkiego odsiewu
        df['Do_wyszukiwania'] = df['Znormalizowana_Nazwa'] + " " + df['Znormalizowany_Adres']
        
        return df
    except Exception as e:
        st.error(f"Nie znaleziono pliku baza.csv lub wystąpił błąd: {e}")
        return None

baza = load_baza()

# --- GŁÓWNA LOGIKA ---
if baza is not None:
    uploaded_file = st.file_uploader("📂 Wgraj swój eksport deali (Excel lub CSV)", type=["xlsx", "csv"])

    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            df_user = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df_user = pd.read_excel(uploaded_file)

        st.markdown("### Podgląd wgranego pliku:")
        st.dataframe(df_user.head(3))

        if st.button("Uruchom automatyczne uzupełnianie", type="primary"):
            with st.spinner("Przeszukuję bazę, weryfikuję adresy i uzupełniam luki..."):
                df_wynik = df_user.copy()
                
                slownik_bazy = baza['Do_wyszukiwania'].to_dict()
                progress_bar = st.progress(0)
                total = len(df_wynik)
                
                # Stałe nazwy kolumn
                col_tytul = 'Szansa sprzedaży - Tytuł'
                col_adres = 'Organizacja - Adres'
                col_rspo = 'Organizacja - Numer RSPO'
                col_dyr = 'Organizacja - Imię i nazwisko dyrektora'
                col_email = 'Organizacja - E-mail'
                col_www = 'Organizacja - Strona internetowa'
                col_uczniowie = 'Szansa sprzedaży - Liczba uczniów'
                
                # Dodawanie brakujących kolumn
                for c in [col_rspo, col_dyr, col_adres, col_email, col_www, col_uczniowie]:
                    if c not in df_wynik.columns:
                        df_wynik[c] = ""
                        
                df_wynik['Status_Dopasowania'] = "Brak"

                for idx, row in df_wynik.iterrows():
                    nazwa_crm = str(row.get(col_tytul, '')) if pd.notna(row.get(col_tytul)) else ''
                    adres_crm = str(row.get(col_adres, '')) if pd.notna(row.get(col_adres)) else ''
                    
                    fraza = nazwa_crm + " " + adres_crm
                    fraza_znormalizowana = normalizuj(fraza)

                    if fraza_znormalizowana.strip():
                        # 1. Pobieramy 5 najlepszych kandydatów (szybki odsiew)
                        kandydaci = process.extract(fraza_znormalizowana, slownik_bazy, limit=5, scorer=fuzz.token_set_ratio)
                        
                        najlepszy_kandydat_idx = None
                        najlepszy_wynik = 0
                        
                        for tekst_kandydata, wynik_wstepny, idx_bazy in kandydaci:
                            wiersz_bazy = baza.loc[idx_bazy]
                            
                            # 2. Rygorystyczna weryfikacja krzyżowa (Nazwa vs Nazwa, Adres vs Adres)
                            znorm_nazwa_crm = normalizuj(nazwa_crm)
                            znorm_adres_crm = normalizuj(adres_crm)
                            
                            score_nazwa = fuzz.token_set_ratio(znorm_nazwa_crm, wiersz_bazy['Znormalizowana_Nazwa'])
                            
                            if znorm_adres_crm.strip() != "":
                                score_adres = fuzz.token_set_ratio(znorm_adres_crm, wiersz_bazy['Znormalizowany_Adres'])
                                # Adres i nazwa ważą po 50%
                                wynik_ostateczny = (score_nazwa * 0.5) + (score_adres * 0.5)
                            else:
                                # Jak w CRM nie ma adresu, ufamy samej nazwie
                                wynik_ostateczny = score_nazwa
                                
                            if wynik_ostateczny > najlepszy_wynik:
                                najlepszy_wynik = wynik_ostateczny
                                najlepszy_kandydat_idx = idx_bazy
                        
                        # 3. Akceptacja tylko wyników >= 80%
                        if najlepszy_kandydat_idx is not None and najlepszy_wynik >= 80:  
                            dopasowany_wiersz = baza.loc[najlepszy_kandydat_idx]

                            # Nadpisujemy Numer RSPO i Adres
                            if pd.notna(dopasowany_wiersz.get('Numer RSPO')):
                                df_wynik.at[idx, col_rspo] = dopasowany_wiersz['Numer RSPO']
                                
                            if pd.notna(dopasowany_wiersz.get('Adres full')):
                                df_wynik.at[idx, col_adres] = dopasowany_wiersz['Adres full']

                            # Uzupełniamy tylko PUSTE pola w reszcie kolumn
                            if pd.isna(row.get(col_dyr)) or str(row.get(col_dyr)).strip() == "":
                                if pd.notna(dopasowany_wiersz.get('Imię i nazwisko dyrektora')):
                                    df_wynik.at[idx, col_dyr] = dopasowany_wiersz['Imię i nazwisko dyrektora']
                                    
                            if pd.isna(row.get(col_email)) or str(row.get(col_email)).strip() == "":
                                if pd.notna(dopasowany_wiersz.get('E-mail')):
                                    df_wynik.at[idx, col_email] = dopasowany_wiersz['E-mail']
                                    
                            if pd.isna(row.get(col_www)) or str(row.get(col_www)).strip() == "":
                                if pd.notna(dopasowany_wiersz.get('Strona www')):
                                    df_wynik.at[idx, col_www] = dopasowany_wiersz['Strona www']
                                    
                            if pd.isna(row.get(col_uczniowie)) or str(row.get(col_uczniowie)).strip() == "":
                                if pd.notna(dopasowany_wiersz.get('Liczba uczniów')):
                                    df_wynik.at[idx, col_uczniowie] = dopasowany_wiersz['Liczba uczniów']
                                    
                            df_wynik.at[idx, 'Status_Dopasowania'] = f"✅ Znaleziono ({round(najlepszy_wynik)}%)"
                        else:
                            df_wynik.at[idx, 'Status_Dopasowania'] = f"❌ Odrzucono (Max {round(najlepszy_wynik)}%)"

                    progress_bar.progress((idx + 1) / total)

                st.success("Analiza zakończona! Dane uzupełnione.")
                st.dataframe(df_wynik.head(15))

                # --- EXPORT ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_wynik.to_excel(writer, index=False, sheet_name='Zaktualizowane')
                gotowy_plik = output.getvalue()

                st.download_button(
                    label="📥 Pobierz zaktualizowany plik Excel",
                    data=gotowy_plik,
                    file_name="uzupelnione_deale_crm.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
