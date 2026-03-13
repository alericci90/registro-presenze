# %% dash presenze
# Esecuzione locale: streamlit run D:\users\TA16669\PycharmProjects\PythonProject\fun\app.py
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

# Path immagini sul repo GitHub — caricate come BASE64
USER_IMAGES = {
    "Basilicata Davide": "images/DB.png",
    "Gioiosano Giacomo": "images/GG.png",
    "Martuncelli Valeria": "images/VM.png",
    "Paratore Christian": "images/CP.png",
    "Ricci Alessio": "images/AR.jpg"
}

# Colori celle
COLOR_MAP = {
    "Smart Working": "background-color: #85C1E9; color: #0A0A0A;",
    "Ufficio":       "background-color: #82E0AA; color: #0A0A0A;",
    "Non registrato":"background-color: #D5D8DC; color: #0A0A0A;"
}

# Colori “pillole” in modalità mobile
PILL_BG = {
    "Smart Working": "#85C1E9",
    "Ufficio": "#82E0AA",
    "Non registrato": "#D5D8DC"
}
PILL_FG = "#0A0A0A"

GIORNI_IT = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
MESI_IT   = ["gennaio","febbraio","marzo","aprile","maggio","giugno",
             "luglio","agosto","settembre","ottobre","novembre","dicembre"]

st.set_page_config(page_title="Pianificazione Presenze", layout="wide")


# =========================
# FUNZIONI DI UTILITÀ
# =========================

def img_to_base64(path: str) -> str | None:
    """Legge file immagine → base64 inline (ritorna data URL)."""
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        # Dettaglio: prova a inferire il mime type dal suffisso
        if path.lower().endswith(".png"):
            mime = "image/png"
        elif path.lower().endswith(".jpg") or path.lower().endswith(".jpeg"):
            mime = "image/jpeg"
        else:
            mime = "image/png"
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def format_data_it(d: date) -> str:
    return f"{GIORNI_IT[d.weekday()]} {d.day} {MESI_IT[d.month-1]}"


def week_monday(base: date, offset_weeks: int = 0) -> date:
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

def load_df() -> pd.DataFrame:
    records = sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=EXPECTED_COLS)

    df = pd.DataFrame(records)

    # Retro-compatibilità
    if "nome" in df.columns:
        df = df.rename(columns={"nome": "utente"})
    for c in EXPECTED_COLS:
        if c not in df.columns:
            df[c] = ""

    return df[EXPECTED_COLS]


def append_week_plan(user: str, monday: date, choices: dict[date, str]):
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
    dates_iso = [d.isoformat() for d in week_dates(monday)]

    if df.empty:
        base = pd.DataFrame(index=USERS, columns=dates_iso).fillna("Non registrato")
    else:
        dff = df[df["sett_inizio"] == monday.isoformat()]
        if dff.empty:
            base = pd.DataFrame(index=USERS, columns=dates_iso).fillna("Non registrato")
        else:
            dff = dff.sort_values("created_at")
            dff = dff.drop_duplicates(subset=["utente", "data"], keep="last")
            pivot = dff.pivot_table(index="utente", columns="data", values="presenza", aggfunc="last")
            pivot = pivot.reindex(index=USERS, columns=dates_iso)
            base = pivot.fillna("Non registrato")

    # Rinomina colonne in formato leggibile “Giorno 13 marzo”
    colmap = {d: format_data_it(pd.to_datetime(d).date()) for d in dates_iso}
    base = base.rename(columns=colmap)
    base.index.name = ""  # niente “Utente” in testa
    return base


def style_colors(val: str) -> str:
    return COLOR_MAP.get(val, COLOR_MAP["Non registrato"])


# =========================
# INTERFACCIA
# =========================

st.title("Leasys HQ Credit - Presenze Settimanali 📅")

today = date.today()

# Selettore settimana (0 = questa, 1 = prossima)
options = [0, 1]
labels = []
for w in options:
    mon = week_monday(today, w)
    fri = mon + timedelta(days=4)
    labels.append(("Questa settimana" if w == 0 else "Prossima settimana")
                  + f": {format_data_it(mon)} – {format_data_it(fri)}")

week_offset = st.selectbox("Scegli la settimana:", options=options, format_func=lambda i: labels[i])

