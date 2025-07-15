import streamlit as st
import pandas as pd
import os
from extract_cheque_data import process_cheque_image_file

st.title("Cheque OCR Extractor")

uploaded_files = st.file_uploader(
    "Upload one or more cheque images", 
    type=["jpg", "jpeg", "png"], 
    accept_multiple_files=True
)

excel_file = "cheque_data_output.xlsx"

# Create Excel file if not exists
if not os.path.exists(excel_file):
    pd.DataFrame(columns=["Filename", "Bank Name", "IFSC Code", "Amount", "Date"]).to_excel(excel_file, index=False)

@st.cache_data(show_spinner=False)
def load_existing_data(excel_path):
    if os.path.exists(excel_path):
        return pd.read_excel(excel_path)
    return pd.DataFrame(columns=["Filename", "Bank Name", "IFSC Code", "Amount", "Date"])

df = load_existing_data(excel_file)

# Normalize existing data
df["Filename"] = df["Filename"].str.strip().str.lower()
df["IFSC Code"] = df["IFSC Code"].astype(str).str.strip().str.upper()
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").round(2)
df["Date"] = df["Date"].astype(str).str.strip()

new_rows = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        new_data = process_cheque_image_file(uploaded_file)

        # Normalize new record
        fname = new_data["Filename"].strip().lower()
        ifsc = str(new_data["IFSC Code"]).strip().upper()
        amt = round(float(new_data["Amount"]), 2) if new_data["Amount"] else None
        date = str(new_data["Date"]).strip()

        is_duplicate = (
            (df["Filename"] == fname) &
            (df["IFSC Code"] == ifsc) &
            (df["Amount"] == amt) &
            (df["Date"] == date)
        ).any()

        if not is_duplicate:
            new_rows.append(new_data)
        else:
            st.warning(f"⚠️ Duplicate cheque skipped: {uploaded_file.name}")

    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        df.to_excel(excel_file, index=False)
        st.success("✅ New cheques processed and added to Excel!")

st.subheader("📄 Extracted Cheque Data")
st.dataframe(df)

if os.path.exists(excel_file):
    with open(excel_file, "rb") as f:
        st.download_button(
            label="📥 Download Excel",
            data=f.read(),
            file_name=excel_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
