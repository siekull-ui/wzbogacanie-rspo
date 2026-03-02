import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re
import base64
from datetime import datetime

# --- 1. KONFIGURACJA STRONY, CSS I INICJALIZACJA PAMIĘCI SESJI ---
st.set_page_config(page_title="Analiza Danych Szkół", layout="wide", page_icon="🏫", initial_sidebar_state="expanded")

# Niestandardowy kod CSS dodający nowoczesny styl (Zaawansowany Glassmorphism, animacje, akcenty)
st.markdown("""
<style>
    /* Ukrycie domyślnego menu Streamlit */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    header {background-color: transparent !important;}
    
    /* Główne tło i czcionki */
    .stApp {
        background-image: radial-gradient(circle at top right, rgba(74, 144, 226, 0.05) 0%, transparent 40%),
                          radial-gradient(circle at bottom left, rgba(80, 227, 194, 0.05) 0%, transparent 40%);
    }

    /* Zwiększenie przestrzeni i wyśrodkowanie tytułu głównego z potężnym gradientem */
    .main-title {
        text-align: center;
        font-size: 4rem;
        font-weight: 900;
        background: linear-gradient(135deg, #4A90E2 0%, #50E3C2 50%, #B8E986 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
        margin-top: 20px;
        letter-spacing: -1.5px;
        text-shadow: 0px 10px 20px rgba(74, 144, 226, 0.1);
        animation: fadeInDown 0.8s ease-out;
    }

    /* Podtytuł */
    .sub-title {
        text-align: center; 
        color: #8892B0; 
        margin-bottom: 50px;
        font-size: 1.2rem;
        font-weight: 400;
        animation: fadeIn 1s ease-out;
    }

    /* Nowoczesne kontenery (Glassmorphism) z efektem Hover */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border: 1px solid rgba(150, 150, 150, 0.1) !important;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.1) !important;
        background: rgba(255, 255, 255, 0.02) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
    }
    
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px -15px rgba(74, 144, 226, 0.25) !important;
        border: 1px solid rgba(74, 144, 226, 0.3) !important;
    }

    /* Estetyka kontenerów Kroków (akcenty kolorystyczne) */
    .step-header {
        padding: 15px 25px;
        border-radius: 12px;
        margin-bottom: 20px;
        font-weight: 700;
        font-size: 1.3rem;
        background: linear-gradient(90deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        color: inherit;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .step-1 { border-left: 8px solid #4A90E2; box-shadow: -5px 0 15px rgba(74, 144, 226, 0.2); }
    .step-2 { border-left: 8px solid #50E3C2; box-shadow: -5px 0 15px rgba(80, 227, 194, 0.2); }
    .step-3 { border-left: 8px solid #B8E986; box-shadow: -5px 0 15px rgba(184, 233, 134, 0.2); }

    /* Wypasione Przyciski */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4A90E2 0%, #50E3C2 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 800 !important;
        font-size: 1.1rem !important;
        border-radius: 50px !important;
        padding: 0.5rem 2rem !important;
        box-shadow: 0 4px 15px rgba(80, 227, 194, 0.4) !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: scale(1.02) translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(80, 227, 194, 0.6) !important;
        filter: brightness(1.1);
    }
    
    .stButton > button[kind="secondary"] {
        border-radius: 50px !important;
        border: 2px solid rgba(150, 150, 150, 0.2) !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        background: transparent !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #4A90E2 !important;
        color: #4A90E2 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 15px rgba(74, 144, 226, 0.1) !important;
    }

    /* Metryki z gradientem */
    [data-testid="stMetricValue"] {
        font-size: 2.8rem !important;
        background: linear-gradient(135deg, #FF6B6B, #50E3C2, #4A90E2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: #8892B0 !important;
    }
    
    /* Upload plików area */
    [data-testid="stFileUploadDropzone"] {
        border: 2px dashed rgba(74, 144, 226, 0.5) !important;
        border-radius: 20px !important;
        background: rgba(74, 144, 226, 0.02) !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        background: rgba(74, 144, 226, 0.08) !important;
        border-color: #4A90E2 !important;
    }

    /* Animacje globalne */
    @keyframes fadeInDown {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
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

# Funkcja zerująca tylko postęp analizy i tindera
def zresetuj_wyniki():
    st.session_state.df_result = None
    st.session_state.to_review_indices = []
    st.session_state.review_index = 0

# Funkcja "twardego" resetu (kiedy klikamy Wgraj Nowy Plik)
def pelny_reset():
    zresetuj_wyniki()
    st.session_state.raw_df = None
    st.session_state.raw_file_name = None
    st.session_state.last_uploaded_id = None

# Funkcja aktualizująca nazwę pliku w historii
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

def pokaz_ekran_ladowania():
    ekran = st.empty()
    try:
        with open("axe.gif", "rb") as f:
            data_url = base64.b64encode(f.read()).decode("utf-8")
        with ekran.container():
            st.markdown(
                f"""
                <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 50vh;'>
                    <div style='background: rgba(255,255,255,0.05); padding: 40px; border-radius: 50%; box-shadow: 0 0 50px rgba(74, 144, 226, 0.2);'>
                        <img src="data:image/gif;base64,{data_url}" width="150" style='border-radius: 50%;'>
                    </div>
                    <h2 style='margin-top: 30px; background: linear-gradient(90deg, #4A90E2, #50E3C2); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                        Trwa ładowanie potężnych modułów... 🪓
                    </h2>
                </div>
                """, unsafe_allow_html=True)
        return ekran
    except FileNotFoundError:
        return ekran


# ==========================================
# MENU BOCZNE (SIDEBAR) - DRZEWKO HISTORII
# ==========================================
with st.sidebar:
    st.markdown("##Nawigacja")
    st.divider()
    
    if st.button("🏠 Strona Główna", use_container_width=True):
        st.session_state.page = 'home'
        st.rerun()
        
    st.markdown("### 🕒 Ostatnie Analizy")
    
    with st.expander("🏫 Wzbogacanie RSPO", expanded=True):
        if not st.session_state.history_rspo:
            st.caption("Brak historii. Przeprowadź pierwszą analizę, aby coś tu zobaczyć.")
        else:
            for item in st.session_state.history_rspo:
                if st.button(f"📄 {item['filename']} \n({item['time']})", key=f"hist_{item['id']}", use_container_width=True):
                    st.session_state.view_history_item = item
                    st.session_state.page = 'history_view'
                    st.rerun()

    with st.expander("📊 Analiza 2 (Nadchodzi)"):
        st.caption("Moduł w przygotowaniu...")

    with st.expander("🗺️ Analiza 3 (Nadchodzi)"):
        st.caption("Moduł w przygotowaniu...")


# ==========================================
# GŁÓWNA NAWIGACJA (STRONY)
# ==========================================

# STRONA GŁÓWNA
if st.session_state.page == 'home':
    st.markdown('<div class="main-title">ANALIZATOR SZKÓŁ</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Wybierz moduł analityczny i rozpocznij przetwarzanie danych na nowym poziomie</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container(border=True):
            st.markdown("### 🏫 Wzbogacanie RSPO")
            st.write("Inteligentnie dopasuj brudne dane adresowe do oficjalnej Bazy RSPO. Uzupełnij telefony, e-maile i WWW za pomocą algorytmu Fuzzy Logic.")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⚡ Uruchom Moduł", key="btn1", use_container_width=True, type="primary"):
                st.session_state.page = 'rspo_tool'
                st.rerun()
                
    with col2:
        with st.container(border=True):
            st.markdown("### 📊 Struktura (Wkrótce)")
            st.write("Moduł w przygotowaniu. Głęboka analiza struktury placówek, statystyki i wyciąganie insightów biznesowych.")
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("🔒 Zablokowane", key="btn2", use_container_width=True, disabled=True)
            
    with col3:
        with st.container(border=True):
            st.markdown("### 🗺️ Geomapping (Wkrótce)")
            st.write("Moduł w przygotowaniu. Wizualizuj rozmieszczenie placówek na interaktywnych mapach cieplnych i przestrzennych.")
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("🔒 Zablokowane", key="btn3", use_container_width=True, disabled=True)


# ==========================================
# PODGLĄD HISTORYCZNY (HISTORIA)
# ==========================================
elif st.session_state.page == 'history_view':
    item = st.session_state.view_history_item
    
    if st.button("⬅ Wróć do Menu Głównego"):
        st.session_state.page = 'home'
        st.rerun()
        
    st.markdown(f"<h1>🕒 Podgląd Zapisanej Analizy: <span style='color:#4A90E2;'>{item['filename']}</span></h1>", unsafe_allow_html=True)
    st.info(f"📅 **Data wykonania:** {item['time']}")
    
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
        type="primary",
        use_container_width=True
    )
    
    st.divider()
    st.markdown("### 👀 Szybki Podgląd Danych")
    st.dataframe(df_do_pobrania, use_container_width=True)


# ==========================================
# STRONA NARZĘDZIA RSPO
# ==========================================
elif st.session_state.page == 'rspo_tool':
    
    if st.button("⬅ Wróć do Menu Głównego"):
        st.session_state.page = 'home'
        st.rerun()
        
    st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>🏫 Ekstrakcja i Wzbogacanie Danych RSPO</h1>", unsafe_allow_html=True)

    ekran_ladowania = pokaz_ekran_ladowania()
    baza_rspo = wczytaj_baze_rspo()
    if ekran_ladowania:
        ekran_ladowania.empty()

    if baza_rspo is not None:
        st.success(f"Silnik gotowy. Baza RSPO wczytana pomyślnie ({len(baza_rspo):,} placówek).", icon="✅")
        st.write("")
        
        # Okno wgrywania plików
        uploaded_file = st.file_uploader("📂 Wgraj swój plik do uzupełnienia (Excel/CSV)", type=["csv", "xlsx"])

        # Logika zachowania pliku w pamięci
        if uploaded_file is not None:
            current_file_id = uploaded_file.name + str(uploaded_file.size)
            # Jeśli wgrano NOWY plik (inny niż poprzednio wczytany)
            if st.session_state.last_uploaded_id != current_file_id:
                zresetuj_wyniki() # Czyścimy tylko Tindera, zachowując widok
                st.session_state.last_uploaded_id = current_file_id
                st.session_state.raw_file_name = uploaded_file.name
                
                # Odczyt surowych danych do pamięci
                try:
                    if uploaded_file.name.endswith('.csv'):
                        st.session_state.raw_df = pd.read_csv(uploaded_file, sep=None, engine='python')
                    else:
                        st.session_state.raw_df = pd.read_excel(uploaded_file)
                except Exception as e:
                    st.error(f"Błąd podczas wczytywania pliku: {e}")
                    st.session_state.raw_df = None

        # --- GŁÓWNA LOGIKA NARZĘDZIA (Uruchamia się dopóki w pamięci jest plik) ---
        if st.session_state.raw_df is not None:
            try:
                # Działamy na kopii surowych danych
                df_uploaded = st.session_state.raw_df.copy()
                kolumny = df_uploaded.columns.tolist()
                
                # --- PANEL STEROWANIA ---
                if st.session_state.df_result is None: 
                    
                    # KROK 1
                    with st.container(border=True):
                        st.markdown('<div class="step-header step-1">📌 Krok 1: Mapowanie Zmiennych</div>', unsafe_allow_html=True)
                        col_a1, col_a2 = st.columns(2)
                        with col_a1:
                            kol_nazwa = st.selectbox("W której kolumnie masz NAZWĘ szkoły?", kolumny)
                        with col_a2:
                            kol_adres_lista = st.multiselect("W których kolumnach masz ADRES? (możesz wybrać kilka)", kolumny)

                        if kol_nazwa and kol_adres_lista:
                            st.caption("👀 Podgląd wybranych danych (pierwsze 5 wierszy):")
                            kolumny_do_podgladu = [kol_nazwa] + kol_adres_lista
                            st.dataframe(df_uploaded[kolumny_do_podgladu].head(5), use_container_width=True)
                        elif kol_nazwa and not kol_adres_lista:
                            st.info("Wybierz przynajmniej jedną kolumnę adresową, aby zobaczyć podgląd.")

                    # KROK 2
                    with st.container(border=True):
                        st.markdown('<div class="step-header step-2">🎯 Krok 2: Opcje dociągania danych</div>', unsafe_allow_html=True)
                        szukaj_wszystko = st.checkbox("Dociągnij automatycznie wszystkie dane z RSPO (Numer, Telefon, E-mail, WWW)", value=True)
                        
                        szukaj_rspo, szukaj_telefon, szukaj_email, szukaj_www = True, True, True, True
                        if not szukaj_wszystko:
                            cc1, cc2, cc3, cc4 = st.columns(4)
                            with cc1: szukaj_rspo = st.checkbox("Numer RSPO", value=True)
                            with cc2: szukaj_telefon = st.checkbox("Telefon")
                            with cc3: szukaj_email = st.checkbox("E-mail")
                            with cc4: szukaj_www = st.checkbox("Strona www")

                    # KROK 3
                    with st.container(border=True):
                        st.markdown('<div class="step-header step-3">🎛️ Krok 3: Czułość algorytmu</div>', unsafe_allow_html=True)
                        st.write("Dostosuj tolerancję na błędy logiczne (literówki, braki). Rekordy poniżej tego progu trafią do ręcznej weryfikacji.")
                        prog_czulosci = st.slider("Próg pewności dopasowania (%)", min_value=50, max_value=100, value=80, step=1)

                    st.markdown("<br>", unsafe_allow_html=True)

                    if st.button("Uruchom Silnik Dopasowujący", type="primary", use_container_width=True):
                        if len(kol_adres_lista) == 0:
                            st.warning("⚠️ Wybierz co najmniej jedną kolumnę w polu ADRES!")
                        else:
                            opisy_dict = baza_rspo['Znormalizowany_Opis'].to_dict()
                            my_bar = st.progress(0, text="Analizuję układ danych i dopasowuję placówki... Proszę czekać.")
                            
                            ekran_szukania = st.empty()
                            try:
                                with open("search.gif", "rb") as f:
                                    search_data_url = base64.b64encode(f.read()).decode("utf-8")
                                with ekran_szukania.container():
                                    st.markdown(f"""
                                    <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 30px; margin-bottom: 30px;'>
                                        <div style='background: rgba(255,255,255,0.05); padding: 20px; border-radius: 30px; box-shadow: 0 10px 30px rgba(80, 227, 194, 0.2);'>
                                            <img src='data:image/gif;base64,{search_data_url}' width='120' style='border-radius: 20px;'>
                                        </div>
                                        <h3 style='background: linear-gradient(45deg, #50E3C2, #4A90E2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-top: 20px;'>
                                            Przeszukuję bazę RSPO...
                                        </h3>
                                    </div>
                                    """, unsafe_allow_html=True)
                            except FileNotFoundError:
                                pass 
                            
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
                            
                            for index, row in df_uploaded.iterrows():
                                if index % 5 == 0 or index == total_rows - 1:
                                    my_bar.progress((index + 1) / total_rows, text=f"Skok kwantowy: {index+1} / {total_rows} rekordów")
                                
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

                            ekran_szukania.empty()
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

                # --- EKRAN WYNIKÓW I TINDER (Pojawia się po analizie) ---
                if st.session_state.df_result is not None:
                    
                    df_res = st.session_state.df_result
                    total_rows = len(df_res)
                    auto_count = len(df_res[df_res['Status'] == '✅ Auto-Dopasowano'])
                    manual_count = len(df_res[df_res['Status'] == '🛠️ Ręcznie dopasowano'])
                    rejected_count = len(df_res[(df_res['Status'] == '⚠️ Do weryfikacji') | (df_res['Status'] == '❌ Odrzucono') | (df_res['Status'] == 'Brak kandydata')])
                    
                    st.markdown("## 📊 Dashboard Wyników")
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("📦 Wszystkie wiersze", total_rows)
                        c2.metric("✅ Dopasowano", auto_count + manual_count, f"{round(((auto_count+manual_count)/total_rows)*100, 1)}%")
                        c3.metric("⚠️ Do weryfikacji", len(st.session_state.to_review_indices) - st.session_state.review_index)
                        c4.metric("❌ Brak / Odrzucono", rejected_count)
                    
                    st.divider()
                    
                    # --- TRYB TINDER ---
                    st.markdown("### 🕵️‍♂️ Tryb Ręcznej Weryfikacji")
                    
                    anim_id = st.session_state.review_index
                    
                    st.markdown(f"""
                    <style>
                        @keyframes slideInCard_{anim_id} {{
                            0% {{ transform: translateY(40px) scale(0.95); opacity: 0; }}
                            100% {{ transform: translateY(0) scale(1); opacity: 1; }}
                        }}
                        .tinder-card-{anim_id} {{
                            animation: slideInCard_{anim_id} 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
                        }}
                    </style>
                    """, unsafe_allow_html=True)
                    
                    if st.session_state.review_index < len(st.session_state.to_review_indices):
                        current_idx = st.session_state.to_review_indices[st.session_state.review_index]
                        row_data = df_res.loc[current_idx]
                        
                        st.info(f"🔎 Rekord **{st.session_state.review_index + 1}** z **{len(st.session_state.to_review_indices)}** wymaga Twojej decyzji:")
                        
                        st.markdown(f'<div class="tinder-card-{anim_id}">', unsafe_allow_html=True)
                        with st.container(border=True):
                            col_t1, col_t2 = st.columns(2)
                            with col_t1:
                                st.markdown("#### 📄 Twoje dane z pliku")
                                st.error(f"**🏫 Nazwa:** {row_data['_Oryginalna_Nazwa']}\n\n**📍 Adres:** {row_data['_Oryginalny_Adres']}")
                            with col_t2:
                                st.markdown(f"#### 🎯 Najlepszy kandydat RSPO (Pewność: <span style='color:#50E3C2;'>{row_data['Pewność dopasowania (%)']}%</span>)", unsafe_allow_html=True)
                                st.success(f"**🏫 Pełny Opis:** {row_data['_Kandydat_Opis']}\n\n**🔢 RSPO:** {row_data['_Kandydat_RSPO']}")
                                
                            st.write("") 
                            
                            c_btn1, c_btn_undo, c_btn2 = st.columns([2, 1, 2])
                            
                            with c_btn_undo:
                                if st.session_state.review_index > 0:
                                    if st.button("⏪ Cofnij", use_container_width=True):
                                        st.session_state.review_index -= 1
                                        idx_to_revert = st.session_state.to_review_indices[st.session_state.review_index]
                                        st.session_state.df_result.at[idx_to_revert, 'Status'] = "⚠️ Do weryfikacji"
                                        st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Numer RSPO'] = "Nie znaleziono"
                                        st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Telefon'] = "-"
                                        st.session_state.df_result.at[idx_to_revert, 'Dopasowane: E-mail'] = "-"
                                        st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Strona www'] = "-"
                                        st.rerun()
                                        
                            with c_btn1:
                                if st.button("✅ TAK, Akceptuj", use_container_width=True, type="primary"):
                                    st.session_state.df_result.at[current_idx, 'Dopasowane: Numer RSPO'] = row_data['_Kandydat_RSPO']
                                    st.session_state.df_result.at[current_idx, 'Dopasowane: Telefon'] = row_data['_Kandydat_Telefon']
                                    st.session_state.df_result.at[current_idx, 'Dopasowane: E-mail'] = row_data['_Kandydat_Email']
                                    st.session_state.df_result.at[current_idx, 'Dopasowane: Strona www'] = row_data['_Kandydat_WWW']
                                    st.session_state.df_result.at[current_idx, 'Status'] = "🛠️ Ręcznie dopasowano"
                                    st.session_state.review_index += 1
                                    st.rerun()
                                    
                            with c_btn2:
                                if st.button("❌ NIE, Odrzuć", use_container_width=True):
                                    st.session_state.df_result.at[current_idx, 'Status'] = "❌ Odrzucono"
                                    st.session_state.review_index += 1
                                    st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                    else:
                        if len(st.session_state.to_review_indices) > 0:
                            st.success("🎉 Weryfikacja zakończona! Przejrzano wszystkie przypadki graniczne. Plik jest gotowy do pobrania.")
                            if st.button("⏪ Cofnij ostatnią decyzję"):
                                st.session_state.review_index -= 1
                                idx_to_revert = st.session_state.to_review_indices[st.session_state.review_index]
                                st.session_state.df_result.at[idx_to_revert, 'Status'] = "⚠️ Do weryfikacji"
                                st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Numer RSPO'] = "Nie znaleziono"
                                st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Telefon'] = "-"
                                st.session_state.df_result.at[idx_to_revert, 'Dopasowane: E-mail'] = "-"
                                st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Strona www'] = "-"
                                st.rerun()
                        else:
                            st.success("🎉 Perfekcyjne dopasowanie algorytmu! Brak szkół granicznych do weryfikacji.")

                    st.divider()
                    
                    df_do_pobrania = df_res.drop(columns=['_Oryginalna_Nazwa', '_Oryginalny_Adres', '_Kandydat_RSPO', '_Kandydat_Telefon', '_Kandydat_Email', '_Kandydat_WWW', '_Kandydat_Opis'])
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_do_pobrania.to_excel(writer, index=False, sheet_name='Uzupełnione Dane')
                    gotowy_excel = output.getvalue()
                    
                    # --- POBIERANIE WYNIKÓW I ZMIANA NAZWY PLIKU ---
                    st.markdown("### 💾 Pobieranie Finalnych Wyników")
                    
                    aktualna_nazwa_z_historii = st.session_state.history_rspo[0]['filename'] if len(st.session_state.history_rspo) > 0 else "Rozszerzone_dane.xlsx"
                    
                    col_input, col_btn = st.columns([3, 1])
                    with col_input:
                        nazwa_uzytkownika = st.text_input(
                            "Zmień nazwę pliku przed pobraniem (opcjonalnie):", 
                            value=aktualna_nazwa_z_historii, 
                            key="user_filename_input",
                            on_change=aktualizuj_nazwe_w_historii
                        )
                    
                    if not nazwa_uzytkownika.endswith(".xlsx"):
                        nazwa_pliku = nazwa_uzytkownika + ".xlsx"
                    else:
                        nazwa_pliku = nazwa_uzytkownika
                    
                    st.download_button(
                        label=f"📥 Pobierz Plik: {nazwa_pliku}",
                        data=gotowy_excel,
                        file_name=nazwa_pliku,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True
                    )
                    
                    st.write("")
                    # Przycisk pełnego resetu połączony z funkcją "pelny_reset()"
                    if st.button("🔄 Zakończ sesję i wgraj nowy plik", use_container_width=True):
                        pelny_reset()
                        st.rerun()

                    st.write("")
                    with st.expander("👀 Podgląd obecnego stanu pliku (Top 15)", expanded=False):
                        st.dataframe(df_do_pobrania.head(15), use_container_width=True)

            except Exception as e:
                st.error(f"Wystąpił krytyczny problem przy przetwarzaniu Twojego pliku: {e}")



