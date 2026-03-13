# %% dash presenze
# streamlit run D:\users\TA16669\PycharmProjects\PythonProject\fun\app.py
# %% dash presenze
# streamlit run D:\users\TA16669\PycharmProjects\PythonProject\fun\app.py
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import base64

# =========================
# CONFIGURAZIONE
# =========================

USERS = [
    "Basilicata Davide",
    "Gioiosano Giacomo",
    "Martuncelli Valeria",
    "Paratore Christian",
    "Ricci Alessio"
]

STATUS = ["Smart Working", "Ufficio"]
SHEET_NAME = "RegistroPresenze"

# Path immagini sul repo GitHub — caricati come BASE64
USER_IMAGES = {
    "Basilicata Davide": "images/DB.png",
    "Gioiosano Giacomo": "images/GG.png",
    "Martuncelli Valeria": "images/VM.png",
    "Paratore Christian": "images/CP.png",
    "Ricci Alessio": "images/AR.jpg"
}

# Colori celle
COLOR_MAP = {
    "Smart Working": "background-color: #85C1E9; color: black;",
    "Ufficio": "background-color: #82E0AA; color: black;",
    "Non registrato": "background-color: #D5D8DC; color: black;"
}

GIORNI_IT = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
MESI_IT = ["gennaio","febbraio","marzo","aprile","maggio","giugno",
           "luglio","agosto","settembre","ottobre","novembre","dicembre"]


# =========================
# FUNZIONI DI UTILITÀ
# =========================

def img_to_base64(path):
    """Legge file immagine → base64."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None


def format_data_it(d: date) -> str:
    return f"{GIORNI_IT[d.weekday()]} {d.day} {MESI_IT[d.month-1]}"


def week_monday(base: date, offset_weeks=0) -> date:
    today = base + timedelta(weeks=offset_weeks)
    return today - timedelta(days=today.weekday())


def week_dates(monday: date):
    return [monday + timedelta(days=i) for i in range(5)]


# =========================
# GOOGLE SHEET CONNECTION
# =========================

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

svc = dict(st.secrets["google_service_account"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(svc, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1


# =========================
# FUNZIONI DATI
# =========================

EXPECTED_COLS = [
    "utente", "data", "giorno", "presenza",
    "settimana", "sett_inizio", "created_at"
]


def load_df():
    records = sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=EXPECTED_COLS)

    df = pd.DataFrame(records)

    if "nome" in df.columns:
        df = df.rename(columns={"nome": "utente"})
    for c in EXPECTED_COLS:
        if c not in df.columns:
            df[c] = ""

    return df[EXPECTED_COLS]


def append_week_plan(user: str, monday: date, choices: dict):
    now_iso = datetime.now().isoformat(timespec="seconds")
    week_no = monday.isocalendar().week

    for d in week_dates(monday):
        presenza = choices.get(d, "Ufficio")
        row = [
            user,
            d.isoformat(),
            GIORNI_IT[d.weekday()],
            presenza,
            week_no,
            monday.isoformat(),
            now_iso,
        ]
        sheet.append_row(row)


def build_week_matrix(df: pd.DataFrame, monday: date) -> pd.DataFrame:
    dates = [d.isoformat() for d in week_dates(monday)]

    if df.empty:
        base = pd.DataFrame(index=USERS, columns=dates).fillna("Non registrato")
    else:
        dff = df[df["sett_inizio"] == monday.isoformat()]
        if dff.empty:
            base = pd.DataFrame(index=USERS, columns=dates).fillna("Non registrato")
        else:
            dff = dff.sort_values("created_at")
            dff = dff.drop_duplicates(subset=["utente", "data"], keep="last")
            pivot = dff.pivot_table(index="utente", columns="data",
                                    values="presenza", aggfunc="last")
            pivot = pivot.reindex(index=USERS, columns=dates)
            base = pivot.fillna("Non registrato")

    # colonne: data formattata
    colmap = {d: format_data_it(pd.to_datetime(d).date()) for d in dates}
    base = base.rename(columns=colmap)

    base.index.name = ""  # rimuovi "Utente"

    return base


def style_colors(val):
    return COLOR_MAP.get(val, COLOR_MAP["Non registrato"])


# =========================
# INTERFACCIA
# =========================

st.title("📅 Pianificazione Presenze Settimanali (con Foto)")

today = date.today()

# Selettore settimana (0 = questa, 1 = prossima)
options = [0, 1]
labels = []
for w in options:
    mon = week_monday(today, w)
    fri = mon + timedelta(days=4)
    if w == 0:
        prefix = "Questa settimana"
    else:
        prefix = "Prossima settimana"
    labels.append(f"{prefix}: {format_data_it(mon)} – {format_data_it(fri)}")

week_offset = st.selectbox("Scegli la settimana:", options=options, format_func=lambda i: labels[i])

monday_sel = week_monday(today, week_offset)
friday_sel = monday_sel + timedelta(days=4)
week_no = monday_sel.isocalendar().week

st.markdown(
    f"### 🗓️ Settimana {week_no}: **{format_data_it(monday_sel)} – {format_data_it(friday_sel)}**"
)

# CARICA MATRICE
df_all = load_df()
matrix = build_week_matrix(df_all, monday_sel)

# ============================
# RENDER TABELLA CON FOTO PERFETTE
# ============================

# Funzione: foto + nome utente
def render_left_col(user):
    img_path = USER_IMAGES.get(user, "")
    b64 = img_to_base64(img_path)
    if b64:
        return f"""
        <div style='display:flex; align-items:center; gap:12px;'>
            data:image/png;base64,{b64}
            <span style='font-size:16px; color:white;'>{user}</span>
        </div>
        """
    else:
        return f"<span style='font-size:16px;'>{user}</span>"

# Prepara DataFrame HTML
df_html = matrix.copy()

# Prima colonna: utente con foto
df_html.insert(0, " ", [render_left_col(u) for u in df_html.index])

# Reset index per evitare doppia colonna
df_html = df_html.reset_index(drop=True)

# Applica colori alle celle dei giorni
color_cols = [c for c in df_html.columns if c not in [" "]]
styled = df_html.style.applymap(style_colors, subset=color_cols)

# Render tabella con HTML
st.write(styled.to_html(escape=False), unsafe_allow_html=True)

st.divider()

# =========================
# INSERIMENTO SETTIMANALE
# =========================

st.subheader("✏️ Imposta pianificazione settimanale")

utente = st.selectbox("Utente:", USERS)

cols = st.columns(5)
choices = {}
for i, d in enumerate(week_dates(monday_sel)):
    with cols[i]:
        scelta = st.radio(
            label=format_data_it(d),
            options=STATUS,
            index=1,
            key=f"{utente}_{d.isoformat()}_{week_offset}"
        )
        choices[d] = scelta

if st.button("💾 Salva pianificazione"):
    append_week_plan(utente, monday_sel, choices)
    st.success(f"Pianificazione salvata per {utente} (settimana {week_no}).")
    st.rerun()
