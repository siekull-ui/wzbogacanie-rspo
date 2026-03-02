import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io

# Konfiguracja strony
st.set_page_config(page_title="Wzbogacanie danych z RSPO", layout="centered", page_icon="🏫")

# --- Funkcja ładująca bazę RSPO (uruchamia się tylko raz) ---
@st.cache_data
def wczytaj_baze_rspo():
    try:
        # Próbujemy wczytać bazę RSPO z tego samego folderu
        df_rspo = pd.read_csv("baza_rspo.csv", sep=None, engine='python', encoding='utf-8')
        
        # Standaryzacja kolumn pod to, co mamy w pliku (Nazwa, Miejscowość, Ulica, Numer budynku)
        nazwa = df_rspo['Nazwa'].fillna('')
        miejscowosc = df_rspo['Miejscowość'].fillna('')
        ulica = df_rspo['Ulica'].fillna('')
        nr_budynku = df_rspo['Numer budynku'].astype(str).replace('nan', '').fillna('')
        
        # Tworzymy kolumnę pomocniczą do wyszukiwania złączając dane
        df_rspo['Pelny_Opis'] = nazwa + ' ' + miejscowosc + ' ' + ulica + ' ' + nr_budynku
        
        # Usuwamy podwójne spacje
        df_rspo['Pelny_Opis'] = df_rspo['Pelny_Opis'].str.replace('  ', ' ')
        
        return df_rspo
    except FileNotFoundError:
        st.error("Błąd: Nie znaleziono pliku 'baza_rspo.csv' w folderze z aplikacją! Upewnij się, że plik ma dokładnie taką nazwę.")
        return None
    except Exception as e:
        st.error(f"Wystąpił nieoczekiwany błąd przy wczytywaniu bazy: {e}")
        return None

# Ładujemy bazę w tle
baza_rspo = wczytaj_baze_rspo()

st.title("Wzbogacanie danych szkół z RSPO")
st.write("Wgraj swój plik ze szkołami, wybierz odpowiednie kolumny i pozwól systemowi dopasować brakujące informacje.")

if baza_rspo is not None:
    st.info(f"✅ Baza RSPO wczytana poprawnie (zawiera {len(baza_rspo)} placówek).")
    
    # 1. Miejsce na wgranie pliku
    uploaded_file = st.file_uploader("Wgraj swój plik do uzupełnienia (Excel lub CSV)", type=["csv", "xlsx"])

    if uploaded_file is not None:
        st.success("Plik wgrany poprawnie!")
        
        try:
            # Wczytywanie wgranego pliku
            if uploaded_file.name.endswith('.csv'):
                df_uploaded = pd.read_csv(uploaded_file, sep=None, engine='python')
            else:
                df_uploaded = pd.read_excel(uploaded_file)
                
            kolumny = df_uploaded.columns.tolist()
            
            st.markdown("---")
            st.subheader("Krok 1: Przypisz kolumny ze swojego pliku")
            
            col1, col2 = st.columns(2)
            with col1:
                kol_nazwa = st.selectbox("W której kolumnie masz Nazwę szkoły?", kolumny)
            with col2:
                kol_adres = st.selectbox("W której kolumnie masz Adres szkoły?", kolumny)

            st.markdown("---")
            st.subheader("Krok 2: Jakie dane chcesz dociągnąć z bazy RSPO?")
            
            szukaj_wszystko = st.checkbox("Wybierz wszystkie (Numer RSPO, Telefon, E-mail, WWW)", value=True)
            
            szukaj_rspo = True
            szukaj_telefon = True
            szukaj_email = True
            szukaj_www = True
            
            if not szukaj_wszystko:
                col_a, col_b = st.columns(2)
                with col_a:
                    szukaj_rspo = st.checkbox("Numer RSPO", value=True)
                    szukaj_telefon = st.checkbox("Telefon")
                with col_b:
                    szukaj_email = st.checkbox("E-mail")
                    szukaj_www = st.checkbox("Strona www")

            st.markdown("---")
            
            # Przycisk uruchamiający algorytm
            if st.button("Rozpocznij dopasowywanie", type="primary"):
                
                # Lista tekstów z bazy RSPO do przeszukiwania
                opisy_rspo = baza_rspo['Pelny_Opis'].tolist()
                
                # Inicjalizacja pasków postępu
                progress_text = "Analizuję Twoje dane i dopasowuję placówki..."
                my_bar = st.progress(0, text=progress_text)
                
                wyniki_rspo, wyniki_telefon, wyniki_email, wyniki_www = [], [], [], []
                
                total_rows = len(df_uploaded)
                
                for index, row in df_uploaded.iterrows():
                    # Aktualizacja paska (co 5 wierszy by nie obciążać interfejsu)
                    if index % 5 == 0 or index == total_rows - 1:
                        my_bar.progress((index + 1) / total_rows, text=f"Dopasowuję: {index+1} / {total_rows}")
                    
                    # Łączymy brudną nazwę i brudny adres
                    szukana_fraza = str(row[kol_nazwa]) + ' ' + str(row[kol_adres])
                    
                    # Funkcja Fuzzy Matching 
                    najlepsze = process.extractOne(szukana_fraza, opisy_rspo, scorer=fuzz.token_set_ratio)
                    
                    # Próg odcięcia - 80 punktów podobieństwa (do dostosowania, jeśli zajdzie potrzeba)
                    if najlepsze and najlepsze[1] > 80:
                        # Pobieramy konkretny, dopasowany wiersz z bazy
                        dopasowany_wiersz = baza_rspo[baza_rspo['Pelny_Opis'] == najlepsze[0]].iloc[0]
                        
                        wyniki_rspo.append(dopasowany_wiersz.get('Numer RSPO', 'Brak'))
                        wyniki_telefon.append(dopasowany_wiersz.get('Telefon', 'Brak'))
                        wyniki_email.append(dopasowany_wiersz.get('E-mail', 'Brak'))
                        wyniki_www.append(dopasowany_wiersz.get('Strona www', 'Brak'))
                    else:
                        # Jeśli poniżej 80% pewności, uznajemy, że nie znaleziono dopasowania
                        wyniki_rspo.append("Nie znaleziono")
                        wyniki_telefon.append("-")
                        wyniki_email.append("-")
                        wyniki_www.append("-")

                # Wrzucenie dopasowanych danych do tabeli wynikowej
                if szukaj_rspo: df_uploaded['Dopasowane: Numer RSPO'] = wyniki_rspo
                if szukaj_telefon: df_uploaded['Dopasowane: Telefon'] = wyniki_telefon
                if szukaj_email: df_uploaded['Dopasowane: E-mail'] = wyniki_email
                if szukaj_www: df_uploaded['Dopasowane: Strona www'] = wyniki_www
                
                st.success("Dopasowanie zakończone!")
                
                # Zapisanie gotowego pliku i stworzenie przycisku do pobierania
                # (Zabezpieczone UTF-8 z BOM, żeby polski Excel nie psuł polskich znaków)
                csv = df_uploaded.to_csv(index=False, sep=';', encoding='utf-8-sig')
                
                st.download_button(
                    label="📥 Pobierz Gotowy Plik (.csv)",
                    data=csv,
                    file_name="Rozszerzone_Szkoly_Z_RSPO.csv",
                    mime="text/csv",
                    type="primary"
                )
                
                st.write("Podgląd pierwszych 5 wierszy:")
                st.dataframe(df_uploaded.head(5))

        except Exception as e:
            st.error(f"Wystąpił problem przy wczytywaniu Twojego pliku: {e}")