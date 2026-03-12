# %% dash presenze
# streamlit run D:\users\TA16669\PycharmProjects\PythonProject\fun\app.py
import streamlit as st
import pandas as pd
import json
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Connessione al Google Sheet ===
scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]


creds_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)

sheet = client.open("RegistroPresenze").sheet1  # nome Google Sheet

# Funzione per leggere dati
def load_data():
    records = sheet.get_all_records()
    return pd.DataFrame(records)

# Funzione per scrivere dati
def append_row(valori):
    sheet.append_row(valori)

# === Interfaccia Streamlit ===
st.title("📅 HQ Credito - Presenze & Smart Working")

df = load_data()

st.subheader("👀 Presenze registrate")
st.dataframe(df, use_container_width=True)

st.subheader("✏️ Inserisci la tua presenza")

nome = st.text_input("Nome e Cognome")
presenza = st.selectbox("Presenza questa settimana?", ["Sì", "No"])
settimana = date.today().isocalendar().week

if st.button("Registra"):
    if nome.strip() == "":
        st.error("Inserisci un nome valido.")
    else:
        append_row([nome, presenza, settimana, str(date.today())])
        st.success("Registrazione salvata!")
        st.rerun()
