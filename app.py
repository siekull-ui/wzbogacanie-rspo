import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re
import base64

# --- 1. KONFIGURACJA STRONY, CSS I INICJALIZACJA PAMIĘCI SESJI ---
st.set_page_config(page_title="Analiza Danych Szkół", layout="wide", page_icon="🏫")

# Niestandardowy kod CSS dodający nowoczesny styl (Glassmorphism, akcenty)
st.markdown("""
<style>
    /* Estetyka kontenerów Kroków (akcenty kolorystyczne) */
    .step-header {
        padding: 15px 20px;
        border-radius: 10px;
        margin-bottom: 15px;
        font-weight: 600;
        font-size: 1.2rem;
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: inherit;
    }
    .step-1 { border-left: 6px solid #4A90E2; } /* Niebieski akcent */
    .step-2 { border-left: 6px solid #50E3C2; } /* Miętowy akcent */
    .step-3 { border-left: 6px solid #B8E986; } /* Zielony akcent */
    
    /* Ukrycie domyślnego paska górnego Streamlit (dla czystszego wyglądu) */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Zwiększenie przestrzeni i wyśrodkowanie tytułu głównego */
    .main-title {
        text-align: center;
        font-size: 3rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #4A90E2, #50E3C2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 50px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'df_result' not in st.session_state:
    st.session_state.df_result = None
if 'to_review_indices' not in st.session_state:
    st.session_state.to_review_indices = []
if 'review_index' not in st.session_state:
    st.session_state.review_index = 0

def zresetuj_sesje():
    st.session_state.df_result = None
    st.session_state.to_review_indices = []
    st.session_state.review_index = 0

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
                    <img src="data:image/gif;base64,{data_url}" width="150">
                    <h3 style='margin-top: 20px; color: #555;'>Trwa ładowanie modułów oświatowych... 🪓</h3>
                </div>
                """, unsafe_allow_html=True)
        return ekran
    except FileNotFoundError:
        return ekran

# ==========================================
# GŁÓWNA NAWIGACJA (STRONY)
# ==========================================

