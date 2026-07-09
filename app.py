import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Wyszukiwarka RSPO CRM", layout="wide")
st.title("🏫 Auto-Uzupełniacz Danych CRM")
st.write("Wersja In-Place: Aktualizuje oryginalne kolumny bez zmiany struktury pliku. Ignoruje wpisy urzędowe.")

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
        try:
            df = pd.read_csv("baza.csv", sep=',', encoding='utf-8', dtype=str)
        except Exception:
            df = pd.read_csv("baza.csv", sep=';', encoding='utf-8', dtype=str)
            
        df['Znormalizowana_Nazwa'] = df['Nazwa'].apply(normalizuj)
        df['Znormalizowany_Adres'] = df['Adres full'].apply(normalizuj)
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

        # --- AUTO-DETEKCJA KOLUMN DOCELOWYCH W TWOIM PLIKU ---
        # Skrypt szuka odpowiednich kolumn w Twoim pliku, by nie zmieniać ich nazw ani kolejności
        col_rspo = next((c for c in kolumny_user if 'rspo' in c.lower()), None)
        col_dyr = next((c for c in kolumny_user if 'dyrektor' in c.lower()), None)
        col_email = next((c for c in kolumny_user if 'mail' in c.lower()), None)
        col_www = next((c for c in kolumny_user if 'stron' in c.lower() or 'www' in c.lower()), None)
        col_uczniowie = next((c for c in kolumny_user if 'uczni' in c.lower()), None)

        # --- PANEL KONTROLNY UŻYTKOWNIKA ---
        st.markdown("### 2. Mapowanie Danych Wejściowych")
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
            with st.spinner("Szukam dopasowań i zaciągam świeże dane bezpośrednio w oryginalnych kolumnach..."):
                df_wynik = df_user.copy().astype(object) # Chroni przed błędem Pandas
                
                slownik_bazy = baza['Do_wyszukiwania'].to_dict()
                progress_bar = st.progress(0)
                total = len(df_wynik)
                
                # Dodajemy tylko jedną kolumnę informacyjną na sam koniec
                df_wynik['Status_Dopasowania'] = "Brak"

                for idx, row in df_wynik.iterrows():
                    nazwa_crm = str(row[col_tytul]) if pd.notna(row[col_tytul]) else ''
                    adres_crm = str(row[col_adres]) if pd.notna(row[col_adres]) else ''
                    
                    nazwa_czysta = nazwa_crm.replace("Szansa sprzedaży", "").strip()
                    nazwa_lower = nazwa_czysta.lower()
                    
                    # --- FILTR ODRZUCAJĄCY GMINY I MIASTA ---
                    wykluczenia = ['gmina ', 'miasto ', 'urząd ', 'urzad ', 'starostwo ']
                    szkoly = ['szkoła', 'szkola', 'sp ', 'zs ', 'zespół', 'zespol', 'liceum', 'technikum', 'przedszkole', 'żłobek', 'zlobek', 'zso', 'zsz']
                    
                    is_urzad = any(w in nazwa_lower for w in wykluczenia)
                    is_szkola = any(w in nazwa_lower for w in szkoly)
                    
                    if is_urzad and not is_szkola:
                        df_wynik.at[idx, 'Status_Dopasowania'] = "⏭️ Pominięto (Gmina/Miasto)"
                        progress_bar.progress((idx + 1) / total)
                        continue

                    # --- WŁAŚCIWE WYSZUKIWANIE ---
                    fraza = nazwa_czysta + " " + adres_crm
                    fraza_znormalizowana = normalizuj(fraza)

                    if fraza_znormalizowana.strip():
                        match = process.extractOne(fraza_znormalizowana, slownik_bazy, scorer=fuzz.token_set_ratio)
                        
                        if match:
                            najlepszy_wynik = match[1]
                            dopasowany_idx = match[2]
                            dopasowany_wiersz = baza.loc[dopasowany_idx]

                            # Sklejamy długi adres z kodem pocztowym
                            kod = str(dopasowany_wiersz.get('Kod pocztowy', '')).strip()
                            adr = str(dopasowany_wiersz.get('Adres full', '')).strip()
                            pelny_dlugi_adres = f"{kod} {adr}".strip()

                            # --- AKTUALIZACJA ORYGINALNYCH KOLUMN (IN-PLACE) ---
                            # Nadpisujemy dane w starych kolumnach nowymi danymi z bazy
                            if col_adres: 
                                df_wynik.at[idx, col_adres] = pelny_dlugi_adres
                            if col_rspo: 
                                df_wynik.at[idx, col_rspo] = str(dopasowany_wiersz.get('Numer RSPO', ''))
                            if col_dyr: 
                                df_wynik.at[idx, col_dyr] = str(dopasowany_wiersz.get('Imię i nazwisko dyrektora', ''))
                            if col_email: 
                                df_wynik.at[idx, col_email] = str(dopasowany_wiersz.get('E-mail', ''))
                            if col_www: 
                                df_wynik.at[idx, col_www] = str(dopasowany_wiersz.get('Strona www', ''))
                            if col_uczniowie: 
                                df_wynik.at[idx, col_uczniowie] = str(dopasowany_wiersz.get('Liczba uczniów', ''))
                            
                            df_wynik.at[idx, 'Status_Dopasowania'] = f"✅ Zaktualizowano ({najlepszy_wynik}%)"

                    progress_bar.progress((idx + 1) / total)

                st.success("Gotowe! Struktura pliku zachowana, a dane w środku zostały zaktualizowane.")
                
                # Wyświetlamy podgląd pliku
                st.dataframe(df_wynik.head(15))

                # --- EXPORT ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_wynik.to_excel(writer, index=False, sheet_name='Uzupełnione')
                gotowy_plik = output.getvalue()

                st.download_button(
                    label="📥 Pobierz plik gotowy do CRM",
                    data=gotowy_plik,
                    file_name="gotowe_do_crm.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
