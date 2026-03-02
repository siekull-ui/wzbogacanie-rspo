import streamlit as st
import pandas as pd
from thefuzz import process, fuzz
import io

# Konfiguracja strony
st.set_page_config(page_title="Wzbogacanie danych z RSPO", layout="centered", page_icon="🏫")

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
        
        return df_rspo
    except Exception as e:
        st.error(f"Wystąpił błąd przy wczytywaniu bazy: {e}")
        return None

# Ładujemy bazę w tle
baza_rspo = wczytaj_baze_rspo()

st.title("🏫 Wzbogacanie danych szkół z RSPO")
st.write("Wgraj swój plik ze szkołami, wybierz odpowiednie kolumny i pozwól systemowi dopasować brakujące informacje.")

if baza_rspo is not None:
    st.info(f"✅ Baza RSPO wczytana poprawnie (zawiera {len(baza_rspo)} placówek).")
    
    uploaded_file = st.file_uploader("Wgraj swój plik do uzupełnienia (Excel lub CSV)", type=["csv", "xlsx"])

    if uploaded_file is not None:
        st.success("Plik wgrany poprawnie!")
        
        try:
            if uploaded_file.name.endswith('.csv'):
                df_uploaded = pd.read_csv(uploaded_file, sep=None, engine='python')
            else:
                df_uploaded = pd.read_excel(uploaded_file)
                
            kolumny = df_uploaded.columns.tolist()
            
            st.markdown("---")
            st.subheader("Krok 1: Przypisz kolumny ze swojego pliku")
            
            kol_nazwa = st.selectbox("W której kolumnie masz NAZWĘ szkoły? (Wybierz 1 kolumnę)", kolumny)
            
            kol_adres_lista = st.multiselect(
                "W których kolumnach masz ADRES? (Możesz wybrać wiele: np. miasto, kod pocztowy, ulica)", 
                kolumny
            )

            # --- NOWOŚĆ: Podgląd wybranych danych ---
            if kol_nazwa and kol_adres_lista:
                st.write("**Podgląd wybranych danych (pierwsze 5 wierszy):**")
                # Tworzymy listę kolumn, które chcemy pokazać (nazwa + wszystkie wybrane części adresu)
                kolumny_do_podgladu = [kol_nazwa] + kol_adres_lista
                # Pokazujemy elegancką tabelkę z pierwszymi 5 wierszami
                st.dataframe(df_uploaded[kolumny_do_podgladu].head(5), use_container_width=True)
            elif kol_nazwa and not kol_adres_lista:
                st.info("Wybierz przynajmniej jedną kolumnę adresową, aby zobaczyć podgląd.")
            # ----------------------------------------

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
            
            if len(kol_adres_lista) == 0:
                st.warning("Wybierz co najmniej jedną kolumnę w polu ADRES, aby móc rozpocząć.")
            else:
                if st.button("🔎 Rozpocznij dopasowywanie", type="primary"):
                    
                    opisy_rspo = baza_rspo['Pelny_Opis'].tolist()
                    my_bar = st.progress(0, text="Analizuję Twoje dane i dopasowuję placówki...")
                    
                    wyniki_rspo, wyniki_telefon, wyniki_email, wyniki_www = [], [], [], []
                    total_rows = len(df_uploaded)
                    
                    for index, row in df_uploaded.iterrows():
                        if index % 5 == 0 or index == total_rows - 1:
                            my_bar.progress((index + 1) / total_rows, text=f"Dopasowuję: {index+1} / {total_rows}")
                        
                        brudna_nazwa = str(row[kol_nazwa])
                        
                        fragmenty_adresu = []
                        for col in kol_adres_lista:
                            wartosc = row[col]
                            if pd.notna(wartosc) and str(wartosc).strip() != "":
                                fragmenty_adresu.append(str(wartosc).strip())
                        
                        brudny_adres = " ".join(fragmenty_adresu)
                        szukana_fraza = brudna_nazwa + ' ' + brudny_adres
                        
                        najlepsze = process.extractOne(szukana_fraza, opisy_rspo, scorer=fuzz.token_set_ratio)
                        
                        if najlepsze and najlepsze[1] > 80:
                            dopasowany_wiersz = baza_rspo[baza_rspo['Pelny_Opis'] == najlepsze[0]].iloc[0]
                            wyniki_rspo.append(dopasowany_wiersz.get('Numer RSPO', 'Brak'))
                            wyniki_telefon.append(dopasowany_wiersz.get('Telefon', 'Brak'))
                            wyniki_email.append(dopasowany_wiersz.get('E-mail', 'Brak'))
                            wyniki_www.append(dopasowany_wiersz.get('Strona www', 'Brak'))
                        else:
                            wyniki_rspo.append("Nie znaleziono")
                            wyniki_telefon.append("-")
                            wyniki_email.append("-")
                            wyniki_www.append("-")

                    if szukaj_rspo: df_uploaded['Dopasowane: Numer RSPO'] = wyniki_rspo
                    if szukaj_telefon: df_uploaded['Dopasowane: Telefon'] = wyniki_telefon
                    if szukaj_email: df_uploaded['Dopasowane: E-mail'] = wyniki_email
                    if szukaj_www: df_uploaded['Dopasowane: Strona www'] = wyniki_www
                    
                    st.success("🎉 Dopasowanie zakończone!")
                    
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
                    
                    st.write("Podgląd pierwszych 5 wierszy gotowego pliku:")
                    st.dataframe(df_uploaded.head(5))

        except Exception as e:
            st.error(f"Wystąpił problem przy przetwarzaniu Twojego pliku: {e}")
