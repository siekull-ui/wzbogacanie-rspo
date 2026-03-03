import streamlit as st

# Konfiguracja - domyślnie zwinięty sidebar
st.set_page_config(page_title="Neumorficzna Aplikacja", layout="wide", initial_sidebar_state="collapsed")

# Inicjalizacja stanu sesji do zarządzania "stronami"
if 'aktualna_strona' not in st.session_state:
    st.session_state.aktualna_strona = 'Strona Główna'

# --- GŁÓWNY CSS (Neumorfizm, Glassmorfizm i ukrywanie domyślnych elementów) ---
st.markdown("""
<style>
    /* Tło pod neumorfizm */
    .stApp {
        background-color: #e0e5ec;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Ukrycie domyślnego nagłówka Streamlita */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}

    /* STYLOWANIE NATYWNYCH PRZYCISKÓW STREAMLITA NA NEUMORFIZM */
    div.stButton > button {
        background-color: #e0e5ec !important;
        color: #555 !important;
        border: none !important;
        border-radius: 12px !important;
        box-shadow: 6px 6px 12px #b8bcc2, -6px -6px 12px #ffffff !important;
        transition: all 0.2s ease !important;
        width: 100%;
        height: 50px;
        font-weight: 600 !important;
        letter-spacing: 1px;
    }
    
    /* Efekt wklęśnięcia przy kliknięciu/aktywności */
    div.stButton > button:active, div.stButton > button:focus {
        box-shadow: inset 6px 6px 12px #b8bcc2, inset -6px -6px 12px #ffffff !important;
        color: #0078D4 !important;
    }

    /* NEUMORFICZNY PANEL GŁÓWNY (Wypukłość z tła) */
    .neumorphic-panel {
        background: #e0e5ec;
        border-radius: 30px;
        box-shadow: 15px 15px 30px #b8bcc2, -15px -15px 30px #ffffff;
        padding: 60px;
        text-align: center;
        margin: 20px auto 60px auto;
        max-width: 800px;
        color: #444;
    }
    
    .neumorphic-panel h1 {
        font-weight: 300;
        letter-spacing: 3px;
        margin-bottom: 10px;
    }

    /* OBSZAR ANALIZATORÓW - GLASSMORFIZM (z poprzedniej wersji) */
    .glass-grid {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        padding: 20px;
    }

    .glass-card {
        flex: 1;
        height: 220px;
        border-radius: 15px;
        padding: 20px;
        position: relative;
        overflow: hidden;
        background: rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.4);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
        color: #222;
    }

    .glass-card::before {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        opacity: 0.15;
        background-image: url('data:image/svg+xml,%3Csvg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noiseFilter"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noiseFilter)"/%3E%3C/svg%3E');
        pointer-events: none;
        z-index: -1;
    }

</style>
""", unsafe_allow_html=True)


# --- GÓRNY PASEK NAWIGACJI (Ostylowane przyciski) ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("STRONA GŁÓWNA"):
        st.session_state.aktualna_strona = 'Strona Główna'
with col2:
    if st.button("ANALIZATOR 1"):
        st.session_state.aktualna_strona = 'Analizator 1'
with col3:
    if st.button("ANALIZATOR 2"):
        st.session_state.aktualna_strona = 'Analizator 2'
with col4:
    if st.button("ANALIZATOR 3"):
        st.session_state.aktualna_strona = 'Analizator 3'

st.markdown("<br><br>", unsafe_allow_html=True)


# --- LOGIKA WYŚWIETLANIA STRON ---

if st.session_state.aktualna_strona == 'Strona Główna':
    # WIDOK STRONY GŁÓWNEJ
    
    st.markdown("""
    <div class="neumorphic-panel">
        <h1>GŁÓWNY PANEL</h1>
        <p>Płynne uwypuklenie z tła. Brak ostrych krawędzi, gra światła i cienia.</p>
    </div>
    
    <div style="text-align: center; margin-top: 40px; margin-bottom: 20px;">
        <h3 style="color: #666; font-weight: 300; letter-spacing: 2px;">PRZEGLĄD MODUŁÓW</h3>
    </div>
    
    <div class="glass-grid">
        <div class="glass-card">
            <h4 style="border-bottom: 1px solid rgba(0,0,0,0.1); padding-bottom: 10px;">Analizator 1</h4>
            <p>Zaszronione szkło z efektem ziarna.</p>
        </div>
        <div class="glass-card">
            <h4 style="border-bottom: 1px solid rgba(0,0,0,0.1); padding-bottom: 10px;">Analizator 2</h4>
            <p>Idealne miejsce na zajawkę tego, co potrafi moduł.</p>
        </div>
        <div class="glass-card">
            <h4 style="border-bottom: 1px solid rgba(0,0,0,0.1); padding-bottom: 10px;">Analizator 3</h4>
            <p>Prześwitujący kontener unoszący się nad interfejsem.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    # WIDOK KONKRETNEGO ANALIZATORA (1, 2 lub 3)
    
    nazwa_analizatora = st.session_state.aktualna_strona
    
    # Wyświetlenie treści na głównej przestrzeni
    st.markdown(f"<h2 style='color: #444;'>Jesteś w: {nazwa_analizatora}</h2>", unsafe_allow_html=True)
    st.write("Tutaj znajdzie się cała logika przetwarzania, wgrywanie plików, wykresy itd.")
    
    # Uruchomienie wysuwanego paska bocznego (Sidebar) TYLKO dla analizatorów
    with st.sidebar:
        st.markdown(f"<h3 style='color: #444;'>Historia - {nazwa_analizatora}</h3>", unsafe_allow_html=True)
        st.write("Ostatnie akcje:")
        
        # Przykładowa historia (można to później podpiąć pod bazę/stan sesji)
        st.info("🕒 10:42 - Wgrano plik data.csv")
        st.info("🕒 10:45 - Wygenerowano wykres rozrzutu")
        st.info("🕒 10:50 - Zapisano raport do PDF")
        
        st.markdown("---")
        st.write("*Ta zakładka widoczna jest tylko podczas pracy z analizatorem.*")
