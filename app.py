import streamlit as st

# Konfiguracja strony musi być pierwszym poleceniem
st.set_page_config(page_title="Minimalistyczne Analizatory", layout="wide", initial_sidebar_state="collapsed")

# Wstrzykiwanie niestandardowego CSS
st.markdown("""
<style>
    /* Ukrycie domyślnych elementów Streamlita dla czystości */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Główne tło - neumorfizm wymaga specyficznego, lekko szarego tła */
    .stApp {
        background-color: #e0e5ec;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* NIERUCHOMY NAGŁÓWEK */
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background-color: #e0e5ec;
        padding: 15px 30px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        z-index: 9999;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    .header-logo {
        font-size: 1.2rem;
        font-weight: bold;
        color: #333;
    }
    
    .nav-buttons {
        display: flex;
        gap: 15px;
    }

    /* NEUMORFICZNE PRZYCISKI (efekt wklęśnięcia) */
    .nav-btn {
        padding: 10px 20px;
        border-radius: 8px;
        background: #e0e5ec;
        color: #333;
        text-decoration: none;
        font-weight: 600;
        /* Wypukły cień */
        box-shadow: 5px 5px 10px #b8bcc2, -5px -5px 10px #ffffff;
        transition: all 0.2s ease;
        cursor: pointer;
        border: none;
    }
    
    .nav-btn:active {
        /* Wklęsły cień przy kliknięciu */
        box-shadow: inset 5px 5px 10px #b8bcc2, inset -5px -5px 10px #ffffff;
        color: #0078D4;
    }

    /* ODCINANIE OD GÓRY (żeby header nie zasłaniał treści) */
    .content-spacer {
        margin-top: 80px; 
    }

    /* TYTUŁ STRONY - DWA KWADRATY */
    .title-area {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 40px auto;
        width: 100%;
        max-width: 800px;
    }
    
    .square {
        width: 300px;
        height: 300px;
        display: flex;
        justify-content: center;
        align-items: center;
        color: white;
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        transition: transform 0.3s;
    }
    
    .square:hover {
        transform: scale(1.02);
    }

    .square-left {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); /* Głęboki niebieski */
        border-radius: 20px 0 0 20px;
        box-shadow: -10px 10px 20px rgba(0,0,0,0.15);
    }

    .square-right {
        background: linear-gradient(135deg, #ff758c 0%, #ff7eb3 100%); /* Ciepły róż/czerwień */
        border-radius: 0 20px 20px 0;
        box-shadow: 10px 10px 20px rgba(0,0,0,0.15);
        /* Ciekawy efekt nałożenia */
        margin-left: -10px; 
        mix-blend-mode: multiply;
    }

    /* OBSZAR ANALIZATORÓW - GLASSMORFIZM + SZUM */
    .glass-grid {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        margin-top: 60px;
        padding: 20px;
    }

    .glass-card {
        flex: 1;
        height: 250px;
        border-radius: 15px;
        padding: 20px;
        position: relative;
        overflow: hidden;
        /* Efekt szronu / prześwitu */
        background: rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.4);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
        color: #222;
    }

    /* Ziarnistość (Noise) dodawana jako pseudoelement */
    .glass-card::before {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        opacity: 0.15;
        background-image: url('data:image/svg+xml,%3Csvg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noiseFilter"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noiseFilter)"/%3E%3C/svg%3E');
        pointer-events: none; /* Żeby nie blokowało klikania w tekst */
        z-index: -1;
    }
    
    .glass-card h3 {
        margin-top: 0;
        color: #111;
        border-bottom: 1px solid rgba(0,0,0,0.1);
        padding-bottom: 10px;
    }

</style>

<div class="fixed-header">
    <div class="header-logo">STRONA GŁÓWNA</div>
    <div class="nav-buttons">
        <button class="nav-btn">Analizator 1</button>
        <button class="nav-btn">Analizator 2</button>
        <button class="nav-btn">Analizator 3</button>
    </div>
</div>

<div class="content-spacer"></div>

<div class="title-area">
    <div class="square square-left">GŁÓWNY</div>
    <div class="square square-right">PANEL</div>
</div>

<div style="text-align: center; margin-top: 50px;">
    <h2 style="color: #444; font-weight: 300; letter-spacing: 2px;">WYBIERZ MODUŁ</h2>
    <hr style="width: 50px; border: 1px solid #888; margin: 10px auto;">
</div>

<div class="glass-grid">
    <div class="glass-card">
        <h3>Analizator 1</h3>
        <p>Tutaj znajdzie się opis pierwszego modułu. Dzięki efektowi szklanej powłoki tło za nim staje się rozmyte, a ziarno dodaje tekstury.</p>
    </div>
    <div class="glass-card">
        <h3>Analizator 2</h3>
        <p>Miejsce na wgranie danych wejściowych, np. plików CSV lub obrazów medycznych, by wyciągnąć szybkie statystyki.</p>
    </div>
    <div class="glass-card">
        <h3>Analizator 3</h3>
        <p>Zaawansowane wykresy i podsumowania. Minimalizm sprawia, że interfejs nie odciąga uwagi od najważniejszego - danych.</p>
    </div>
</div>
""", unsafe_allow_html=True)
