import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re
from datetime import datetime

# --- 1. KONFIGURACJA STRONY I INICJALIZACJA PAMIĘCI SESJI ---
st.set_page_config(page_title="Analiza Danych Szkół", layout="wide", initial_sidebar_state="expanded")

# Zaawansowany, profesjonalny CSS odpowiedzialny za UI/UX
st.markdown("""
<style>
    /* Ukrycie TYLKO zbędnych elementów Streamlit (zostawiamy hamburger menu) */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    
    /* Globalne style dla tytułów (Nowoczesne, statyczne, eleganckie) */
    .main-title {
        text-align: center;
        font-size: 3rem;
        font-weight: 800;
        color: #1B263B; /* Głęboki, matowy granat */
        letter-spacing: -0.5px;
        margin-bottom: 2rem;
        margin-top: -2rem;
        padding-bottom: 15px;
        border-bottom: 3px solid #415A77; /* Subtelne odcięcie */
    }
    .sub-title {
        text-align: center;
        font-size: 2rem;
        font-weight: 700;
        color: #415A77;
        margin-bottom: 1.5rem;
    }

    /* Ujednolicenie i efekt hover dla kontenerów (Kart) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px;
        border: 1px solid rgba(150, 150, 150, 0.2);
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        background-color: transparent;
        height: 100%;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
        border-color: #415A77;
    }

    /* Wymuszanie równej wysokości kolumn */
    [data-testid="column"] > div {
        height: 100%;
    }

    /* Karty 'Tinder' do recenzji */
    .review-cards-container {
        display: flex;
        gap: 20px;
        margin-top: 15px;
        margin-bottom: 25px;
    }
    .review-card {
        flex: 1;
        padding: 20px;
        border-radius: 12px;
        border-top: 5px solid;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    .user-card {
        background-color: #F8F9FA;
        border-top-color: #6C757D;
    }
    .rspo-card {
        background-color: #F0F4F8;
        border-top-color: #415A77;
    }
    .card-header {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 15px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .user-card .card-header { color: #5A6268; }
    .rspo-card .card-header { color: #1B263B; }
    
    .card-row { margin-bottom: 8px; font-size: 0.95rem; color: #333;}
    .card-label { font-weight: 600; opacity: 0.8; }
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

# --- Zmienne wyników analizy ---
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
# MENU BOCZNE (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("Nawigacja")
    st.divider()
    
    if st.button("Strona Główna", use_container_width=True):
        st.session_state.page = 'home'
        st.rerun()
        
    st.subheader("Ostatnie Analizy")
    
    with st.expander("Wzbogacanie RSPO", expanded=True):
        if not st.session_state.history_rspo:
            st.caption("Brak historii. Przeprowadź pierwszą analizę.")
        else:
            for item in st.session_state.history_rspo:
                if st.button(f"{item['filename']} \n({item['time']})", key=f"hist_{item['id']}", use_container_width=True):
                    st.session_state.view_history_item = item
                    st.session_state.page = 'history_view'
                    st.rerun()

    with st.expander("Analiza Struktury (Wkrótce)"):
        st.caption("Moduł w przygotowaniu...")

    with st.expander("Geomapping (Wkrótce)"):
        st.caption("Moduł w przygotowaniu...")

# ==========================================
# GŁÓWNA NAWIGACJA (STRONY)
# ==========================================

# STRONA GŁÓWNA
if st.session_state.page == 'home':
    st.markdown("<div class='main-title'>Platforma Analityczna Szkół</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555; margin-bottom: 3rem; font-size: 1.1rem;'>Wybierz moduł analityczny i rozpocznij przetwarzanie danych z wykorzystaniem zaawansowanych algorytmów.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container(border=True):
            st.subheader("Wzbogacanie RSPO")
            st.write("Dopasuj dane adresowe do Bazy RSPO. Uzupełnij telefony, e-maile i adresy WWW za pomocą algorytmu Fuzzy Logic.")
            st.write("") # Spacer
            if st.button("Uruchom Moduł", key="btn1", use_container_width=True, type="primary"):
                st.session_state.page = 'rspo_tool'
                st.rerun()
                
    with col2:
        with st.container(border=True):
            st.subheader("Struktura Organizacyjna")
            st.write("Analiza struktury placówek, wskaźniki statystyczne i generowanie raportów w oparciu o dostarczone zbiory.")
            st.write("") # Spacer
            st.button("Zablokowane", key="btn2", use_container_width=True, disabled=True)
            
    with col3:
        with st.container(border=True):
            st.subheader("Geomapping")
            st.write("Wizualizacja rozmieszczenia placówek na interaktywnych mapach przestrzennych wraz z analizą zasięgu.")
            st.write("") # Spacer
            st.button("Zablokowane", key="btn3", use_container_width=True, disabled=True)


# ==========================================
# PODGLĄD HISTORYCZNY
# ==========================================
elif st.session_state.page == 'history_view':
    item = st.session_state.view_history_item
    
    if st.button("Wróć do Menu Głównego"):
        st.session_state.page = 'home'
        st.rerun()
        
    st.markdown(f"<div class='sub-title'>Historia: {item['filename']}</div>", unsafe_allow_html=True)
    st.caption(f"Czas wygenerowania raportu: {item['time']}")
    
    df_res = item['df_ref']
    df_do_pobrania = df_res.drop(columns=['_Oryginalna_Nazwa', '_Oryginalny_Adres', '_Kandydat_RSPO', '_Kandydat_Telefon', '_Kandydat_Email', '_Kandydat_WWW', '_Kandydat_Opis'], errors='ignore')
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_do_pobrania.to_excel(writer, index=False, sheet_name='Uzupełnione Dane')
    gotowy_excel = output.getvalue()
    
    st.download_button(
        label="Pobierz Plik Ponownie (.xlsx)",
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
    
    if st.button("Wróć do Menu Głównego"):
        st.session_state.page = 'home'
        st.rerun()
        
    st.markdown("<div class='sub-title'>Ekstrakcja i Wzbogacanie Danych RSPO</div>", unsafe_allow_html=True)
    st.write("---")

    with st.spinner("Inicjalizacja środowiska i ładowanie Bazy RSPO..."):
        baza_rspo = wczytaj_baze_rspo()

    if baza_rspo is not None:
        st.success(f"System gotowy. Pomyślnie wczytano {len(baza_rspo):,} rekordów placówek.")
        
        # Okno wgrywania plików
        uploaded_file = st.file_uploader("Prześlij plik z danymi do wzbogacenia (Excel / CSV)", type=["csv", "xlsx"])

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
                    st.error(f"Wystąpił błąd krytyczny podczas parsowania pliku: {e}")
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
                        st.subheader("Etap 1: Mapowanie Atrybutów")
                        col_a1, col_a2 = st.columns(2)
                        with col_a1:
                            kol_nazwa = st.selectbox("Wskaż kolumnę zawierającą NAZWĘ placówki:", kolumny)
                        with col_a2:
                            kol_adres_lista = st.multiselect("Wskaż kolumny definiujące ADRES:", kolumny)

                        if kol_nazwa and kol_adres_lista:
                            st.caption("Podgląd wyselekcjonowanej struktury (próbka 5 rekordów):")
                            kolumny_do_podgladu = [kol_nazwa] + kol_adres_lista
                            st.dataframe(df_uploaded[kolumny_do_podgladu].head(5), use_container_width=True)

                    # KROK 2
                    with st.container(border=True):
                        st.subheader("Etap 2: Parametry Wzbogacania")
                        szukaj_wszystko = st.checkbox("Automatyczna ekstrakcja wszystkich dostępnych atrybutów (RSPO, Telefon, E-mail, WWW)", value=True)
                        
                        szukaj_rspo, szukaj_telefon, szukaj_email, szukaj_www = True, True, True, True
                        if not szukaj_wszystko:
                            cc1, cc2, cc3, cc4 = st.columns(4)
                            with cc1: szukaj_rspo = st.checkbox("Identyfikator RSPO", value=True)
                            with cc2: szukaj_telefon = st.checkbox("Numer telefonu")
                            with cc3: szukaj_email = st.checkbox("Adres e-mail")
                            with cc4: szukaj_www = st.checkbox("Witryna internetowa")

                    # KROK 3
                    with st.container(border=True):
                        st.subheader("Etap 3: Kalibracja Algorytmu")
                        st.write("Wybierz próg pewności dopasowania. Rekordy poniżej wskazanej wartości zostaną skierowane do weryfikacji manualnej.")
                        prog_czulosci = st.slider("Minimalny próg akceptacji dopasowania (%)", min_value=50, max_value=100, value=80, step=1)

                    st.write("")

                    if st.button("Inicjuj Przetwarzanie", type="primary"):
                        if len(kol_adres_lista) == 0:
                            st.warning("Należy przypisać co najmniej jedną kolumnę w sekcji definiującej ADRES.")
                        else:
                            opisy_dict = baza_rspo['Znormalizowany_Opis'].to_dict()
                            my_bar = st.progress(0, text="Skanowanie przestrzeni roboczej...")
                            
                            df_uploaded['Dopasowane: Numer RSPO'] = "Brak kandydata"
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
                            
                            with st.spinner("Przetwarzanie rozmyte i optymalizacja macierzy..."):
                                for index, row in df_uploaded.iterrows():
                                    if index % 5 == 0 or index == total_rows - 1:
                                        my_bar.progress((index + 1) / total_rows, text=f"Analiza: rekord {index+1} / {total_rows}")
                                    
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
                                            df_uploaded.at[index, 'Status'] = "Auto-Dopasowano"
                                            df_uploaded.at[index, 'Dopasowane: Numer RSPO'] = dopasowany_wiersz.get('Numer RSPO', 'Brak')
                                            df_uploaded.at[index, 'Dopasowane: Telefon'] = dopasowany_wiersz.get('Telefon', 'Brak')
                                            df_uploaded.at[index, 'Dopasowane: E-mail'] = dopasowany_wiersz.get('E-mail', 'Brak')
                                            df_uploaded.at[index, 'Dopasowane: Strona www'] = dopasowany_wiersz.get('Strona www', 'Brak')
                                        else:
                                            df_uploaded.at[index, 'Status'] = "Do weryfikacji"

                            my_bar.empty()
                            
                            st.session_state.df_result = df_uploaded
                            st.session_state.to_review_indices = df_uploaded[df_uploaded['Status'] == "Do weryfikacji"].index.tolist()
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
                    auto_count = len(df_res[df_res['Status'] == 'Auto-Dopasowano'])
                    manual_count = len(df_res[df_res['Status'] == 'Ręcznie dopasowano'])
                    rejected_count = len(df_res[(df_res['Status'] == 'Do weryfikacji') | (df_res['Status'] == 'Odrzucono') | (df_res['Status'] == 'Brak kandydata')])
                    
                    st.subheader("Konsola Wyników")
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Łączna liczba rekordów", total_rows)
                        c2.metric("Skuteczność przypisań", auto_count + manual_count, f"{round(((auto_count+manual_count)/total_rows)*100, 1)}%")
                        c3.metric("Oczekujące weryfikacje", len(st.session_state.to_review_indices) - st.session_state.review_index)
                        c4.metric("Rekordy odrzucone", rejected_count)
                    
                    st.divider()
                    
                    # --- TRYB RĘCZNEJ WERYFIKACJI (TINDER KARTY) ---
                    st.subheader("Panel Rozstrzygania Niejednoznaczności")
                    
                    if st.session_state.review_index < len(st.session_state.to_review_indices):
                        current_idx = st.session_state.to_review_indices[st.session_state.review_index]
                        row_data = df_res.loc[current_idx]
                        
                        st.info(f"Analiza rekordu **{st.session_state.review_index + 1}** z **{len(st.session_state.to_review_indices)}** (Pewność dopasowania algorytmu: {row_data['Pewność dopasowania (%)']}%)")
                        
                        # Tworzenie Kart przy użyciu HTML/CSS
                        html_cards = f"""
                        <div class="review-cards-container">
                            <div class="review-card user-card">
                                <div class="card-header">Dane z pliku wejściowego</div>
                                <div class="card-row"><span class="card-label">Nazwa:</span> {row_data['_Oryginalna_Nazwa']}</div>
                                <div class="card-row"><span class="card-label">Oryginalny Adres:</span> {row_data['_Oryginalny_Adres']}</div>
                            </div>
                            <div class="review-card rspo-card">
                                <div class="card-header">Kandydat z Bazy RSPO</div>
                                <div class="card-row"><span class="card-label">Znormalizowany Opis:</span> {row_data['_Kandydat_Opis']}</div>
                                <div class="card-row"><span class="card-label">Numer RSPO:</span> {row_data['_Kandydat_RSPO']}</div>
                            </div>
                        </div>
                        """
                        st.markdown(html_cards, unsafe_allow_html=True)
                        
                        # Przyciski sterujące pod kartami
                        c_btn1, c_btn_undo, c_btn2 = st.columns([2, 1, 2])
                        
                        with c_btn_undo:
                            if st.session_state.review_index > 0:
                                if st.button("Cofnij akcję", use_container_width=True):
                                    st.session_state.review_index -= 1
                                    idx_to_revert = st.session_state.to_review_indices[st.session_state.review_index]
                                    st.session_state.df_result.at[idx_to_revert, 'Status'] = "Do weryfikacji"
                                    st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Numer RSPO'] = "Brak kandydata"
                                    st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Telefon'] = "-"
                                    st.session_state.df_result.at[idx_to_revert, 'Dopasowane: E-mail'] = "-"
                                    st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Strona www'] = "-"
                                    st.rerun()
                                    
                        with c_btn1:
                            if st.button("Zatwierdź Powiązanie", use_container_width=True, type="primary"):
                                st.session_state.df_result.at[current_idx, 'Dopasowane: Numer RSPO'] = row_data['_Kandydat_RSPO']
                                st.session_state.df_result.at[current_idx, 'Dopasowane: Telefon'] = row_data['_Kandydat_Telefon']
                                st.session_state.df_result.at[current_idx, 'Dopasowane: E-mail'] = row_data['_Kandydat_Email']
                                st.session_state.df_result.at[current_idx, 'Dopasowane: Strona www'] = row_data['_Kandydat_WWW']
                                st.session_state.df_result.at[current_idx, 'Status'] = "Ręcznie dopasowano"
                                st.session_state.review_index += 1
                                st.rerun()
                                
                        with c_btn2:
                            if st.button("Odrzuć Kandydata", use_container_width=True):
                                st.session_state.df_result.at[current_idx, 'Status'] = "Odrzucono"
                                st.session_state.review_index += 1
                                st.rerun()
                        
                    else:
                        if len(st.session_state.to_review_indices) > 0:
                            st.success("Proces weryfikacji manualnej został pomyślnie zakończony.")
                            if st.button("Cofnij ostatnią akcję rozstrzygającą"):
                                st.session_state.review_index -= 1
                                idx_to_revert = st.session_state.to_review_indices[st.session_state.review_index]
                                st.session_state.df_result.at[idx_to_revert, 'Status'] = "Do weryfikacji"
                                st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Numer RSPO'] = "Brak kandydata"
                                st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Telefon'] = "-"
                                st.session_state.df_result.at[idx_to_revert, 'Dopasowane: E-mail'] = "-"
                                st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Strona www'] = "-"
                                st.rerun()
                        else:
                            st.success("Nie wykryto rekordów wymagających ręcznej interwencji. Proces zakończony w trybie automatycznym.")

                    st.divider()
                    
                    df_do_pobrania = df_res.drop(columns=['_Oryginalna_Nazwa', '_Oryginalny_Adres', '_Kandydat_RSPO', '_Kandydat_Telefon', '_Kandydat_Email', '_Kandydat_WWW', '_Kandydat_Opis'])
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_do_pobrania.to_excel(writer, index=False, sheet_name='Uzupełnione Dane')
                    gotowy_excel = output.getvalue()
                    
                    # --- POBIERANIE WYNIKÓW ---
                    st.subheader("Eksport Danych Wyjściowych")
                    
                    aktualna_nazwa_z_historii = st.session_state.history_rspo[0]['filename'] if len(st.session_state.history_rspo) > 0 else "Rozszerzone_dane.xlsx"
                    
                    col_input, col_btn = st.columns([3, 1])
                    with col_input:
                        nazwa_uzytkownika = st.text_input(
                            "Zdefiniuj nazwę pliku docelowego:", 
                            value=aktualna_nazwa_z_historii, 
                            key="user_filename_input",
                            on_change=aktualizuj_nazwe_w_historii
                        )
                    
                    if not nazwa_uzytkownika.endswith(".xlsx"):
                        nazwa_pliku = nazwa_uzytkownika + ".xlsx"
                    else:
                        nazwa_pliku = nazwa_uzytkownika
                    
                    st.download_button(
                        label="Pobierz Zestawienie (.xlsx)",
                        data=gotowy_excel,
                        file_name=nazwa_pliku,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
                    
                    st.write("")
                    if st.button("Zamknij sesję i prześlij nowy zbiór danych"):
                        pelny_reset()
                        st.rerun()

                    st.write("")
                    with st.expander("Inspekcja struktury wyjściowej (podgląd 15 pierwszych wierszy)", expanded=False):
                        st.dataframe(df_do_pobrania.head(15), use_container_width=True)

            except Exception as e:
                st.error(f"Zdiagnozowano błąd podczas manipulacji ramką danych: {e}")

