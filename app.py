import streamlit as st
import pandas as pd
import os
import json
import datetime
from google import genai
from google.genai import types

# --- CONFIGURAZIONE ---
API_KEY = os.getenv("Gemini_Google_API_Key")
DEFAULT_DB_PATH = "data/Statistiche_Fantacalcio_Stagione_2025_26.xlsx"
SQUAD_FILE = "my_fanta_squad.json"

FANTA_GLOSSARY = """
GLOSSARIO STATISTICHE:
- R: Ruolo (P, D, C, A)
- Pv: Partite a voto | Mv: Media Voto | Fm: Fanta-media (con bonus/malus)
- Gf: Gol Fatti | Ass: Assist | Amm: Ammonizioni | Esp: Espulsioni
"""

# --- GESTIONE DATI E ROSA ---
@st.cache_data
def load_player_data(source) -> pd.DataFrame:
    df = pd.read_excel(source, header=1)
    df = df.dropna(subset=['Nome'])
    return df

def save_squad(squad_dict):
    with open(SQUAD_FILE, "w") as f:
        json.dump(squad_dict, f)

def load_squad():
    if os.path.exists(SQUAD_FILE):
        try:
            with open(SQUAD_FILE, "r") as f:
                return json.load(f)
        except:
            return {"P": [], "D": [], "C": [], "A": []}
    return {"P": [], "D": [], "C": [], "A": []}

def get_data_source():
    if os.path.exists(DEFAULT_DB_PATH):
        df = load_player_data(DEFAULT_DB_PATH)
        mod_time = os.path.getmtime(DEFAULT_DB_PATH)
        last_update = datetime.datetime.fromtimestamp(mod_time).strftime("%d/%m/%Y")
        return df, f"DB locale ({last_update})"
    
    st.sidebar.warning("Nessun DB locale trovato.")
    uploaded_file = st.sidebar.file_uploader("Carica Excel Fantacalcio.it", type=['xlsx'])
    if uploaded_file:
        return load_player_data(uploaded_file), "File caricato"
    return None, None

# --- AI CORE ---
def call_gemini(prompt_text):
    client = genai.Client(api_key=API_KEY)
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_text,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7,
            )
        )
        sources = []
        if response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.grounding_chunks:
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                if chunk.web:
                    sources.append({"title": chunk.web.title, "url": chunk.web.uri})
        return response.text, sources
    except Exception as e:
        return f"Errore AI: {e}", []

# --- UI SETUP ---
st.set_page_config(page_title="Fanta-AI Pro 25/26", page_icon="⚽", layout="wide")
st.title("⚽ Fanta-AI: Il tuo DS Intelligente")

if not API_KEY:
    st.error("Chiave API non trovata.")
    st.stop()

df, source_label = get_data_source()