monday_sel = week_monday(today, week_offset)
friday_sel = monday_sel + timedelta(days=4)
week_no = monday_sel.isocalendar().week

st.markdown(
    f"### 🗓️ Settimana {week_no}: "
    f"**{format_data_it(monday_sel)} – {format_data_it(friday_sel)}**"
)

# Toggle Modalità Mobile
mobile = st.toggle("📱 Modalità mobile", value=False, help="Vista ottimizzata per smartphone")

# Carica dati e matrice
df_all = load_df()
matrix = build_week_matrix(df_all, monday_sel)

# =========================
# RENDER: DESKTOP vs MOBILE
# =========================

if not mobile:
    # ---------- DESKTOP: Tabella classica ----------
    # Prima colonna: foto + nome come HTML così non si schiaccia
    def left_cell(user: str) -> str:
        data_url = img_to_base64(USER_IMAGES.get(user, ""))
        if data_url:
            return (
                f"<div style='display:flex;align-items:center;gap:10px;'>"
                f"<img src='{data_url}' style='width:56px;height:56px;border-radius:8px;object-fit:cover;'/>"
                f"<span style='font-size:16px;'>{user}</span>"
                f"</div>"
            )
        else:
            return f"<span style='font-size:16px;'>{user}</span>"

    df_html = matrix.copy()
    df_html.insert(0, " ", [left_cell(u) for u in df_html.index])
    df_html = df_html.reset_index(drop=True)

    color_cols = [c for c in df_html.columns if c.strip() != ""]
    styled = df_html.style.applymap(style_colors, subset=color_cols)
    st.write(styled.to_html(escape=False), unsafe_allow_html=True)

else:
    # ---------- MOBILE: Card per utente ----------
    # CSS per card responsive
    st.markdown(
        """
        <style>
          .card {
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 12px;
            background: rgba(255,255,255,0.03);
          }
          .row {
            display: flex; align-items: center; gap: 12px;
          }
          .avatar {
            width: 64px; height: 64px; border-radius: 10px; object-fit: cover; flex-shrink: 0;
          }
          .uname {
            font-size: 17px; font-weight: 600;
          }
          .pills {
            display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;
          }
          .pill {
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 13px;
            border: 1px solid rgba(0,0,0,0.05);
          }
          @media (max-width: 420px) {
            .avatar { width: 56px; height: 56px; }
            .uname { font-size: 16px; }
            .pill { font-size: 12px; padding: 5px 8px; }
          }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Per ogni utente, mostra card con avatar e 5 “pillole”
    for user in matrix.index.tolist():
        data_url = img_to_base64(USER_IMAGES.get(user, ""))

        # Costruisco pillole giorni
        pills_html = ""
        for col in matrix.columns:
            stato = str(matrix.loc[user, col])
            bg = PILL_BG.get(stato, "#D5D8DC")
            fg = PILL_FG
            pills_html += f"<span class='pill' style='background:{bg};color:{fg};'>{col.split()[0]}: {stato}</span>"

        card_html = (
            "<div class='card'>"
            "<div class='row'>"
            f"{f'<img src=\"{data_url}\" class=\"avatar\"/>' if data_url else ''}"
            f"<div class='uname'>{user}</div>"
            "</div>"
            f"<div class='pills'>{pills_html}</div>"
            "</div>"
        )
        st.markdown(card_html, unsafe_allow_html=True)

st.divider()

# =========================
# INSERIMENTO SETTIMANALE
# =========================

st.subheader("✏️ Imposta pianificazione settimanale")

utente = st.selectbox("Utente:", USERS)

cols = st.columns(5) if not mobile else st.columns(1)  # su mobile una colonna verticale
choices: dict[date, str] = {}

for i, d in enumerate(week_dates(monday_sel)):
    with (cols[i] if not mobile else cols[0]):
        scelta = st.radio(
            label=format_data_it(d),
            options=STATUS,
            index=1,  # default Ufficio
            key=f"{utente}_{d.isoformat()}_{'m' if mobile else 'd'}_{week_offset}",
            horizontal=not mobile  # su mobile meglio verticale
        )
        choices[d] = scelta

if st.button("💾 Salva pianificazione"):
    append_week_plan(utente, monday_sel, choices)
    st.success(f"Pianificazione salvata per {utente} (settimana {week_no}).")
    st.rerun()
