import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io
import re
import base64

# Konfiguracja strony
st.set_page_config(page_title="Wzbogacanie danych z RSPO", layout="centered", page_icon="🏫")

# --- Moduł Inteligentnej Normalizacji Tekstu ---
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

# --- Funkcja ładująca bazę RSPO ---
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

# --- Funkcja wyświetlająca kręcący się topór przy starcie ---
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
                """, 
                unsafe_allow_html=True
            )
        return ekran
    except FileNotFoundError:
        return ekran

# 1. ŁADOWANIE BAZY I EKRAN POCZEKAJKI
ekran_ladowania = pokaz_ekran_ladowania()
baza_rspo = wczytaj_baze_rspo()
if ekran_ladowania:
    ekran_ladowania.empty()

# --- Właściwy interfejs aplikacji ---
st.title("🏫 Wzbogacanie danych szkół z RSPO")
st.write("Wgraj swój plik ze szkołami, wybierz odpowiednie kolumny i dopasuj brakujące informacje.")

if baza_rspo is not None:
    st.info(f"✅ Baza RSPO wczytana poprawnie ({len(baza_rspo)} placówek). Moduł NLP aktywny.")
    
    uploaded_file = st.file_uploader("Wgraj swój plik do uzupełnienia (Excel lub CSV)", type=["csv", "xlsx"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_uploaded = pd.read_csv(uploaded_file, sep=None, engine='python')
            else:
                df_uploaded = pd.read_excel(uploaded_file)
                
            kolumny = df_uploaded.columns.tolist()
            
            st.markdown("---")
            st.subheader("Krok 1: Przypisz kolumny ze swojego pliku")
            
            kol_nazwa = st.selectbox("W której kolumnie masz NAZWĘ szkoły? (Wybierz 1 kolumnę)", kolumny)
            kol_adres_lista = st.multiselect("W których kolumnach masz ADRES? (Możesz wybrać wiele)", kolumny)

            if kol_nazwa and kol_adres_lista:
                with st.expander("👀 Kliknij, aby zobaczyć podgląd wybranych danych", expanded=False):
                    kolumny_do_podgladu = [kol_nazwa] + kol_adres_lista
                    st.dataframe(df_uploaded[kolumny_do_podgladu].head(5), use_container_width=True)

            st.markdown("---")
            st.subheader("Krok 2: Jakie dane chcesz dociągnąć z bazy RSPO?")
            szukaj_wszystko = st.checkbox("Wybierz wszystkie (Numer RSPO, Telefon, E-mail, WWW)", value=True)
            
            szukaj_rspo, szukaj_telefon, szukaj_email, szukaj_www = True, True, True, True
            if not szukaj_wszystko:
                col_a, col_b = st.columns(2)
                with col_a:
                    szukaj_rspo = st.checkbox("Numer RSPO", value=True)
                    szukaj_telefon = st.checkbox("Telefon")
                with col_b:
                    szukaj_email = st.checkbox("E-mail")
                    szukaj_www = st.checkbox("Strona www")

            st.markdown("---")
            st.subheader("Krok 3: Czułość algorytmu")
            st.write("Ustaw minimalny próg podobieństwa. Zbyt niska wartość może przypisać złe szkoły, zbyt wysoka – odrzucić poprawne z drobną literówką.")
            prog_czulosci = st.slider("Wybierz próg pewności dopasowania (%)", min_value=50, max_value=100, value=80, step=1)

            st.markdown("---")
            if len(kol_adres_lista) == 0:
                st.warning("Wybierz co najmniej jedną kolumnę w polu ADRES, aby móc rozpocząć.")
            else:
                if st.button("🔎 Rozpocznij dopasowywanie", type="primary"):
                    
                    opisy_dict = baza_rspo['Znormalizowany_Opis'].to_dict()
                    my_bar = st.progress(0, text="Analizuję Twoje dane i dopasowuję placówki...")
                    
                    # Kontener na kręcącą się lupę
                    ekran_szukania = st.empty()
                    try:
                        with open("search.gif", "rb") as f:
                            search_data_url = base64.b64encode(f.read()).decode("utf-8")
                        with ekran_szukania.container():
                            st.markdown(
                                f"""
                                <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 20px;'>
                                    <img src="data:image/gif;base64,{search_data_url}" width="100">
                                    <p style='color: #888; font-style: italic; margin-top: 10px;'>Algorytm przeczesuje tysiące rekordów...</p>
                                </div>
                                """, unsafe_allow_html=True)
                    except FileNotFoundError:
                        pass 
                    
                    wyniki_rspo, wyniki_telefon, wyniki_email, wyniki_www, wyniki_pewnosc = [], [], [], [], []
                    licznik_znalezionych = 0
                    licznik_brakow = 0
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
                        
                        # Zapisujemy pewność dopasowania niezależnie od tego czy spełnia próg czy nie
                        pewnosc = najlepsze[1] if najlepsze else 0
                        wyniki_pewnosc.append(pewnosc)
                        
                        if najlepsze and pewnosc >= prog_czulosci:
                            licznik_znalezionych += 1
                            dopasowany_indeks = najlepsze[2]
                            dopasowany_wiersz = baza_rspo.loc[dopasowany_indeks]
                            
                            wyniki_rspo.append(dopasowany_wiersz.get('Numer RSPO', 'Brak'))
                            wyniki_telefon.append(dopasowany_wiersz.get('Telefon', 'Brak'))
                            wyniki_email.append(dopasowany_wiersz.get('E-mail', 'Brak'))
                            wyniki_www.append(dopasowany_wiersz.get('Strona www', 'Brak'))
                        else:
                            licznik_brakow += 1
                            wyniki_rspo.append("Nie znaleziono")
                            wyniki_telefon.append("-")
                            wyniki_email.append("-")
                            wyniki_www.append("-")

                    # Zrzucamy kolumny wynikowe
                    if szukaj_rspo: df_uploaded['Dopasowane: Numer RSPO'] = wyniki_rspo
                    if szukaj_telefon: df_uploaded['Dopasowane: Telefon'] = wyniki_telefon
                    if szukaj_email: df_uploaded['Dopasowane: E-mail'] = wyniki_email
                    if szukaj_www: df_uploaded['Dopasowane: Strona www'] = wyniki_www
                    
                    # NOWOŚĆ: Dodajemy kolumnę z procentową pewnością
                    df_uploaded['Pewność dopasowania (%)'] = wyniki_pewnosc
                    
                    ekran_szukania.empty()
                    
                    # --- DASHBOARD STATYSTYCZNY ---
                    st.success("🎉 Dopasowanie zakończone!")
                    st.markdown("### 📊 Podsumowanie wyników")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(label="Wszystkie wiersze", value=total_rows)
                    with col2:
                        st.metric(label="✅ Dopasowano poprawnie", value=licznik_znalezionych, delta=f"{round((licznik_znalezionych/total_rows)*100, 1)}%")
                    with col3:
                        st.metric(label="❌ Nie znaleziono / Poniżej progu", value=licznik_brakow, delta=f"-{round((licznik_brakow/total_rows)*100, 1)}%", delta_color="inverse")
                    
                    st.markdown("---")
                    
                    # Generowanie pliku Excel
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_uploaded.to_excel(writer, index=False, sheet_name='Uzupełnione Dane')
                    gotowy_excel = output.getvalue()
                    
                    st.download_button(
                        label="📥 Pobierz Gotowy Plik (.xlsx)",
                        data=gotowy_excel,
                        file_name="Rozszerzone_Szkoly_Z_RSPO.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
                    
                    st.write("👀 Podgląd gotowego pliku (zwróć uwagę na kolumnę 'Pewność dopasowania (%)' na samym końcu):")
                    st.dataframe(df_uploaded.head(10))

        except Exception as e:
            st.error(f"Wystąpił problem przy przetwarzaniu Twojego pliku: {e}")
