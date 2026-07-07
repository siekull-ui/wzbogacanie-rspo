import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re

# Ustawienia strony
st.set_page_config(page_title="Wyszukiwarka RSPO CRM", layout="wide")
st.title("🏫 Auto-Uzupełniacz Danych CRM z RSPO")
st.write("Wgraj eksport z CRM (lista szans sprzedaży), a algorytm automatycznie uzupełni braki i poprawi adresy.")

# Funkcja czyszcząca tekst dla lepszego dopasowania
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

# Wczytywanie bazy (plik musi nazywać się baza.csv)
@st.cache_data
def load_baza():
    try:
        df = pd.read_csv("baza.csv", sep=None, engine='python', encoding='utf-8')
        cols = ['Nazwa', 'Adres full', 'Imię i nazwisko dyrektora']
        dostepne = [c for c in cols if c in df.columns]
        
        df['Do_wyszukiwania'] = df[dostepne].fillna('').astype(str).agg(' '.join, axis=1)
        df['Znormalizowane_wyszukiwanie'] = df['Do_wyszukiwania'].apply(normalizuj)
        return df
    except Exception as e:
        st.error(f"Nie znaleziono pliku baza.csv lub wystąpił błąd: {e}")
        return None

baza = load_baza()

if baza is not None:
    # Wgrywanie pliku użytkownika
    uploaded_file = st.file_uploader("📂 Wgraj swój eksport deali (Excel lub CSV)", type=["xlsx", "csv"])

    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            df_user = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df_user = pd.read_excel(uploaded_file)

        st.markdown("### Podgląd wgranego pliku:")
        st.dataframe(df_user.head(3))

        # Zaczynamy automatyczną magię od razu po wciśnięciu przycisku
        if st.button("Uruchom automatyczne uzupełnianie", type="primary"):
            with st.spinner("Przeszukuję bazę i uzupełniam luki... To może chwilę potrwać."):
                df_wynik = df_user.copy()
                
                # Słownik do szybkiego wyszukiwania
                slownik_bazy = baza['Znormalizowane_wyszukiwanie'].to_dict()
                progress_bar = st.progress(0)
                total = len(df_wynik)
                
                # Definicja kolumn z Twojego pliku CRM
                col_tytul = 'Szansa sprzedaży - Tytuł'
                col_adres = 'Organizacja - Adres'
                col_rspo = 'Organizacja - Numer RSPO'
                col_dyr = 'Organizacja - Imię i nazwisko dyrektora'
                col_email = 'Organizacja - E-mail'
                col_www = 'Organizacja - Strona internetowa'
                col_uczniowie = 'Szansa sprzedaży - Liczba uczniów'
                
                # Zabezpieczenie: jeśli jakiejś kolumny brakuje, to ją dodajemy
                for c in [col_rspo, col_dyr, col_adres, col_email, col_www, col_uczniowie]:
                    if c not in df_wynik.columns:
                        df_wynik[c] = ""
                        
                df_wynik['Status_Dopasowania'] = "Brak"

                for idx, row in df_wynik.iterrows():
                    # Tworzymy frazę wyszukiwania: Nazwa Szkoły + Adres
                    nazwa = str(row.get(col_tytul, '')) if pd.notna(row.get(col_tytul)) else ''
                    adres_org = str(row.get(col_adres, '')) if pd.notna(row.get(col_adres)) else ''
                    
                    fraza = nazwa + " " + adres_org
                    fraza_znormalizowana = normalizuj(fraza)

                    if fraza_znormalizowana.strip():
                        # Używamy fuzz.token_set_ratio, które świetnie radzi sobie z odwróconą kolejnością słów
                        match = process.extractOne(fraza_znormalizowana, slownik_bazy, scorer=fuzz.token_set_ratio)
                        
                        # Próg pewności na 75, by nie wciągać przypadkowych szkół
                        if match and match[1] >= 75:  
                            dopasowany_idx = match[2]
                            dopasowany_wiersz = baza.loc[dopasowany_idx]

                            # 1. Numer RSPO -> Nadpisujemy
                            if pd.notna(dopasowany_wiersz.get('Numer RSPO')):
                                df_wynik.at[idx, col_rspo] = dopasowany_wiersz['Numer RSPO']
                                
                            # 2. Adres -> Nadpisujemy (poprawiamy na czysty adres RSPO)
                            if pd.notna(dopasowany_wiersz.get('Adres full')):
                                df_wynik.at[idx, col_adres] = dopasowany_wiersz['Adres full']

                            # 3. Dyrektor -> Uzupełniamy tylko LUKI
                            if pd.isna(row.get(col_dyr)) or str(row.get(col_dyr)).strip() == "":
                                if pd.notna(dopasowany_wiersz.get('Imię i nazwisko dyrektora')):
                                    df_wynik.at[idx, col_dyr] = dopasowany_wiersz['Imię i nazwisko dyrektora']
                                    
                            # 4. E-mail -> Uzupełniamy tylko LUKI
                            if pd.isna(row.get(col_email)) or str(row.get(col_email)).strip() == "":
                                if pd.notna(dopasowany_wiersz.get('E-mail')):
                                    df_wynik.at[idx, col_email] = dopasowany_wiersz['E-mail']
                                    
                            # 5. WWW -> Uzupełniamy tylko LUKI
                            if pd.isna(row.get(col_www)) or str(row.get(col_www)).strip() == "":
                                if pd.notna(dopasowany_wiersz.get('Strona www')):
                                    df_wynik.at[idx, col_www] = dopasowany_wiersz['Strona www']
                                    
                            # 6. Liczba uczniów -> Uzupełniamy tylko LUKI
                            if pd.isna(row.get(col_uczniowie)) or str(row.get(col_uczniowie)).strip() == "":
                                if pd.notna(dopasowany_wiersz.get('Liczba uczniów')):
                                    df_wynik.at[idx, col_uczniowie] = dopasowany_wiersz['Liczba uczniów']
                                    
                            df_wynik.at[idx, 'Status_Dopasowania'] = f"✅ Znaleziono ({match[1]}%)"

                    progress_bar.progress((idx + 1) / total)

                st.success("Analiza zakończona! Dane uzupełnione.")
                st.dataframe(df_wynik.head(15))

                # Generowanie Excela do pobrania
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
