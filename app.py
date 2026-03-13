# %% dash presenze
# streamlit run D:\users\TA16669\PycharmProjects\PythonProject\fun\app.py
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# Config
# =========================
USERS = ["User 1", "User 2", "User 3", "User 4", "User 5"]
STATUS = ["Smart Working", "Ufficio"]  # 2 soli casi
SHEET_NAME = "RegistroPresenze"

# Mappa per colori
COLOR_MAP = {
    "Smart Working": "background-color: #85C1E9; color: #000000;",  # azzurro
    "Ufficio": "background-color: #82E0AA; color: #000000;",        # verde
    "Non registrato": "background-color: #D5D8DC; color: #000000;", # grigio
}

# Giorni e mesi in italiano (evita dipendenze da locale)
GIORNI_IT = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
MESI_IT = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
           "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def format_data_it(d: date) -> str:
    """Esempio: 'Venerdì 13 marzo'."""
    return f"{GIORNI_IT[d.weekday()]} {d.day} {MESI_IT[d.month-1]}"


def week_monday(base: date, offset_weeks: int = 0) -> date:
    """Ritorna il lunedì della settimana relativa (0=questa, 1=prossima, ecc.)."""
    today = base + timedelta(weeks=offset_weeks)
    return today - timedelta(days=today.weekday())


def week_dates(monday: date) -> list[date]:
    """Lunedì → Venerdì."""
    return [monday + timedelta(days=i) for i in range(5)]


# =========================
# Connessione Google Sheet (via Secrets TOML a tabella [google_service_account])
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
# Funzioni Dati
# =========================
EXPECTED_COLS = ["utente", "data", "giorno", "presenza", "settimana", "sett_inizio", "created_at"]

def load_df() -> pd.DataFrame:
    """Carica i dati; gestisce sia vecchie che nuove intestazioni."""
    records = sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=EXPECTED_COLS)

    df = pd.DataFrame(records)

    # Compatibilità con vecchio schema: nome|presenza|settimana|data
    if "utente" not in df.columns and "nome" in df.columns:
        df = df.rename(columns={"nome": "utente"})
    if "giorno" not in df.columns and "data" in df.columns:
        # Ricava giorno in italiano dalla data (se possibile)
        try:
            dtmp = pd.to_datetime(df["data"]).dt.date
            df["giorno"] = [GIORNI_IT[d.weekday()] for d in dtmp]
        except Exception:
            df["giorno"] = ""
    if "sett_inizio" not in df.columns and "data" in df.columns:
        try:
            dtmp = pd.to_datetime(df["data"]).dt.date
            mons = [(d - timedelta(days=d.weekday())).isoformat() for d in dtmp]
            df["sett_inizio"] = mons
        except Exception:
            df["sett_inizio"] = ""
    if "created_at" not in df.columns:
        df["created_at"] = ""

    # Ordina colonne
    for c in EXPECTED_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df[EXPECTED_COLS]
    return df


def append_week_plan(user: str, monday: date, choices: dict[date, str]):
    """Salva 5 righe (lun–ven) per un utente e una settimana (append-only con timestamp)."""
    week_no = monday.isocalendar().week
    now_iso = datetime.now().isoformat(timespec="seconds")
    for d in week_dates(monday):
        presenza = choices.get(d, "Ufficio")  # default Ufficio se non impostato
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
    """Costruisce matrice [utenti x giorni] con ultimo stato noto; riempie 'Non registrato'."""
    dates = [d.isoformat() for d in week_dates(monday)]

    if df.empty:
        base = pd.DataFrame(index=USERS, columns=dates)
        return base.fillna("Non registrato")

    # Considera solo la settimana scelta (per robustezza uso sett_inizio)
    dff = df.copy()
    dff = dff[dff["sett_inizio"] == monday.isoformat()]

    if dff.empty:
        base = pd.DataFrame(index=USERS, columns=dates)
        return base.fillna("Non registrato")

    # Tieni l'ultima registrazione per (utente, data)
    dff = dff.sort_values("created_at")
    dff = dff.drop_duplicates(subset=["utente", "data"], keep="last")

    # Pivot: righe utenti, colonne date (YYYY-MM-DD), valori presenza
    pivot = dff.pivot_table(index="utente", columns="data", values="presenza", aggfunc="last")

    # Assicura tutte le righe utenti e tutte le colonne (lun–ven)
    pivot = pivot.reindex(index=USERS, columns=dates)
    pivot = pivot.fillna("Non registrato")

    # Rinomina colonne con label "Giorno dd mese"
    colmap = {d: format_data_it(pd.to_datetime(d).date()) for d in dates}
    pivot = pivot.rename(columns=colmap)

    # Rinomina indice per estetica
    pivot.index.name = "Utente"
    return pivot


def style_colors(val: str) -> str:
    return COLOR_MAP.get(val, COLOR_MAP["Non registrato"])


# =========================
# UI
# =========================
st.title("📅 Pianificazione Presenze (Settimana)")

# Selettore settimana (0=questa, 1=prossima, fino a +8)
options = list(range(0, 9))
labels = []
today = date.today()
for w in options:
    mon = week_monday(today, w)
    fri = mon + timedelta(days=4)
    labels.append(f"{'Questa' if w==0 else ('Prossima' if w==1 else f'+{w} settimane')} "
                  f"({format_data_it(mon)} – {format_data_it(fri)})")

week_offset = st.selectbox("Scegli la settimana:", options=options, format_func=lambda i: labels[i], index=0)
monday_sel = week_monday(today, week_offset)
friday_sel = monday_sel + timedelta(days=4)
week_no = monday_sel.isocalendar().week

st.markdown(
    f"### 🗓️ Settimana {week_no}: **{format_data_it(monday_sel)} – {format_data_it(friday_sel)}**"
)

# Carica dati e mostra matrice della settimana selezionata
df_all = load_df()
matrix = build_week_matrix(df_all, monday_sel)
st.subheader("👀 Pianificazione settimana selezionata (tutti gli utenti)")
styled = matrix.style.applymap(style_colors)
st.dataframe(styled, width="stretch")

st.divider()

# =========================
# Pianificazione per un utente (lun–ven in un colpo solo)
# =========================
st.subheader("✏️ Imposta la pianificazione settimanale")

utente = st.selectbox("Utente:", USERS, index=0)

st.caption("Imposta per ciascun giorno se sei in **Smart Working** (azzurro) o in **Ufficio** (verde).")
cols = st.columns(5)
choices = {}
for i, d in enumerate(week_dates(monday_sel)):
    with cols[i]:
        # Default Ufficio; l'utente sceglie
        scelta = st.radio(
            label=f"{format_data_it(d)}",
            options=STATUS,
            index=1,  # 0=Smart Working, 1=Ufficio → default "Ufficio"
            key=f"rad_{utente}_{d.isoformat()}_{week_offset}"
        )
        choices[d] = scelta

if st.button("💾 Salva pianificazione per questa settimana"):
    append_week_plan(utente, monday_sel, choices)
    st.success(f"Pianificazione salvata per **{utente}** – settimana {week_no}.")
    st.rerun()
