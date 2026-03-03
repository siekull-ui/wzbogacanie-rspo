import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re
from datetime import datetime

# --- 1. KONFIGURACJA STRONY I INICJALIZACJA PAMIĘCI SESJI ---
st.set_page_config(page_title="Analiza Danych Szkół", layout="wide", page_icon="🏫", initial_sidebar_state="expanded")

# Minimalistyczny CSS ukrywający tylko zbędne elementy menu
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

# Inicjalizacja stanu sesji
if 'page' not in st.session_state:
    st.session_state.page = 'home'

# --- Zmienne dla przetrzymywania wgranego pliku (Persystencja) ---
if 'raw_df' not in st.session_state:
    st.session_state.raw_df = None
if 'raw_file_name' not in st.session_state:
    st.session_state.raw_file_name = None
if 'last_uploaded_id' not in st.session_state:
    st.session_state.last_uploaded_id = None

# --- Zmienne wyników analizy i Tindera ---
if 'df_result' not in st.session_state:
    st.session_state.df_result = None
if 'to_review_indices' not in st.session_state:
    st.session_state.to_review_indices = []
if 'review_index' not in st.session_state:
    st.session_state.review_index = 0

# --- Zmienne do historii plików ---
if 'history_rspo' not in st.session_state:
    st.session_state.history_rspo = []
if 'view_history_item' not in st.session_state:
    st.session_state.view_history_item = None

def zresetuj_wyniki():
    st.session_state.df_result = None
    st.session_state.to_review_indices = []
    st.session_state.review_index = 0

def pelny_reset():
    zresetuj_wyniki()
    st.session_state.raw_df = None
    st.session_state.raw_file_name = None
    st.session_state.last_uploaded_id = None

def aktualizuj_nazwe_w_historii():
    if len(st.session_state.history_rspo) > 0:
        nowa_nazwa = st.session_state.user_filename_input
        if not nowa_nazwa.endswith('.xlsx'):
            nowa_nazwa += '.xlsx'
        st.session_state.history_rspo[0]['filename'] = nowa_nazwa

# --- 2. MODUŁ NORMALIZACJI NLP ---
def normalizuj_tekst(tekst):
    if not isinstance(tekst, str):
        return ""
    tekst = tekst.lower()
    zamiany = {
        r'\bsp\b': 'szkoła podstawowa', r'\bzs\b': 'zespół szkół', r'\blo\b': 'liceum ogólnokształcące',
        r'\bzso\b': 'zespół szkół ogólnokształcących', r'\bzsz\b': 'zespół szkół zawodowych',
        r'\bckziu\b': 'centrum kształcenia zawodowego i ustawicznego', r'\bmow\b': 'młodzieżowy ośrodek wychowawczy',
        r'\bmos\b': 'młodzieżowy ośrodek socjoterapii', r'\bsosw\b': 'specjalny ośrodek szkolno wychowawczy',
        r'\bim\.\b': '', r'\bimienia\b': '', r'\bul\.\b': '', r'\bulica\b': '', r'\bal\.\b': '',
        r'\baleja\b': '', r'\bpl\.\b': '', r'\bplac\b': '', r'\bnr\b': '', r'\bnumer\b': ''
    }
    for wzorzec, zamiennik in zamiany.items():
        tekst = re.sub(wzorzec, zamiennik, tekst)
    rzymskie_na_arabskie = {
        r'\bxv\b': '15', r'\bxiv\b': '14', r'\bxiii\b': '13', r'\bxii\b': '12', r'\bxi\b': '11',
        r'\bx\b': '10', r'\bix\b': '9', r'\bviii\b': '8', r'\bvii\b': '7', r'\bvi\b': '6',
        r'\biv\b': '4', r'\bv\b': '5', r'\biii\b': '3', r'\bii\b': '2', r'\bi\b': '1'
    }
    for rzym, arab in rzymskie_na_arabskie.items():
        tekst = re.sub(rzym, arab, tekst)
    tekst = re.sub(r'[^\w\s]', ' ', tekst)
    tekst = re.sub(r'\s+', ' ', tekst).strip()
    return tekst