# STRONA GŁÓWNA
if st.session_state.page == 'home':
    st.markdown('<div class="main-title">Analiza Danych Szkół</div>', unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: gray; margin-bottom: 50px;'>Wybierz moduł analityczny, aby rozpocząć pracę</h4>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container(border=True):
            st.markdown("### 🏫 Wzbogacanie RSPO")
            st.write("Dopasuj brudne dane adresowe do oficjalnej Bazy RSPO, uzupełnij telefony i e-maile.")
            st.write("")
            if st.button("Uruchom Moduł", key="btn1", use_container_width=True, type="primary"):
                st.session_state.page = 'rspo_tool'
                st.rerun()
                
    with col2:
        with st.container(border=True):
            st.markdown("### 📊 Analiza 2 (Wkrótce)")
            st.write("Moduł w przygotowaniu. Będzie służył do analizy struktury placówek i statystyk.")
            st.write("")
            st.button("Zablokowane", key="btn2", use_container_width=True, disabled=True)
            
    with col3:
        with st.container(border=True):
            st.markdown("### 🗺️ Analiza 3 (Wkrótce)")
            st.write("Moduł w przygotowaniu. Będzie wizualizował rozmieszczenie placówek na mapie.")
            st.write("")
            st.button("Zablokowane", key="btn3", use_container_width=True, disabled=True)


# STRONA NARZĘDZIA RSPO
elif st.session_state.page == 'rspo_tool':
    
    # Przycisk powrotu
    if st.button("⬅ Wróć do Menu Głównego"):
        st.session_state.page = 'home'
        st.rerun()
        
    st.title("🏫 Wzbogacanie danych szkół z RSPO")
    st.write("Wgraj plik, przypisz zmienne i decyduj o przypadkach granicznych!")

    # Ladowanie bazy z animacją (uruchomi się tylko raz przy wejściu)
    ekran_ladowania = pokaz_ekran_ladowania()
    baza_rspo = wczytaj_baze_rspo()
    if ekran_ladowania:
        ekran_ladowania.empty()

    if baza_rspo is not None:
        st.success(f"Baza RSPO wczytana pomyślnie ({len(baza_rspo)} placówek). Silnik gotowy do pracy.", icon="✅")
        
        uploaded_file = st.file_uploader("Wgraj swój plik do uzupełnienia (Excel/CSV)", type=["csv", "xlsx"], on_change=zresetuj_sesje)

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_uploaded = pd.read_csv(uploaded_file, sep=None, engine='python')
                else:
                    df_uploaded = pd.read_excel(uploaded_file)
                    
                kolumny = df_uploaded.columns.tolist()
                
                # --- PANEL STEROWANIA ---
                if st.session_state.df_result is None: 
                    
                    # KROK 1 (Niebieski akcent)
                    with st.container(border=True):
                        st.markdown('<div class="step-header step-1">Krok 1: Mapowanie Zmiennych</div>', unsafe_allow_html=True)
                        col_a1, col_a2 = st.columns(2)
                        with col_a1:
                            kol_nazwa = st.selectbox("W której kolumnie masz NAZWĘ szkoły?", kolumny)
                        with col_a2:
                            kol_adres_lista = st.multiselect("W których kolumnach masz ADRES?", kolumny)

                        if kol_nazwa and kol_adres_lista:
                            st.caption("👀 Podgląd wybranych danych (pierwsze 5 wierszy):")
                            kolumny_do_podgladu = [kol_nazwa] + kol_adres_lista
                            st.dataframe(df_uploaded[kolumny_do_podgladu].head(5), use_container_width=True)
                        elif kol_nazwa and not kol_adres_lista:
                            st.info("Wybierz przynajmniej jedną kolumnę adresową, aby zobaczyć podgląd.")

                    # KROK 2 (Miętowy akcent)
                    with st.container(border=True):
                        st.markdown('<div class="step-header step-2">Krok 2: Opcje dociągania danych</div>', unsafe_allow_html=True)
                        szukaj_wszystko = st.checkbox("Dociągnij wszystkie dane z RSPO (Numer, Telefon, E-mail, WWW)", value=True)
                        
                        szukaj_rspo, szukaj_telefon, szukaj_email, szukaj_www = True, True, True, True
                        if not szukaj_wszystko:
                            cc1, cc2, cc3, cc4 = st.columns(4)
                            with cc1: szukaj_rspo = st.checkbox("Numer RSPO", value=True)
                            with cc2: szukaj_telefon = st.checkbox("Telefon")
                            with cc3: szukaj_email = st.checkbox("E-mail")
                            with cc4: szukaj_www = st.checkbox("Strona www")

                    # KROK 3 (Zielony akcent)
                    with st.container(border=True):
                        st.markdown('<div class="step-header step-3">Krok 3: Czułość algorytmu</div>', unsafe_allow_html=True)
                        st.write("Dostosuj tolerancję na błędy. Rekordy poniżej tego progu trafią do ręcznej weryfikacji.")
                        prog_czulosci = st.slider("Próg pewności dopasowania (%)", min_value=50, max_value=100, value=80, step=1)

                    st.markdown("<br>", unsafe_allow_html=True)

                    if st.button("🚀 Rozpocznij dopasowywanie", type="primary", use_container_width=True):
                        if len(kol_adres_lista) == 0:
                            st.warning("Wybierz co najmniej jedną kolumnę w polu ADRES!")
                        else:
                            opisy_dict = baza_rspo['Znormalizowany_Opis'].to_dict()
                            my_bar = st.progress(0, text="Analizuję Twoje dane i dopasowuję placówki...")
                            
                            ekran_szukania = st.empty()
                            try:
                                with open("search.gif", "rb") as f:
                                    search_data_url = base64.b64encode(f.read()).decode("utf-8")
                                with ekran_szukania.container():
                                    st.markdown(f"<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 20px;'><img src='data:image/gif;base64,{search_data_url}' width='100'><p style='color: #888; font-style: italic; margin-top: 10px;'>Silnik analityczny pracuje...</p></div>", unsafe_allow_html=True)
                            except FileNotFoundError:
                                pass 
                            
                            # Inicjalizacja nowych kolumn
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
                                    my_bar.progress((index + 1) / total_rows, text=f"Dopasowuję: {index+1} / {total_rows}")
                                
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
                            st.rerun()

                # --- EKRAN WYNIKÓW I TINDER (Pojawia się po analizie) ---
                if st.session_state.df_result is not None:
                    
                    df_res = st.session_state.df_result
                    total_rows = len(df_res)
                    auto_count = len(df_res[df_res['Status'] == '✅ Auto-Dopasowano'])
                    manual_count = len(df_res[df_res['Status'] == '🛠️ Ręcznie dopasowano'])
                    rejected_count = len(df_res[(df_res['Status'] == '⚠️ Do weryfikacji') | (df_res['Status'] == '❌ Odrzucono') | (df_res['Status'] == 'Brak kandydata')])
                    
                    st.markdown("### 📊 Podsumowanie wyników")
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Wszystkie wiersze", total_rows)
                        c2.metric("✅ Dopasowano", auto_count + manual_count, f"{round(((auto_count+manual_count)/total_rows)*100, 1)}%")
                        c3.metric("⚠️ Oczekuje na weryfikację", len(st.session_state.to_review_indices) - st.session_state.review_index)
                        c4.metric("❌ Brak / Odrzucono", rejected_count)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # --- TRYB TINDER ---
                    st.markdown("### 🕵️‍♂️ Tryb Weryfikacji (Tinder)")
                    
                    # Wstrzyknięcie CSS dla efektu przesuwania/wskakiwania karty
                    st.markdown("""
                    <style>
                        @keyframes slideInCard {
                            0% { transform: translateY(40px) scale(0.95); opacity: 0; }
                            100% { transform: translateY(0) scale(1); opacity: 1; }
                        }
                        .tinder-animated-card {
                            animation: slideInCard 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
                        }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    if st.session_state.review_index < len(st.session_state.to_review_indices):
                        current_idx = st.session_state.to_review_indices[st.session_state.review_index]
                        row_data = df_res.loc[current_idx]
                        
                        st.warning(f"Szkoła {st.session_state.review_index + 1} z {len(st.session_state.to_review_indices)} do weryfikacji:")
                        
                        # Otwarcie animowanego kontenera karty
                        st.markdown('<div class="tinder-animated-card">', unsafe_allow_html=True)
                        with st.container(border=True):
                            col_t1, col_t2 = st.columns(2)
                            with col_t1:
                                st.info(f"**TWOJE DANE (Z pliku)**\n\n🏫 **Nazwa:** {row_data['_Oryginalna_Nazwa']}\n\n📍 **Adres:** {row_data['_Oryginalny_Adres']}")
                            with col_t2:
                                st.success(f"**NAJLEPSZY KANDYDAT RSPO** (Pewność: {row_data['Pewność dopasowania (%)']}%)\n\n🏫 **Pełny Opis:** {row_data['_Kandydat_Opis']}\n\n🔢 **RSPO:** {row_data['_Kandydat_RSPO']}")
                                
                            st.write("") # Spacing
                            
                            # Dodanie przycisku Cofnij (układ 1:2:2)
                            c_btn1, c_btn_undo, c_btn2 = st.columns([2, 1, 2])
                            
                            with c_btn_undo:
                                if st.session_state.review_index > 0:
                                    if st.button("⏪ Cofnij", use_container_width=True):
                                        # Zmniejszamy indeks o 1
                                        st.session_state.review_index -= 1
                                        idx_to_revert = st.session_state.to_review_indices[st.session_state.review_index]
                                        # Czyścimy decyzję w głównej tabeli
                                        st.session_state.df_result.at[idx_to_revert, 'Status'] = "⚠️ Do weryfikacji"
                                        st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Numer RSPO'] = "Nie znaleziono"
                                        st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Telefon'] = "-"
                                        st.session_state.df_result.at[idx_to_revert, 'Dopasowane: E-mail'] = "-"
                                        st.session_state.df_result.at[idx_to_revert, 'Dopasowane: Strona www'] = "-"
                                        st.rerun()
                                        
                            with c_btn1:
                                if st.button("✅ TAK, to jest to!", use_container_width=True):
                                    st.session_state.df_result.at[current_idx, 'Dopasowane: Numer RSPO'] = row_data['_Kandydat_RSPO']
                                    st.session_state.df_result.at[current_idx, 'Dopasowane: Telefon'] = row_data['_Kandydat_Telefon']
                                    st.session_state.df_result.at[current_idx, 'Dopasowane: E-mail'] = row_data['_Kandydat_Email']
                                    st.session_state.df_result.at[current_idx, 'Dopasowane: Strona www'] = row_data['_Kandydat_WWW']
                                    st.session_state.df_result.at[current_idx, 'Status'] = "🛠️ Ręcznie dopasowano"
                                    
                                    st.session_state.review_index += 1
                                    st.rerun()
                                    
                            with c_btn2:
                                if st.button("❌ NIE, odrzuć", use_container_width=True):
                                    st.session_state.df_result.at[current_idx, 'Status'] = "❌ Odrzucono"
                                    st.session_state.review_index += 1
                                    st.rerun()
                                    
                        # Zamknięcie animowanego kontenera
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                    else:
                        if len(st.session_state.to_review_indices) > 0:
                            st.success("🎉 Przejrzano wszystkie propozycje graniczne! Plik jest gotowy do pobrania.")
                            # Możliwość cofnięcia z samego końca, jeśli ostatnia decyzja była błędna
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
                            st.success("🎉 Algorytm był bardzo pewny swoich decyzji! Brak szkół granicznych do weryfikacji.")

                    st.markdown("---")
                    
                    df_do_pobrania = df_res.drop(columns=['_Oryginalna_Nazwa', '_Oryginalny_Adres', '_Kandydat_RSPO', '_Kandydat_Telefon', '_Kandydat_Email', '_Kandydat_WWW', '_Kandydat_Opis'])
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_do_pobrania.to_excel(writer, index=False, sheet_name='Uzupełnione Dane')
                    gotowy_excel = output.getvalue()
                    
                    st.download_button(
                        label="📥 Pobierz Gotowy, Zweryfikowany Plik (.xlsx)",
                        data=gotowy_excel,
                        file_name="Rozszerzone_Szkoly_Z_RSPO.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True
                    )
                    
                    if st.button("🔄 Wgraj nowy plik / Zresetuj panel"):
                        zresetuj_sesje()
                        st.rerun()

                    with st.expander("👀 Pokaż podgląd obecnego stanu pliku", expanded=True):
                        st.dataframe(df_do_pobrania.head(15), use_container_width=True)

            except Exception as e:
                st.error(f"Wystąpił problem przy przetwarzaniu Twojego pliku: {e}")