if df is not None:
    st.sidebar.success(f"✅ {source_label}")
    
    tab1, tab2 = st.tabs(["⚖️ Confronto Dubbi", "📋 Formazione Consigliata"])

    # --- TAB 1: CONFRONTO SINGOLO ---
    with tab1:
        st.subheader("Chi schiero tra questi?")
        
        # Nuovo sistema di filtraggio per ruolo
        role_choice = st.radio(
            "Filtra per ruolo:", 
            ["Tutti", "P", "D", "C", "A"], 
            horizontal=True,
            key="role_filter_tab1"
        )
        
        # Filtriamo le opzioni in base alla scelta
        if role_choice == "Tutti":
            available_options = sorted(df['Nome'].unique())
        else:
            available_options = sorted(df[df['R'] == role_choice]['Nome'].unique())
            
        selected_players = st.multiselect(
            "Seleziona i giocatori da confrontare:", 
            options=available_options
        )
        
        if selected_players:
            # Recuperiamo i dati completi (senza filtraggio di ruolo per sicurezza 
            # nel caso avessi rimosso il filtro dopo la selezione)
            selected_data = df[df['Nome'].isin(selected_players)]
            cols = ['Nome', 'Squadra', 'R', 'Pv', 'Mv', 'Fm', 'Gf', 'Ass']
            st.dataframe(selected_data[cols], use_container_width=True)
            
            extra_ctx = st.text_input(
                "Contesto (es. chi suggerisci di schierare fra questi giocatori?):", 
                key="ctx_1"
            )
            
            if st.button("🔍 Analizza Dubbio", type="primary"):
                with st.spinner("Analisi in corso..."):
                    # Il prompt rimane identico, è già perfetto
                    prompt = f"""
                    Analista Fantacalcio: Confronta questi giocatori.
                    Data: {datetime.date.today()}. Cerca info ULTIME 72H (infortuni/probabili).
                    Cerca info sul calendario, ovvero il prossimo avversario dei giocatori selezionati.
                    {FANTA_GLOSSARY}
                    DATI: {selected_data[cols].to_string(index=False)}
                    CONTESTO: {extra_ctx}
                    Dai un verdetto secco su chi schierare.
                    """
                    advice, sources = call_gemini(prompt)
                    st.markdown(advice)
                    if sources:
                        with st.expander("Fonti"):
                            for s in sources: 
                                st.markdown(f"- [{s['title']}]({s['url']})")

    # --- TAB 2: FORMAZIONE COMPLETA ---
    with tab2:
        st.subheader("Gestione Rosa e Top 11")
        
        # Caricamento rosa persistente
        if 'my_squad' not in st.session_state:
            st.session_state.my_squad = load_squad()

        with st.expander("⚙️ Modifica la tua Rosa (25 giocatori)"):
            st.info("Seleziona i tuoi giocatori per ruolo. Verranno salvati automaticamente.")
            new_squad = {}
            c1, c2 = st.columns(2)
            
            limits = {"P": 3, "D": 8, "C": 8, "A": 6}
            for i, (r, limit) in enumerate(limits.items()):
                col = c1 if i < 2 else c2
                current_sel = [n for n in st.session_state.my_squad.get(r, []) if n in df['Nome'].values]
                new_squad[r] = col.multiselect(f"{r} (Max {limit})", options=sorted(df[df['R']==r]['Nome'].unique()), default=current_sel)
            
            def save_squad(squad_dict):
                with open(SQUAD_FILE, "w", encoding="utf-8") as f:
                    # indent=4 serve a rendere il file leggibile, 
                    # ensure_ascii=False salva gli accenti correttamente
                    json.dump(squad_dict, f, ensure_ascii=False, indent=4)

        # Calcolo Formazione
        flat_list = [p for sub in st.session_state.my_squad.values() for p in sub]
        
        if len(flat_list) < 11:
            st.warning("Completa la rosa per generare la formazione (servono almeno 11 giocatori).")
        else:
            st.write(f"Giocatori in rosa: **{len(flat_list)}/25**")
            # --- NUOVA FEATURE: MODIFICATORE ---
            col_mod, col_btn = st.columns([1, 2])
            with col_mod:
                usa_modificatore = st.toggle("🛡️ Usa Modificatore Difesa", value=False, help="Se attivo, l'IA valuterà se conviene passare alla difesa a 4 per bonus extra.")
            # Contesto extra
            extra_ctx = st.text_input(
                "Contesto (es. vorrei un modulo offensivo):", 
                key="ctx_1"
            )

            if st.button("🪄 Genera Formazione Ottimale", type="primary"):
                with st.spinner("L'IA sta scegliendo il modulo e i titolari..."):
                    squad_df = df[df['Nome'].isin(flat_list)]
                    # Calcoliamo la data per dare un riferimento preciso
                    oggi = datetime.date.today().strftime("%d %B %Y")

                    testo_modificatore = """
                    REGOLA MODIFICATORE DIFESA (ATTIVA):
                    - Se schieri ALMENO 4 difensori, ricevi un bonus basato sulla media voto (voto puro, NO bonus/malus) dei 3 migliori difensori + il portiere.
                    - Le fasce dei bonus sono specifiche da user a user, ma in generale più alta è la media voto dei tuoi difensori, più alto sarà il bonus.
                    COMPITO: Valuta se i miei difensori e portiere posssono ottenere una media voto alta abbastanza da giustificare il passaggio a una difesa a 4. Se sì, considera questa opzione nella formazione.
                    """ if usa_modificatore else "MODIFICATORE DIFESA: Disattivato. Scegli il modulo più offensivo possibile."

                    prompt = f"""
                    SISTEMA: Sei un DS di Fantacalcio preciso. 
                    {testo_modificatore}
                    CONTESTO: {extra_ctx}
                    Data: {datetime.date.today()}.
                    Cerca info ULTIME 72H (MANDATORIA)

                    FASE 1 - RICERCA CALENDARIO (MANDATORIA):
                    Cerca online la prossima giornata di Serie A 2025/26.
                    Ti ho fornito la data odierna, dunque puoi capire quale sarà la prossima giornata di serie A.
                    Identifica esattamente chi gioca contro chi e printa il calendario in questo formato: "Squadra A vs Squadra B".

                    FASE 2 - VERIFICA STATO GIOCATORI (MANDATORIA):
                    Per OGNI giocatore della lista sotto, controlla le ultime notizie (infortuni, squalifiche, tempi di recupero). 
                    Esempio critico: Se Provedel è rotto fino a fine stagione, NON suggerirlo.

                    DATI MIA ROSA (CONTROLLA SOLO QUESTI NOMI):
                    {squad_df[['Nome', 'Squadra', 'R']].to_string(index=False)}

                    FASE 3 - SCHIERAMENTO (TOP 11):
                    - Scegli il modulo (es. 3-4-3, 4-3-3).
                    - Scrivi i Titolari in questo formato: "Nome (Squadra) vs Avversario - [Motivazione + Stato fisico]".
                    - Se un giocatore NON è nella mia lista sopra, NON citarlo mai.

                    FASE 4 - REPORT INFORTUNI DETTAGLIATO:
                    Elenca chi tra i MIEI giocatori è sicuramente OUT e perché (es. "Provedel: Stagione finita per rottura...").

                    {FANTA_GLOSSARY}
                    """
                    advice, sources = call_gemini(prompt)
                    st.divider()
                    st.markdown(advice)
                    if sources:
                        with st.expander("Fonti"):
                            for s in sources: st.markdown(f"- [{s['title']}]({s['url']})")

else:
    st.info("Carica il file Excel per iniziare.")

# --- FOOTER ---
st.sidebar.divider()
if st.sidebar.button("🔄 Reset Cache"):
    st.cache_data.clear()
    st.rerun()