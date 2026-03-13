# %% dash presenze
# streamlit run D:\users\TA16669\PycharmProjects\PythonProject\fun\app.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Connessione Google Sheet ===
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

svc = dict(st.secrets["google_service_account"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(svc, scope)
client = gspread.authorize(creds)
sheet = client.open("RegistroPresenze").sheet1

# === Funzioni utili ===
def load_data():
    records = sheet.get_all_records()
    return pd.DataFrame(records)

def append_row(values):
    sheet.append_row(values)

def get_current_week_dates():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    return monday, friday

def colore_presenza(val):
    if val == "Smart Working":
        return "background-color: #85C1E9; color: black;"  # azzurro
    elif val == "Ufficio":
        return "background-color: #82E0AA; color: black;"  # verde
    else:
        return "background-color: #D5D8DC; color: black;"  # grigio


# === INTERFACCIA ===
st.title("📅 Registro Presenze")

# Settimana attuale
monday, friday = get_current_week_dates()
week_number = date.today().isocalendar().week

st.markdown(
    f"""
    ### 🗓️ Settimana {week_number}:  
    **{monday.strftime('%A %d %B')} – {friday.strftime('%A %d %B')}**
    """,
    unsafe_allow_html=True,
)

# Carica dati
df = load_data()

# Filtra la settimana corrente
df_week = df[df["settimana"] == week_number]

st.subheader("👀 Presenze della settimana")

if df_week.empty:
    st.info("Nessuna presenza registrata per questa settimana.")
else:
    styled = df_week.style.applymap(colore_presenza, subset=["presenza"])
    st.dataframe(styled, width="stretch")

# === Inserimento ===
st.subheader("✏️ Inserisci la tua presenza")

utente = st.selectbox(
    "Seleziona l'utente:",
    ["User 1", "User 2", "User 3", "User 4", "User 5"]
)

presenza = st.selectbox(
    "Presenza:",
    ["Smart Working", "Ufficio"]
)

if st.button("Registra"):
    append_row([utente, presenza, week_number, str(date.today())])
    st.success("Registrazione salvata!")
    st.rerun()
