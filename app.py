import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Wyszukiwarka RSPO CRM", layout="wide")
st.title("🏫 Auto-Uzupełniacz Danych CRM")
st.write("Wersja niezawodna: Szuka najlepszego dopasowania na podstawie połączonej nazwy i adresu.")

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
        # Wymuszamy dtype=str, żeby zabić błędy typowania Pandas
        try:
            df = pd.read_csv("baza.csv", sep=',', encoding='utf-8', dtype=str)
        except Exception:
            df = pd.read_csv("baza.csv", sep=';', encoding='utf-8', dtype=str)
            
        df['Znormalizowana_Nazwa'] = df['Nazwa'].apply(normalizuj)
        df['Znormalizowany_Adres'] = df['Adres full'].apply(normalizuj)
        # Łączymy w jeden solidny blok do szukania
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
            try:
                df_user = pd.read_csv(uploaded_file, sep=',', dtype=str)
            except Exception:
                uploaded_file.seek(0)
                df_user = pd.read_csv(uploaded_file, sep=';', dtype=str)
        else:
            df_user = pd.read_excel(uploaded_file, dtype=str)

        st.markdown("### 1. Podgląd wgranego pliku:")
        st.dataframe(df_user.head(3))

        kolumny_user = df_user.columns.tolist()

        # --- PANEL KONTROLNY UŻYTKOWNIKA ---
        st.markdown("### 2. Mapowanie Danych")
        col1, col2 = st.columns(2)
        with col1:
            col_tytul = st.selectbox("📌 Wybierz kolumnę z NAZWĄ szkoły:", kolumny_user, index=0)
        with col2:
            domyslny_adres = 1 if len(kolumny_user) > 1 else 0
            for i, kol in enumerate(kolumny_user):
                if "adres" in kol.lower():
                    domyslny_adres = i
                    break
            col_adres = st.selectbox("📍 Wybierz kolumnę z ADRESEM szkoły:", kolumny_user, index=domyslny_adres)

        if st.button("🚀 Szukaj RSPO", type="primary"):
            with st.spinner("Szukam najbardziej prawdopodobnych dopasowań..."):
                df_wynik = df_user.copy()
                
                # Zabezpieczenie przed TypeError (konwersja na czysty object)
                df_wynik = df_wynik.astype(object)
                
                slownik_bazy = baza['Do_wyszukiwania'].to_dict()
                progress_bar = st.progress(0)
                total = len(df_wynik)
                
                # Tworzymy puste kolumny i wymuszamy typ object
                nowe_kolumny = [
                    'RSPO - Numer', 'RSPO - Adres Poprawny', 'RSPO - Dyrektor', 
                    'RSPO - E-mail', 'RSPO - WWW', 'RSPO - Uczniowie', 'Pewność Dopasowania'
                ]
                for c in nowe_kolumny:
                    df_wynik[c] = ""
                    df_wynik[c] = df_wynik[c].astype(object)

                for idx, row in df_wynik.iterrows():
                    nazwa_crm = str(row[col_tytul]) if pd.notna(row[col_tytul]) else ''
                    adres_crm = str(row[col_adres]) if pd.notna(row[col_adres]) else ''
                    
                    nazwa_crm = nazwa_crm.replace("Szansa sprzedaży", "").strip()
                    
                    fraza = nazwa_crm + " " + adres_crm
                    fraza_znormalizowana = normalizuj(fraza)

                    if fraza_znormalizowana.strip():
                        # Znajduje jedno najlepsze dopasowanie ignorując kolejność słów
                        match = process.extractOne(fraza_znormalizowana, slownik_bazy, scorer=fuzz.token_set_ratio)
                        
                        if match:
                            najlepszy_wynik = match[1]
                            dopasowany_idx = match[2]
                            dopasowany_wiersz = baza.loc[dopasowany_idx]

                            # Wymuszamy zrzutowanie wyniku na string (str()), żeby zablokować TypeError z Pandas
                            df_wynik.at[idx, 'RSPO - Numer'] = str(dopasowany_wiersz.get('Numer RSPO', ''))
                            df_wynik.at[idx, 'RSPO - Adres Poprawny'] = str(dopasowany_wiersz.get('Adres full', ''))
                            df_wynik.at[idx, 'RSPO - Dyrektor'] = str(dopasowany_wiersz.get('Imię i nazwisko dyrektora', ''))
                            df_wynik.at[idx, 'RSPO - E-mail'] = str(dopasowany_wiersz.get('E-mail', ''))
                            df_wynik.at[idx, 'RSPO - WWW'] = str(dopasowany_wiersz.get('Strona www', ''))
                            df_wynik.at[idx, 'RSPO - Uczniowie'] = str(dopasowany_wiersz.get('Liczba uczniów', ''))
                            df_wynik.at[idx, 'Pewność Dopasowania'] = f"{najlepszy_wynik}%"

                    progress_bar.progress((idx + 1) / total)

                st.success("Analiza zakończona!")
                # Wyświetlamy tylko kluczowe kolumny do weryfikacji wzrokowej
                st.dataframe(df_wynik[[col_tytul, col_adres, 'RSPO - Numer', 'RSPO - Adres Poprawny', 'Pewność Dopasowania']].head(20))

                # --- EXPORT ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_wynik.to_excel(writer, index=False, sheet_name='Uzupełnione')
                gotowy_plik = output.getvalue()

                st.download_button(
                    label="📥 Pobierz zaktualizowany plik Excel",
                    data=gotowy_plik,
                    file_name="proste_uzupelnienie_rspo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
