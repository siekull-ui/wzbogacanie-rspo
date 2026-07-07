import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re

# Ustawienia strony
st.set_page_config(page_title="Wyszukiwarka RSPO", layout="wide")
st.title("🏫 Wyszukiwarka Danych Szkół RSPO")
st.write("Wgraj plik, wskaż kolumny z danymi i pobierz uzupełnionego Excela.")

# Funkcja czyszcząca tekst (żeby łatwiej było parować np. SP = Szkoła Podstawowa)
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

# Wczytywanie bazy RSPO (cache, żeby działało szybko)
@st.cache_data
def load_baza():
    try:
        df = pd.read_csv("baza_rspo.csv", sep=None, engine='python')
        # Łączymy dane do szukania w jeden ciąg
        cols = ['Nazwa', 'Miejscowość', 'Ulica', 'Numer budynku', 'Dyrektor']
        dostepne = [c for c in cols if c in df.columns]
        
        df['Do_wyszukiwania'] = df[dostepne].fillna('').astype(str).agg(' '.join, axis=1)
        df['Znormalizowane_wyszukiwanie'] = df['Do_wyszukiwania'].apply(normalizuj)
        return df
    except Exception as e:
        st.error(f"Nie znaleziono pliku baza_rspo.csv lub wystąpił błąd: {e}")
        return None

baza = load_baza()

if baza is not None:
    # Wgrywanie pliku
    uploaded_file = st.file_uploader("📂 Wgraj swój plik (Excel lub CSV)", type=["xlsx", "csv"])

    if uploaded_file:
        # Odczyt pliku użytkownika
        if uploaded_file.name.endswith('.csv'):
            df_user = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df_user = pd.read_excel(uploaded_file)

        st.markdown("### Podgląd Twojego pliku:")
        st.dataframe(df_user.head(3))

        # Wybór kolumn do wyszukiwania
        kolumny = df_user.columns.tolist()
        wybrane_kolumny = st.multiselect(
            "Wybierz kolumny, z których mam złożyć frazę do szukania (np. Nazwa szkoły, Adres, Dyrektor):", 
            kolumny
        )

        if wybrane_kolumny:
            if st.button("Szukaj dopasowań w RSPO", type="primary"):
                with st.spinner("Przeszukuję bazę..."):
                    df_wynik = df_user.copy()
                    
                    # Te kolumny dociągamy z pliku bazy (MUSZĄ się tak nazywać w Twoim baza_rspo.csv)
                    kolumny_rspo = [
                        'Numer RSPO', 'Miejscowość', 'Ulica', 'Numer budynku', 
                        'Dyrektor', 'Strona www', 'E-mail', 'Telefon', 'Liczba uczniów'
                    ]
                    
                    # Tworzymy puste kolumny w pliku wynikowym
                    df_wynik['Pewność_dopasowania_%'] = 0
                    for col in kolumny_rspo:
                        df_wynik[f'RSPO_{col}'] = ""

                    # Przygotowanie słownika do szybkiego szukania
                    slownik_bazy = baza['Znormalizowane_wyszukiwanie'].to_dict()
                    progress_bar = st.progress(0)
                    total = len(df_wynik)

                    # Główna pętla wyszukiwania
                    for idx, row in df_wynik.iterrows():
                        # Kleimy dane użytkownika z wybranych kolumn
                        fraza = " ".join([str(row[col]) for col in wybrane_kolumny if pd.notna(row[col])])
                        fraza_znormalizowana = normalizuj(fraza)

                        if fraza_znormalizowana:
                            # token_set_ratio super radzi sobie z wyrazami w różnej kolejności i "śmieciami" w nazwie
                            match = process.extractOne(fraza_znormalizowana, slownik_bazy, scorer=fuzz.token_set_ratio)
                            
                            if match:
                                pewnosc = match[1]
                                dopasowany_idx = match[2]
                                dopasowany_wiersz = baza.loc[dopasowany_idx]

                                df_wynik.at[idx, 'Pewność_dopasowania_%'] = pewnosc
                                for col in kolumny_rspo:
                                    if col in baza.columns:
                                        df_wynik.at[idx, f'RSPO_{col}'] = dopasowany_wiersz[col]

                        # Pasek postępu
                        progress_bar.progress((idx + 1) / total)

                    st.success("Analiza zakończona!")
                    st.dataframe(df_wynik.head(10))

                    # Generowanie pliku do pobrania
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_wynik.to_excel(writer, index=False, sheet_name='Wyniki')
                    gotowy_plik = output.getvalue()

                    st.download_button(
                        label="📥 Pobierz uzupełniony plik Excel",
                        data=gotowy_plik,
                        file_name="uzupelnione_dane_rspo.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
