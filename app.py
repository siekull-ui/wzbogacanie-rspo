import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Wyszukiwarka RSPO CRM", layout="wide")
st.title("🏫 Auto-Uzupełniacz Danych CRM (Pełna Kontrola)")
st.write("Wgraj eksport, wskaż kolumny i dopasuj rygorystyczność. System weryfikuje osobno NAZWĘ i ADRES.")

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

        st.markdown("### 1. Podgląd wgranego pliku:")
        st.dataframe(df_user.head(3))

        kolumny_user = df_user.columns.tolist()

        # --- PANEL KONTROLNY UŻYTKOWNIKA ---
        st.markdown("### 2. Mapowanie Danych")
        col1, col2 = st.columns(2)
        with col1:
            col_tytul = st.selectbox("📌 Wybierz kolumnę z NAZWĄ szkoły:", kolumny_user, index=0)
        with col2:
            # Próba domyślnego wybrania kolumny z adresem, jeśli istnieje
            domyslny_adres = 1 if len(kolumny_user) > 1 else 0
            for i, kol in enumerate(kolumny_user):
                if "adres" in kol.lower():
                    domyslny_adres = i
                    break
            col_adres = st.selectbox("📍 Wybierz kolumnę z ADRESEM szkoły:", kolumny_user, index=domyslny_adres)

        st.markdown("### 3. Opcje Czułości")
        col3, col4 = st.columns(2)
        with col3:
            prog_adres = st.slider("Wymagana zgodność ADRESU (%)", min_value=50, max_value=100, value=85, step=1, help="Ustaw na 85-90% dla rygorystycznego sprawdzania miasta i ulicy.")
        with col4:
            prog_nazwa = st.slider("Wymagana zgodność NAZWY (%)", min_value=50, max_value=100, value=80, step=1)

        if st.button("🚀 Uruchom rygorystyczne dopasowanie", type="primary"):
            with st.spinner("Przeszukuję bazę z restrykcyjnym sprawdzaniem adresów..."):
                df_wynik = df_user.copy()
                slownik_nazw = baza['Znormalizowana_Nazwa'].to_dict()
                
                progress_bar = st.progress(0)
                total = len(df_wynik)
                
                # Zabezpieczenie kolumn wyjściowych
                col_rspo_out = 'RSPO - Numer'
                col_dyr_out = 'RSPO - Dyrektor'
                col_adres_out = 'RSPO - Adres Poprawny'
                col_email_out = 'RSPO - E-mail'
                col_www_out = 'RSPO - WWW'
                col_uczniowie_out = 'RSPO - Uczniowie'
                
                for c in [col_rspo_out, col_dyr_out, col_adres_out, col_email_out, col_www_out, col_uczniowie_out]:
                    df_wynik[c] = ""
                        
                df_wynik['Status_Dopasowania'] = "Brak"
                df_wynik['Szczegóły_Błędu'] = ""

                for idx, row in df_wynik.iterrows():
                    nazwa_crm = str(row[col_tytul]) if pd.notna(row[col_tytul]) else ''
                    adres_crm = str(row[col_adres]) if pd.notna(row[col_adres]) else ''
                    
                    # Czyszczenie z typowych śmieci CRM
                    nazwa_crm = nazwa_crm.replace("Szansa sprzedaży", "").strip()
                    
                    znorm_nazwa_crm = normalizuj(nazwa_crm)
                    znorm_adres_crm = normalizuj(adres_crm)

                    if znorm_nazwa_crm.strip():
                        # KROK 1: Pobierz 15 szkół z najbardziej podobną NAZWĄ
                        kandydaci = process.extract(znorm_nazwa_crm, slownik_nazw, limit=15, scorer=fuzz.token_set_ratio)
                        
                        najlepszy_idx = None
                        najlepszy_wynik_nazwy = 0
                        powod_odrzucenia = "Nie znaleziono podobnej nazwy w bazie"

                        for kandydat_nazwa, wynik_nazwy, bazy_idx in kandydaci:
                            wiersz_bazy = baza.loc[bazy_idx]
                            znorm_adres_bazy = str(wiersz_bazy['Znormalizowany_Adres'])
                            
                            # KROK 2: Weryfikacja ADRESU (Tylko jeśli jest podany w CRM)
                            if znorm_adres_crm.strip() != "":
                                zgodnosc_adresu = fuzz.token_set_ratio(znorm_adres_crm, znorm_adres_bazy)
                                
                                # Sprawdzamy, czy adres zgadza się z suwakiem (domyślnie 85%)
                                if zgodnosc_adresu < prog_adres:
                                    powod_odrzucenia = f"Adres odrzucony (zgodność: {zgodnosc_adresu}%)"
                                    continue
                            
                            # KROK 3: Zapisujemy najlepszy wynik z tych, co przetrwały sito adresu
                            if wynik_nazwy >= prog_nazwa and wynik_nazwy > najlepszy_wynik_nazwy:
                                najlepszy_wynik_nazwy = wynik_nazwy
                                najlepszy_idx = bazy_idx
                        
                        # KROK 4: Zapisywanie danych do pliku
                        if najlepszy_idx is not None:  
                            dopasowany_wiersz = baza.loc[najlepszy_idx]

                            df_wynik.at[idx, col_rspo_out] = dopasowany_wiersz.get('Numer RSPO', '')
                            df_wynik.at[idx, col_adres_out] = dopasowany_wiersz.get('Adres full', '')
                            df_wynik.at[idx, col_dyr_out] = dopasowany_wiersz.get('Imię i nazwisko dyrektora', '')
                            df_wynik.at[idx, col_email_out] = dopasowany_wiersz.get('E-mail', '')
                            df_wynik.at[idx, col_www_out] = dopasowany_wiersz.get('Strona www', '')
                            df_wynik.at[idx, col_uczniowie_out] = dopasowany_wiersz.get('Liczba uczniów', '')
                                    
                            df_wynik.at[idx, 'Status_Dopasowania'] = f"✅ Znaleziono (Nazwa: {najlepszy_wynik_nazwy}%)"
                        else:
                            df_wynik.at[idx, 'Status_Dopasowania'] = "❌ Odrzucono"
                            df_wynik.at[idx, 'Szczegóły_Błędu'] = powod_odrzucenia

                    progress_bar.progress((idx + 1) / total)

                st.success("Analiza zakończona!")
                st.dataframe(df_wynik[[col_tytul, col_adres, 'Status_Dopasowania', 'Szczegóły_Błędu']].head(20))

                # --- EXPORT ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_wynik.to_excel(writer, index=False, sheet_name='Zaktualizowane')
                gotowy_plik = output.getvalue()

                st.download_button(
                    label="📥 Pobierz zaktualizowany plik Excel",
                    data=gotowy_plik,
                    file_name="uzupelnione_deale_kontrola.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
