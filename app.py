import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re
import base64

# --- 1. KONFIGURACJA STRONY I INICJALIZACJA PAMIĘCI SESJI ---
st.set_page_config(page_title="Wzbogacanie danych z RSPO", layout="wide", page_icon="🏫")

if 'df_result' not in st.session_state:
    st.session_state.df_result = None
if 'to_review_indices' not in st.session_state:
    st.session_state.to_review_indices = []
if 'review_index' not in st.session_state:
    st.session_state.review_index = 0

# Funkcja do resetowania pamięci przy wgrywaniu nowego pliku
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
                    <h3 style='margin-top: 20px; color: #555;'>Topór pracuje... Rąbiemy dane z RSPO! 🪓</h3>
                </div>
                """, unsafe_allow_html=True)
        return ekran
    except FileNotFoundError:
        return ekran

# Ladowanie bazy z animacją
ekran_ladowania = pokaz_ekran_ladowania()
baza_rspo = wczytaj_baze_rspo()
if ekran_ladowania:
    ekran_ladowania.empty()


# --- 4. GŁÓWNY INTERFEJS ---
st.title("🏫 Wzbogacanie danych szkół z RSPO (Tinder Mode)")
st.write("Wgraj plik, ustaw czułość i decyduj o przypadkach granicznych!")

if baza_rspo is not None:
    st.info(f"✅ Baza RSPO wczytana poprawnie ({len(baza_rspo)} placówek).")
    
    # Wyczyszczenie sesji przy wgraniu nowego pliku
    uploaded_file = st.file_uploader("Wgraj swój plik do uzupełnienia (Excel/CSV)", type=["csv", "xlsx"], on_change=zresetuj_sesje)

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_uploaded = pd.read_csv(uploaded_file, sep=None, engine='python')
            else:
                df_uploaded = pd.read_excel(uploaded_file)
                
            kolumny = df_uploaded.columns.tolist()
            
            # --- PANEL STEROWANIA ---
            if st.session_state.df_result is None: # Pokazuj panel tylko jeśli jeszcze nie przeprowadzono analizy
                st.markdown("### Krok 1: Kolumny i Zmienne")
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    kol_nazwa = st.selectbox("W której kolumnie masz NAZWĘ szkoły?", kolumny)
                with col_a2:
                    kol_adres_lista = st.multiselect("W których kolumnach masz ADRES?", kolumny)

                st.markdown("### Krok 2: Czego szukamy i Próg czułości")
                szukaj_wszystko = st.checkbox("Dociągnij wszystko (RSPO, Telefon, E-mail, WWW)", value=True)
                
                szukaj_rspo, szukaj_telefon, szukaj_email, szukaj_www = True, True, True, True
                if not szukaj_wszystko:
                    cc1, cc2, cc3, cc4 = st.columns(4)
                    with cc1: szukaj_rspo = st.checkbox("Numer RSPO", value=True)
                    with cc2: szukaj_telefon = st.checkbox("Telefon")
                    with cc3: szukaj_email = st.checkbox("E-mail")
                    with cc4: szukaj_www = st.checkbox("Strona www")

                prog_czulosci = st.slider("Wybierz próg pewności (Poniżej tego progu szkoły trafią do 'Tindera')", min_value=50, max_value=100, value=80, step=1)

                if st.button("🔎 Rozpocznij dopasowywanie", type="primary"):
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
                                st.markdown(f"<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 20px;'><img src='data:image/gif;base64,{search_data_url}' width='100'><p style='color: #888; font-style: italic; margin-top: 10px;'>Algorytm przeczesuje tysiące rekordów...</p></div>", unsafe_allow_html=True)
                        except FileNotFoundError:
                            pass 
                        
                        # Inicjalizacja nowych kolumn
                        df_uploaded['Dopasowane: Numer RSPO'] = "Nie znaleziono"
                        df_uploaded['Dopasowane: Telefon'] = "-"
                        df_uploaded['Dopasowane: E-mail'] = "-"
                        df_uploaded['Dopasowane: Strona www'] = "-"
                        df_uploaded['Pewność dopasowania (%)'] = 0
                        df_uploaded['Status'] = "Brak kandydata"
                        
                        # Zmienne ukryte dla Tindera
                        df_uploaded['_Oryginalna_Nazwa'] = ""
                        df_uploaded['_Oryginalny_Adres'] = ""
                        df_uploaded['_Kandydat_RSPO'] = ""
                        df_uploaded['_Kandydat_Telefon'] = ""
                        df_uploaded['_Kandydat_Email'] = ""
                        df_uploaded['_Kandydat_WWW'] = ""
                        df_uploaded['_Kandydat_Opis'] = ""
                        
                        total_rows = len(df_uploaded)
                        
                        # GŁÓWNA PĘTLA
                        for index, row in df_uploaded.iterrows():
                            if index % 5 == 0 or index == total_rows - 1:
                                my_bar.progress((index + 1) / total_rows, text=f"Dopasowuję: {index+1} / {total_rows}")
                            
                            brudna_nazwa = str(row[kol_nazwa])
                            fragmenty_adresu = [str(row[col]).strip() for col in kol_adres_lista if pd.notna(row[col]) and str(row[col]).strip() != ""]
                            brudny_adres = " ".join(fragmenty_adresu)
                            
                            szukana_fraza = brudna_nazwa + ' ' + brudny_adres
                            znormalizowana_fraza = normalizuj_tekst(szukana_fraza)
                            
                            najlepsze = process.extractOne(znormalizowana_fraza, opisy_dict, scorer=fuzz.token_set_ratio)
                            
                            # Zapisanie surowych danych wejściowych
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
                                    # Automatyczny sukces
                                    df_uploaded.at[index, 'Status'] = "✅ Auto-Dopasowano"
                                    df_uploaded.at[index, 'Dopasowane: Numer RSPO'] = dopasowany_wiersz.get('Numer RSPO', 'Brak')
                                    df_uploaded.at[index, 'Dopasowane: Telefon'] = dopasowany_wiersz.get('Telefon', 'Brak')
                                    df_uploaded.at[index, 'Dopasowane: E-mail'] = dopasowany_wiersz.get('E-mail', 'Brak')
                                    df_uploaded.at[index, 'Dopasowane: Strona www'] = dopasowany_wiersz.get('Strona www', 'Brak')
                                else:
                                    # Przypadek do weryfikacji ręcznej (Tinder)
                                    df_uploaded.at[index, 'Status'] = "⚠️ Do weryfikacji"

                        ekran_szukania.empty()
                        my_bar.empty()
                        
                        # ZAPISANIE WYNIKÓW DO PAMIĘCI SESJI
                        st.session_state.df_result = df_uploaded
                        # Wyłapanie indeksów do "Tindera"
                        st.session_state.to_review_indices = df_uploaded[df_uploaded['Status'] == "⚠️ Do weryfikacji"].index.tolist()
                        st.session_state.review_index = 0
                        
                        # Odświeżenie interfejsu
                        st.rerun()

            # --- EKRAN WYNIKÓW I TINDER (Pojawia się po analizie) ---
            if st.session_state.df_result is not None:
                
                df_res = st.session_state.df_result
                total_rows = len(df_res)
                auto_count = len(df_res[df_res['Status'] == '✅ Auto-Dopasowano'])
                manual_count = len(df_res[df_res['Status'] == '🛠️ Ręcznie dopasowano'])
                rejected_count = len(df_res[(df_res['Status'] == '⚠️ Do weryfikacji') | (df_res['Status'] == '❌ Odrzucono') | (df_res['Status'] == 'Brak kandydata')])
                
                # DASHBOARD STATYSTYCZNY
                st.markdown("### 📊 Podsumowanie wyników")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Wszystkie wiersze", total_rows)
                c2.metric("✅ Dopasowano", auto_count + manual_count, f"{round(((auto_count+manual_count)/total_rows)*100, 1)}%")
                c3.metric("⚠️ Oczekuje na weryfikację", len(st.session_state.to_review_indices) - st.session_state.review_index)
                c4.metric("❌ Brak / Odrzucono", rejected_count)
                
                st.markdown("---")
                
                # --- TRYB TINDER ---
                st.markdown("### 🕵️‍♂️ Tryb Weryfikacji (Tinder dla Szkół)")
                
                if st.session_state.review_index < len(st.session_state.to_review_indices):
                    # Pobranie wiersza, który aktualnie oceniamy
                    current_idx = st.session_state.to_review_indices[st.session_state.review_index]
                    row_data = df_res.loc[current_idx]
                    
                    st.warning(f"Szkoła {st.session_state.review_index + 1} z {len(st.session_state.to_review_indices)} do weryfikacji:")
                    
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        st.info(f"**TWOJE DANE (Z pliku)**\n\n🏫 **Nazwa:** {row_data['_Oryginalna_Nazwa']}\n\n📍 **Adres:** {row_data['_Oryginalny_Adres']}")
                    with col_t2:
                        st.success(f"**NAJLEPSZY KANDYDAT RSPO** (Pewność: {row_data['Pewność dopasowania (%)']}%)\n\n🏫 **Pełny Opis:** {row_data['_Kandydat_Opis']}\n\n🔢 **RSPO:** {row_data['_Kandydat_RSPO']}")
                        
                    # Przyciski Decyzyjne
                    c_btn1, c_btn2, c_btn3 = st.columns([1, 1, 2])
                    if c_btn1.button("✅ TAK, to jest to!", use_container_width=True):
                        # Nadpisanie danych kandydata do głównych kolumn
                        st.session_state.df_result.at[current_idx, 'Dopasowane: Numer RSPO'] = row_data['_Kandydat_RSPO']
                        st.session_state.df_result.at[current_idx, 'Dopasowane: Telefon'] = row_data['_Kandydat_Telefon']
                        st.session_state.df_result.at[current_idx, 'Dopasowane: E-mail'] = row_data['_Kandydat_Email']
                        st.session_state.df_result.at[current_idx, 'Dopasowane: Strona www'] = row_data['_Kandydat_WWW']
                        st.session_state.df_result.at[current_idx, 'Status'] = "🛠️ Ręcznie dopasowano"
                        
                        st.session_state.review_index += 1
                        st.rerun() # Odświeża stronę by pokazać kolejną szkołę
                        
                    if c_btn2.button("❌ NIE, odrzuć", use_container_width=True):
                        st.session_state.df_result.at[current_idx, 'Status'] = "❌ Odrzucono"
                        st.session_state.review_index += 1
                        st.rerun()
                else:
                    if len(st.session_state.to_review_indices) > 0:
                        st.success("🎉 Przejrzano wszystkie propozycje graniczne! Plik jest gotowy do pobrania.")
                    else:
                        st.success("🎉 Algorytm był bardzo pewny swoich decyzji! Brak szkół granicznych do weryfikacji.")

                st.markdown("---")
                
                # --- POBIERANIE WYNIKÓW ---
                # Czyszczenie pliku z roboczych kolumn (by Excel był czysty)
                df_do_pobrania = df_res.drop(columns=['_Oryginalna_Nazwa', '_Oryginalny_Adres', '_Kandydat_RSPO', '_Kandydat_Telefon', '_Kandydat_Email', '_Kandydat_WWW', '_Kandydat_Opis'])
                
                # Zrzucanie zaktualizowanego DataFrame do Excela
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

                st.write("👀 Podgląd obecnego stanu pliku:")
                st.dataframe(df_do_pobrania.head(15))

        except Exception as e:
            st.error(f"Wystąpił problem przy przetwarzaniu Twojego pliku: {e}")