# --- 3. WYSZUKIWANIE I BAZA RSPO ---
@st.cache_data
def wczytaj_baze_rspo():
    try:
        df_rspo = pd.read_csv("baza_rspo.csv", sep=None, engine='python', encoding='utf-8')
        nazwa = df_rspo['Nazwa'].fillna('')
        miejscowosc = df_rspo['Miejscowość'].fillna('')
        ulica = df_rspo['Ulica'].fillna('')
        nr_budynku = df_rspo['Numer budynku'].astype(str).replace('nan', '').fillna('')
        
        df_rspo['Pelny_Opis'] = nazwa + ' ' + miejscowosc + ' ' + ulica + ' ' + nr_budynku
        df_rspo['Pelny_Opis'] = df_rspo['Pelny_Opis'].str.replace('  ', ' ')
        df_rspo['Znormalizowany_Opis'] = df_rspo['Pelny_Opis'].apply(normalizuj_tekst)
        return df_rspo
    except Exception as e:
        st.error(f"Wystąpił błąd przy wczytywaniu bazy: {e}")
        return None


# ==========================================
# MENU BOCZNE (SIDEBAR) - DRZEWKO HISTORII
# ==========================================
with st.sidebar:
    st.header("Nawigacja")
    st.divider()
    
    if st.button("🏠 Strona Główna", use_container_width=True):
        st.session_state.page = 'home'
        st.rerun()
        
    st.subheader("🕒 Ostatnie Analizy")
    
    with st.expander("🏫 Wzbogacanie RSPO", expanded=True):
        if not st.session_state.history_rspo:
            st.caption("Brak historii. Przeprowadź pierwszą analizę.")
        else:
            for item in st.session_state.history_rspo:
                if st.button(f"📄 {item['filename']} \n({item['time']})", key=f"hist_{item['id']}", use_container_width=True):
                    st.session_state.view_history_item = item
                    st.session_state.page = 'history_view'
                    st.rerun()

    with st.expander("📊 Analiza 2 (Wkrótce)"):
        st.caption("Moduł w przygotowaniu...")

    with st.expander("🗺️ Analiza 3 (Wkrótce)"):
        st.caption("Moduł w przygotowaniu...")


# ==========================================
# GŁÓWNA NAWIGACJA (STRONY)
# ==========================================

