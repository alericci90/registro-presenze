# %% dash presenze
# streamlit run D:\users\TA16669\PycharmProjects\PythonProject\fun\app.py
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# CONFIGURAZIONE
# =========================

USERS = ["Basilicata Davide", "Giacomo Gioiosano", "Martuncelli Valeria", "Paratore Christian",
          "Ricci Alessio"]
STATUS = ["Smart Working", "Ufficio"]  # 2 soli casi
SHEET_NAME = "RegistroPresenze"

# Immagini utente (devi caricarle in /images/ dentro il repo GitHub)
USER_IMAGES = {
    "Basilicata Davide": "images/DB.png",
    "Giacomo Gioiosano": "images/GG.png",
    "Martuncelli Valeria": "images/VM.png",
    "Paratore Christian": "images/CP.png",
    "Ricci Alessio": "images/AR.jpg",
}

# Colori
COLOR_MAP = {
    "Smart Working": "background-color: #85C1E9; color: black;",   # azzurro
    "Ufficio": "background-color: #82E0AA; color: black;",         # verde
    "Non registrato": "background-color: #D5D8DC; color: black;",  # grigio
}

GIORNI_IT = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
MESI_IT = ["gennaio","febbraio","marzo","aprile","maggio","giugno",
           "luglio","agosto","settembre","ottobre","novembre","dicembre"]


def format_data_it(d: date) -> str:
    return f"{GIORNI_IT[d.weekday()]} {d.day} {MESI_IT[d.month-1]}"


def week_monday(base: date, offset_weeks: int = 0) -> date:
    today = base + timedelta(weeks=offset_weeks)
    return today - timedelta(days=today.weekday())


def week_dates(monday: date):
    return [monday + timedelta(days=i) for i in range(5)]


# =========================
# GOOGLE SHEET CONNECTION (USA I SECRETS TOML)
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


def load_df() -> pd.DataFrame:
    records = sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=EXPECTED_COLS)

    df = pd.DataFrame(records)

    # Adatta vecchie colonne se presenti
    if "nome" in df.columns:
        df = df.rename(columns={"nome": "utente"})
    if "giorno" not in df.columns:
        df["giorno"] = ""
    if "sett_inizio" not in df.columns:
        df["sett_inizio"] = ""
    if "created_at" not in df.columns:
        df["created_at"] = ""

    # Garantisce lo schema
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
        base = pd.DataFrame(index=USERS, columns=dates)
        base = base.fillna("Non registrato")
    else:
        dff = df[df["sett_inizio"] == monday.isoformat()]

        if dff.empty:
            base = pd.DataFrame(index=USERS, columns=dates)
            base = base.fillna("Non registrato")
        else:
            dff = dff.sort_values("created_at")
            dff = dff.drop_duplicates(subset=["utente", "data"], keep="last")

            pivot = dff.pivot_table(index="utente", columns="data",
                                    values="presenza", aggfunc="last")
            pivot = pivot.reindex(index=USERS, columns=dates)
            base = pivot.fillna("Non registrato")

    # Label eleganti per colonne
    colmap = {d: format_data_it(pd.to_datetime(d).date()) for d in dates}
    base = base.rename(columns=colmap)

    # Aggiungi colonna FOTO
    base.insert(0, "Foto", USERS)
    for user in USERS:
        base.loc[user, "Foto"] = USER_IMAGES.get(user, "")

    base.index.name = "Utente"
    return base


def style_colors(val: str):
    return COLOR_MAP.get(val, COLOR_MAP["Non registrato"])


# =========================
# UI
# =========================

st.title("📅 Pianificazione Presenze Settimanali")

today = date.today()

# Selettore settimana (0 = questa)
options = list(range(0, 9))
labels = []
for w in options:
    mon = week_monday(today, w)
    fri = mon + timedelta(days=4)
    if w == 0:
        prefix = "Questa settimana"
    elif w == 1:
        prefix = "Prossima settimana"
    else:
        prefix = f"Tra {w} settimane"
    labels.append(f"{prefix}: {format_data_it(mon)} – {format_data_it(fri)}")

week_offset = st.selectbox(
    "Scegli la settimana:",
    options=options,
    format_func=lambda i: labels[i]
)

monday_sel = week_monday(today, week_offset)
friday_sel = monday_sel + timedelta(days=4)
week_no = monday_sel.isocalendar().week

st.markdown(
    f"### 🗓️ Settimana {week_no}: "
    f"**{format_data_it(monday_sel)} – {format_data_it(friday_sel)}**"
)

# CARICA DATI
df_all = load_df()
matrix = build_week_matrix(df_all, monday_sel)

# Mostra tabella con immagini
st.subheader("👀 Pianificazione (tutti gli utenti)")

html = "<style>img.userpic{width:40px;height:40px;border-radius:6px;object-fit:cover;}</style>"
st.markdown(html, unsafe_allow_html=True)

# Converti Foto in <img>
matrix_html = matrix.copy()
for user in USERS:
    img = USER_IMAGES.get(user, "")
    matrix_html.loc[user, "Foto"] = f'<img class="userpic" src="{img}">'

styled = matrix_html.style.applymap(style_colors, subset=matrix_html.columns[1:])
st.write(styled.to_html(escape=False), unsafe_allow_html=True)

st.divider()

# =========================
# INSERIMENTO PIANIFICAZIONE
# =========================

st.subheader("✏️ Imposta pianificazione per un utente")

utente = st.selectbox("Utente:", USERS)

st.caption("Imposta per ogni giorno se sarai in **Smart Working** o in **Ufficio**.")
cols = st.columns(5)

choices = {}
for i, d in enumerate(week_dates(monday_sel)):
    with cols[i]:
        scelta = st.radio(
            label=format_data_it(d),
            options=STATUS,
            index=1,  # default Ufficio
            key=f"{utente}_{d.isoformat()}_{week_offset}"
        )
        choices[d] = scelta

if st.button("💾 Salva pianificazione"):
    append_week_plan(utente, monday_sel, choices)
    st.success(f"Pianificazione salvata per {utente} (settimana {week_no}).")
    st.rerun()
