import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Wyszukiwarka RSPO CRM", layout="wide")
st.title("🏫 Auto-Uzupełniacz Danych CRM (Rygorystyczny Adres)")
st.write("Wgraj eksport z CRM. System weryfikuje osobno NAZWĘ i ADRES. Jeśli adres z CRM nie pokrywa się z RSPO, dopasowanie jest odrzucane, zapobiegając błędom lokalizacyjnym.")

# --- FUNKCJE POMOCNICZE ---
def normalizuj(tekst):
    if pd.isna(tekst): return ""
    tekst = str(tekst).lower()
    zamiany = {
        r'\bsp\b': 'szkoła podstawowa', r'\bzs\b': 'zespół szkół', r'\blo\b': 'liceum ogólnokształcące',
        r'\bzso\b': 'zespół szkół ogólnokształcących', r'\bzsz\b': 'zespół szkół zawodowych',
        r'\bgmina\b': '', r'\bui\.\b': '', r'\bulica\b': '', r'\bul\.\b': ''
    }
    for wzorzec, zamiennik in zamiany.items():
        tekst = re.sub(wzorzec, zamiennik, tekst)
    tekst = re.sub(r'[^\w\s]', ' ', tekst)
    return re.sub(r'\s+', ' ', tekst).strip()

@st.cache_data
def load_baza():
    try:
        df = pd.read_csv("baza.csv", sep=None, engine='python', encoding='utf-8')
        
        # Przygotowujemy osobne, czyste kolumny dla nazwy i adresu
        df['Znormalizowana_Nazwa'] = df['Nazwa'].apply(normalizuj)
        df['Znormalizowany_Adres'] = df['Adres full'].apply(normalizuj)
        
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

        if st.button("🚀 Uruchom rygorystyczne dopasowanie", type="primary"):
            with st.spinner("Przeszukuję bazę z restrykcyjnym sprawdzaniem adresów..."):
                df_wynik = df_user.copy()
                
                # Słownik do szybkiego wyszukiwania nazw
                slownik_nazw = baza['Znormalizowana_Nazwa'].to_dict()
                
                progress_bar = st.progress(0)
                total = len(df_wynik)
                
                # Stałe nazwy kolumn z CRM
                col_tytul = 'Szansa sprzedaży - Tytuł'
                col_adres = 'Organizacja - Adres'
                col_rspo = 'Organizacja - Numer RSPO'
                col_dyr = 'Organizacja - Imię i nazwisko dyrektora'
                col_email = 'Organizacja - E-mail'
                col_www = 'Organizacja - Strona internetowa'
                col_uczniowie = 'Szansa sprzedaży - Liczba uczniów'
                
                for c in [col_rspo, col_dyr, col_adres, col_email, col_www, col_uczniowie]:
                    if c not in df_wynik.columns:
                        df_wynik[c] = ""
                        
                df_wynik['Status_Dopasowania'] = "Brak"
                df_wynik['Szczegóły_Błędu'] = "" # Dodatkowa kolumna do diagnozy

                for idx, row in df_wynik.iterrows():
                    nazwa_crm = str(row.get(col_tytul, '')) if pd.notna(row.get(col_tytul)) else ''
                    adres_crm = str(row.get(col_adres, '')) if pd.notna(row.get(col_adres)) else ''
                    
                    nazwa_crm = nazwa_crm.replace("Szansa sprzedaży", "").strip()
                    
                    znorm_nazwa_crm = normalizuj(nazwa_crm)
                    znorm_adres_crm = normalizuj(adres_crm)

                    if znorm_nazwa_crm.strip():
                        # KROK 1: Pobierz 15 szkół z najbardziej podobną NAZWĄ
                        kandydaci = process.extract(znorm_nazwa_crm, slownik_nazw, limit=15, scorer=fuzz.token_set_ratio)
                        
                        najlepszy_idx = None
                        najlepszy_wynik_nazwy = 0
                        
                        powod_odrzucenia = "Nie znaleziono podobnej nazwy"

                        for kandydat_nazwa, wynik_nazwy, bazy_idx in kandydaci:
                            wiersz_bazy = baza.loc[bazy_idx]
                            znorm_adres_bazy = str(wiersz_bazy['Znormalizowany_Adres'])
                            
                            # KROK 2: Restrykcyjna weryfikacja ADRESU (Tylko jeśli jest podany w CRM)
                            if znorm_adres_crm.strip() != "":
                                # Używamy token_set_ratio, więc zignoruje przecinki, ale "Bytom" vs "Kraków" da bardzo niski wynik
                                zgodnosc_adresu = fuzz.token_set_ratio(znorm_adres_crm, znorm_adres_bazy)
                                
                                # HARD LIMIT: Adres musi zgadzać się w min. 85%
                                if zgodnosc_adresu < 85:
                                    powod_odrzucenia = f"Adres odrzucony (zgodność {zgodnosc_adresu}%)"
                                    continue # Przerywamy dla tej szkoły, sprawdzamy następną z listy 15
                            
                            # KROK 3: Szkoła przeszła test adresu (lub CRM nie miał adresu). 
                            # Zapisujemy najlepszy wynik nazwy.
                            # Hard limit dla nazwy: 80%
                            if wynik_nazwy >= 80 and wynik_nazwy > najlepszy_wynik_nazwy:
                                najlepszy_wynik_nazwy = wynik_nazwy
                                najlepszy_idx = bazy_idx
                        
                        # KROK 4: Zapisywanie danych do pliku
                        if najlepszy_idx is not None:  
                            dopasowany_wiersz = baza.loc[najlepszy_idx]

                            if pd.notna(dopasowany_wiersz.get('Numer RSPO')):
                                df_wynik.at[idx, col_rspo] = dopasowany_wiersz['Numer RSPO']
                            if pd.notna(dopasowany_wiersz.get('Adres full')):
                                df_wynik.at[idx, col_adres] = dopasowany_wiersz['Adres full']

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
                                    
                            df_wynik.at[idx, 'Status_Dopasowania'] = f"✅ Znaleziono (Zgodność: {najlepszy_wynik_nazwy}%)"
                        else:
                            df_wynik.at[idx, 'Status_Dopasowania'] = "❌ Odrzucono"
                            df_wynik.at[idx, 'Szczegóły_Błędu'] = powod_odrzucenia

                    progress_bar.progress((idx + 1) / total)

                st.success("Analiza zakończona! Błędy lokalizacyjne zostały zablokowane.")
                st.dataframe(df_wynik[['Szansa sprzedaży - Tytuł', 'Organizacja - Adres', 'Status_Dopasowania', 'Szczegóły_Błędu']].head(20))

                # --- EXPORT ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_wynik.to_excel(writer, index=False, sheet_name='Zaktualizowane')
                gotowy_plik = output.getvalue()

                st.download_button(
                    label="📥 Pobierz zaktualizowany plik Excel",
                    data=gotowy_plik,
                    file_name="uzupelnione_deale_rygorystyczne.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