# STRONA GŁÓWNA
if st.session_state.page == 'home':
    st.title("Analizator Szkół")
    st.markdown("Wybierz moduł analityczny i rozpocznij przetwarzanie danych.")
    st.write("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container(border=True):
            st.subheader("🏫 Wzbogacanie RSPO")
            st.write("Dopasuj dane adresowe do Bazy RSPO. Uzupełnij telefony, e-maile i WWW za pomocą algorytmu Fuzzy Logic.")
            if st.button("Uruchom Moduł", key="btn1", use_container_width=True, type="primary"):
                st.session_state.page = 'rspo_tool'
                st.rerun()
                
    with col2:
        with st.container(border=True):
            st.subheader("📊 Struktura")
            st.write("Moduł w przygotowaniu. Analiza struktury placówek, statystyki i wyciąganie wniosków.")
            st.button("Zablokowane", key="btn2", use_container_width=True, disabled=True)
            
    with col3:
        with st.container(border=True):
            st.subheader("🗺️ Geomapping")
            st.write("Moduł w przygotowaniu. Wizualizacja rozmieszczenia placówek na mapach przestrzennych.")
            st.button("Zablokowane", key="btn3", use_container_width=True, disabled=True)


# ==========================================
# PODGLĄD HISTORYCZNY (HISTORIA)
# ==========================================
elif st.session_state.page == 'history_view':
    item = st.session_state.view_history_item
    
    if st.button("⬅ Wróć do Menu Głównego"):
        st.session_state.page = 'home'
        st.rerun()
        
    st.title(f"Historia: {item['filename']}")
    st.caption(f"Data wykonania: {item['time']}")
    
    df_res = item['df_ref']
    df_do_pobrania = df_res.drop(columns=['_Oryginalna_Nazwa', '_Oryginalny_Adres', '_Kandydat_RSPO', '_Kandydat_Telefon', '_Kandydat_Email', '_Kandydat_WWW', '_Kandydat_Opis'], errors='ignore')
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_do_pobrania.to_excel(writer, index=False, sheet_name='Uzupełnione Dane')
    gotowy_excel = output.getvalue()
    
    st.download_button(
        label="📥 Pobierz Plik Ponownie (.xlsx)",
        data=gotowy_excel,
        file_name=item['filename'],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )
    
    st.divider()
    st.subheader("Podgląd Danych")
    st.dataframe(df_do_pobrania, use_container_width=True)


# ==========================================
# STRONA NARZĘDZIA RSPO
# ==========================================
elif st.session_state.page == 'rspo_tool':
    
    if st.button("⬅ Wróć do Menu Głównego"):
        st.session_state.page = 'home'
        st.rerun()
        
    st.title("Ekstrakcja i Wzbogacanie Danych RSPO")
    st.write("---")

    with st.spinner("Ładowanie silnika dopasowującego oraz bazy RSPO..."):
        baza_rspo = wczytaj_baze_rspo()

    if baza_rspo is not None:
        st.success(f"Baza wczytana pomyślnie ({len(baza_rspo):,} placówek).")
        
        # Okno wgrywania plików
        uploaded_file = st.file_uploader("Wgraj swój plik do uzupełnienia (Excel/CSV)", type=["csv", "xlsx"])

        # Logika zachowania pliku w pamięci
        if uploaded_file is not None:
            current_file_id = uploaded_file.name + str(uploaded_file.size)
            if st.session_state.last_uploaded_id != current_file_id:
                zresetuj_wyniki() 
                st.session_state.last_uploaded_id = current_file_id
                st.session_state.raw_file_name = uploaded_file.name
                
                try:
                    if uploaded_file.name.endswith('.csv'):
                        st.session_state.raw_df = pd.read_csv(uploaded_file, sep=None, engine='python')
                    else:
                        st.session_state.raw_df = pd.read_excel(uploaded_file)
                except Exception as e:
                    st.error(f"Błąd podczas wczytywania pliku: {e}")
                    st.session_state.raw_df = None

        # --- GŁÓWNA LOGIKA NARZĘDZIA ---
        if st.session_state.raw_df is not None:
            try:
                df_uploaded = st.session_state.raw_df.copy()
                kolumny = df_uploaded.columns.tolist()
                
                # --- PANEL STEROWANIA ---
                if st.session_state.df_result is None: 
                    
                    # KROK 1
                    with st.container(border=True):
                        st.subheader("Krok 1: Mapowanie Zmiennych")
                        col_a1, col_a2 = st.columns(2)
                        with col_a1:
                            kol_nazwa = st.selectbox("Kolumna z NAZWĄ szkoły:", kolumny)
                        with col_a2:
                            kol_adres_lista = st.multiselect("Kolumny z ADRESEM (możesz wybrać kilka):", kolumny)

                        if kol_nazwa and kol_adres_lista:
                            st.caption("Podgląd wybranych danych (pierwsze 5 wierszy):")
                            kolumny_do_podgladu = [kol_nazwa] + kol_adres_lista
                            st.dataframe(df_uploaded[kolumny_do_podgladu].head(5), use_container_width=True)

                    # KROK 2
                    with st.container(border=True):
                        st.subheader("Krok 2: Opcje dociągania danych")
                        szukaj_wszystko = st.checkbox("Dociągnij automatycznie wszystkie dane (Numer, Telefon, E-mail, WWW)", value=True)
                        
                        szukaj_rspo, szukaj_telefon, szukaj_email, szukaj_www = True, True, True, True
                        if not szukaj_wszystko:
                            cc1, cc2, cc3, cc4 = st.columns(4)
                            with cc1: szukaj_rspo = st.checkbox("Numer RSPO", value=True)
                            with cc2: szukaj_telefon = st.checkbox("Telefon")
                            with cc3: szukaj_email = st.checkbox("E-mail")
                            with cc4: szukaj_www = st.checkbox("Strona www")

                    # KROK 3
                    with st.container(border=True):
                        st.subheader("Krok 3: Czułość algorytmu")
                        st.write("Rekordy poniżej progu tolerancji trafią do ręcznej weryfikacji.")
                        prog_czulosci = st.slider("Próg pewności dopasowania (%)", min_value=50, max_value=100, value=80, step=1)

                    st.write("")

                    if st.button("Uruchom Analizę", type="primary"):
                        if len(kol_adres_lista) == 0:
                            st.warning("Wybierz co najmniej jedną kolumnę w polu ADRES.")
                        else:
                            opisy_dict = baza_rspo['Znormalizowany_Opis'].to_dict()
                            my_bar = st.progress(0, text="Analiza układu danych...")
                            
                            df_uploaded['Dopasowane: Numer RSPO'] = "Nie znaleziono"
                            df_uploaded['Dopasowane: Telefon'] = "-"
                            df_uploaded['Dopasowane: E-mail'] = "-"
                            df_uploaded['Dopasowane: Strona www'] = "-"
                            df_uploaded['Pewność dopasowania (%)'] = 0
                            df_uploaded['Status'] = "Brak kandydata"
                            
                            df_uploaded['_Oryginalna_Nazwa'] = ""
                            df_uploaded['_Oryginalny_Adres'] = ""
                            df_uploaded['_Kandydat_RSPO'] = ""
                            df_uploaded['_Kandydat_Telefon'] = ""
                            df_uploaded['_Kandydat_Email'] = ""
                            df_uploaded['_Kandydat_WWW'] = ""
                            df_uploaded['_Kandydat_Opis'] = ""
                            
                            total_rows = len(df_uploaded)
                            
                            with st.spinner("Przeszukiwanie bazy i dopasowywanie rekordów..."):
                                for index, row in df_uploaded.iterrows():
                                    if index % 5 == 0 or index == total_rows - 1:
                                        my_bar.progress((index + 1) / total_rows, text=f"Przetwarzanie: {index+1} / {total_rows} rekordów")
                                    
                                    brudna_nazwa = str(row[kol_nazwa])
                                    fragmenty_adresu = [str(row[col]).strip() for col in kol_adres_lista if pd.notna(row[col]) and str(row[col]).strip() != ""]
                                    brudny_adres = " ".join(fragmenty_adresu)
                                    
                                    szukana_fraza = brudna_nazwa + ' ' + brudny_adres
                                    znormalizowana_fraza = normalizuj_tekst(szukana_fraza)
                                    
                                    najlepsze = process.extractOne(znormalizowana_fraza, opisy_dict, scorer=fuzz.token_set_ratio)
                                    
                                    df_uploaded.at[index, '_Oryginalna_Nazwa'] = brudna_nazwa
                                    df_uploaded.at[index, '_Oryginalny_Adres'] = brudny_adres
                                    
                                    if najlepsze:
                                        pewnosc = najlepsze[1]
                                        dopasowany_indeks = najlepsze[2]
                                        dopasowany_wiersz = baza_rspo.loc[dopasowany_indeks]
                                        
                                        df_uploaded.at[index, 'Pewność dopasowania (%)'] = pewnosc
                                        df_uploaded.at[index, '_Kandydat_Opis'] = dopasowany_wiersz['Pelny_Opis']
                                        df_uploaded.at[index, '_Kandydat_RSPO'] = dopasowany_wiersz.get('Numer RSPO', 'Brak')
                                        df_uploaded.at[index, '_Kandydat_Telefon'] = dopasowany_wiersz.get('Telefon', 'Brak')
                                        df_uploaded.at[index, '_Kandydat_Email'] = dopasowany_wiersz.get('E-mail', 'Brak')
                                        df_uploaded.at[index, '_Kandydat_WWW'] = dopasowany_wiersz.get('Strona www', 'Brak')
                                        
                                        if pewnosc >= prog_czulosci:
                                            df_uploaded.at[index, 'Status'] = "✅ Auto-Dopasowano"
                                            df_uploaded.at[index, 'Dopasowane: Numer RSPO'] = dopasowany_wiersz.get('Numer RSPO', 'Brak')
                                            df_uploaded.at[index, 'Dopasowane: Telefon'] = dopasowany_wiersz.get('Telefon', 'Brak')
                                            df_uploaded.at[index, 'Dopasowane: E-mail'] = dopasowany_wiersz.get('E-mail', 'Brak')
                                            df_uploaded.at[index, 'Dopasowane: Strona www'] = dopasowany_wiersz.get('Strona www', 'Brak')
                                        else:
                                            df_uploaded.at[index, 'Status'] = "⚠️ Do weryfikacji"

                            my_bar.empty()
                            
                            st.session_state.df_result = df_uploaded
                            st.session_state.to_review_indices = df_uploaded[df_uploaded['Status'] == "⚠️ Do weryfikacji"].index.tolist()
                            st.session_state.review_index = 0
                            
                            # --- ZAPIS DO HISTORII ---
                            nazwa_bazowa = st.session_state.raw_file_name.rsplit('.', 1)[0]
                            domyslna_nazwa_pliku = f"Rozszerzone_{nazwa_bazowa}.xlsx"
                            
                            nowa_historia = {
                                'id': datetime.now().strftime("%Y%m%d%H%M%S"),
                                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'filename': domyslna_nazwa_pliku,
                                'df_ref': st.session_state.df_result 
                            }
                            st.session_state.history_rspo.insert(0, nowa_historia)
                            if len(st.session_state.history_rspo) > 10:
                                st.session_state.history_rspo.pop()
                            
                            st.rerun()

                # --- EKRAN WYNIKÓW I WERYFIKACJA ---
                if st.session_state.df_result is not None:
                    
                    df_res = st.session_state.df_result
                    total_rows = len(df_res)
                    auto_count = len(df_res[df_res['Status'] == '✅ Auto-Dopasowano'])
                    manual_count = len(df_res[df_res['Status'] == '🛠️ Ręcznie dopasowano'])
                    rejected_count = len(df_res[(df_res['Status'] == '⚠️ Do weryfikacji') | (df_res['Status'] == '❌ Odrzucono') | (df_res['Status'] == 'Brak kandydata')])
                    
                    st.subheader("Dashboard Wyników")
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Wszystkie wiersze", total_rows)
                        c2.metric("Dopasowano", auto_count + manual_count, f"{round(((auto_count+manual_count)/total_rows)*100, 1)}%")
                        c3.metric("Do weryfikacji", len(st.session_state.to_review_indices) - st.session_state.review_index)
                        c4.metric("Brak / Odrzucono", rejected_count)
                    
                    st.divider()
                    
                    # --- TRYB RĘCZNEJ WERYFIKACJI ---
                    st.subheader("Tryb Ręcznej Weryfikacji")
                    
                    if st.session_state.review_index < len(st.session_state.to_review_indices):
                        current_idx = st.session_state.to_review_indices[st.session_state.review_index]
                        row_data = df_res.loc[current_idx]
                        
                        st.info(f"Rekord **{st.session_state.review_index + 1}** z **{len(st.session_state.to_review_indices)}** wymaga weryfikacji:")
                        
                        with st.container(border=True):
                            col_t1, col_t2 = st.columns(2)
                            with col_t1:
                                st.markdown("#### Twoje dane z pliku")
                                st.write(f"**Nazwa:** {row_data['_Oryginalna_Nazwa']}")
                                st.write(f"**Adres:** {row_data['_Oryginalny_Adres']}")
                            with col_t2:
                                st.markdown(f"#### Kandydat RSPO (Pewność: {row_data['Pewność dopasowania (%)']}%)")
                                st.write(f"**Opis:** {row_data['_Kandydat_Opis']}")
                                st.write(f"**RSPO:** {row_data['_Kandydat_RSPO']}")
                                
                            st.write("---") 
                            
                            c_btn1, c_btn_undo, c_btn2 = st.columns([2, 1, 2])
                            
                            with c_btn_undo:
                                if st.session_state.review_index > 0:
                                    if st.button("Cofnij", use_container_width=True):
                                        st.session_state.review_index -= 1
                                        idx_to_revert = st.session_state.to_review_indices[st.session_state.review_index]
                                        st.session_state.df_result.at[idx_to_revert, 'Status'] = "⚠️ Do weryfikacji"
                                        st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Numer RSPO'] = "Nie znaleziono"
                                        st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Telefon'] = "-"
                                        st.session_state.df_result.at[idx_to_revert, 'Dopasowane: E-mail'] = "-"
                                        st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Strona www'] = "-"
                                        st.rerun()
                                        
                            with c_btn1:
                                if st.button("Akceptuj", use_container_width=True, type="primary"):
                                    st.session_state.df_result.at[current_idx, 'Dopasowane: Numer RSPO'] = row_data['_Kandydat_RSPO']
                                    st.session_state.df_result.at[current_idx, 'Dopasowane: Telefon'] = row_data['_Kandydat_Telefon']
                                    st.session_state.df_result.at[current_idx, 'Dopasowane: E-mail'] = row_data['_Kandydat_Email']
                                    st.session_state.df_result.at[current_idx, 'Dopasowane: Strona www'] = row_data['_Kandydat_WWW']
                                    st.session_state.df_result.at[current_idx, 'Status'] = "🛠️ Ręcznie dopasowano"
                                    st.session_state.review_index += 1
                                    st.rerun()
                                    
                            with c_btn2:
                                if st.button("Odrzuć", use_container_width=True):
                                    st.session_state.df_result.at[current_idx, 'Status'] = "❌ Odrzucono"
                                    st.session_state.review_index += 1
                                    st.rerun()
                        
                    else:
                        if len(st.session_state.to_review_indices) > 0:
                            st.success("Weryfikacja zakończona. Plik jest gotowy do pobrania.")
                            if st.button("Cofnij ostatnią decyzję"):
                                st.session_state.review_index -= 1
                                idx_to_revert = st.session_state.to_review_indices[st.session_state.review_index]
                                st.session_state.df_result.at[idx_to_revert, 'Status'] = "⚠️ Do weryfikacji"
                                st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Numer RSPO'] = "Nie znaleziono"
                                st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Telefon'] = "-"
                                st.session_state.df_result.at[idx_to_revert, 'Dopasowane: E-mail'] = "-"
                                st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Strona www'] = "-"
                                st.rerun()
                        else:
                            st.success("Brak szkół granicznych do weryfikacji. Proces zakończony automatycznie.")

                    st.divider()
                    
                    df_do_pobrania = df_res.drop(columns=['_Oryginalna_Nazwa', '_Oryginalny_Adres', '_Kandydat_RSPO', '_Kandydat_Telefon', '_Kandydat_Email', '_Kandydat_WWW', '_Kandydat_Opis'])
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_do_pobrania.to_excel(writer, index=False, sheet_name='Uzupełnione Dane')
                    gotowy_excel = output.getvalue()
                    
                    # --- POBIERANIE WYNIKÓW ---
                    st.subheader("Pobieranie Wyników")
                    
                    aktualna_nazwa_z_historii = st.session_state.history_rspo[0]['filename'] if len(st.session_state.history_rspo) > 0 else "Rozszerzone_dane.xlsx"
                    
                    col_input, col_btn = st.columns([3, 1])
                    with col_input:
                        nazwa_uzytkownika = st.text_input(
                            "Zmień nazwę pliku przed pobraniem:", 
                            value=aktualna_nazwa_z_historii, 
                            key="user_filename_input",
                            on_change=aktualizuj_nazwe_w_historii
                        )
                    
                    if not nazwa_uzytkownika.endswith(".xlsx"):
                        nazwa_pliku = nazwa_uzytkownika + ".xlsx"
                    else:
                        nazwa_pliku = nazwa_uzytkownika
                    
                    st.download_button(
                        label="Pobierz Plik (.xlsx)",
                        data=gotowy_excel,
                        file_name=nazwa_pliku,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
                    
                    st.write("")
                    if st.button("Zakończ sesję i wgraj nowy plik"):
                        pelny_reset()
                        st.rerun()

                    st.write("")
                    with st.expander("Podgląd obecnego stanu pliku (Top 15)", expanded=False):
                        st.dataframe(df_do_pobrania.head(15), use_container_width=True)

            except Exception as e:
                st.error(f"Wystąpił problem przy przetwarzaniu pliku: {e}")
