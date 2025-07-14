import os
import cv2
import pytesseract
import pandas as pd
import re
from pytesseract import Output
from datetime import datetime

# === Template Matching for Regions Based on Keywords ===
def locate_template_region(img, keyword):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    data = pytesseract.image_to_data(gray, output_type=Output.DICT)

    for i, word in enumerate(data['text']):
        if keyword.upper() in word.upper():
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            return img[y:y+h+40, x:x+250]  # Adjust crop area as needed
    return None

# === Field Extractors ===
def extract_ifsc(region_text):
    match = re.search(r'[A-Z]{4}0[0-9A-Z]{6}', region_text.replace("O", "0"))
    return match.group() if match else ""

def extract_amount(region_text):
    region_text = region_text.replace(",", "").replace("O", "0")
    match = re.findall(r'(\d+\.\d{2})', region_text)
    if match:
        return str(max([float(m) for m in match]))
    return ""

def extract_date(region_text):
    patterns = [
        r'(\d{1,2})[-/.]([A-Z]{3})[-/.](\d{4})',
        r'(\d{2})[.-](\d{2})[.-](\d{4})'
    ]
    month_map = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
        "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
        "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
    }
    for pattern in patterns:
        match = re.search(pattern, region_text.upper())
        if match:
            groups = match.groups()
            if len(groups) == 3:
                if groups[1].isalpha():
                    return f"{int(groups[0]):02d}-{month_map.get(groups[1][:3], '00')}-{groups[2]}"
                else:
                    return f"{groups[0]}-{groups[1]}-{groups[2]}"
    return ""

def extract_bank_name(full_text, ifsc_code):
    KNOWN_BANKS = [
        "ICICI BANK", "AXIS BANK", "SYNDICATE BANK", "CANARA BANK",
        "STATE BANK OF INDIA", "BANK OF BARODA", "HDFC BANK", "UNION BANK"
    ]
    for bank in KNOWN_BANKS:
        if bank in full_text:
            return bank

    IFSC_PREFIX_MAP = {
        "ICIC": "ICICI BANK", "UTIB": "AXIS BANK", "SYNB": "SYNDICATE BANK",
        "CNRB": "CANARA BANK", "SBIN": "STATE BANK OF INDIA",
        "BARB": "BANK OF BARODA", "HDFC": "HDFC BANK", "UBIN": "UNION BANK"
    }
    if ifsc_code:
        return IFSC_PREFIX_MAP.get(ifsc_code[:4], "Unknown")

    return "Unknown"

# === Main Cheque Processing Function ===
def process_cheque(image_path):
    img = cv2.imread(image_path)
    full_text = pytesseract.image_to_string(img).upper()

    ifsc_region = locate_template_region(img, "IFSC")
    amount_region = locate_template_region(img, "RUPEES")
    date_region = locate_template_region(img, "DATE")

    ifsc_text = pytesseract.image_to_string(ifsc_region).upper() if ifsc_region is not None else full_text
    amount_text = pytesseract.image_to_string(amount_region).upper() if amount_region is not None else full_text
    date_text = pytesseract.image_to_string(date_region).upper() if date_region is not None else full_text

    ifsc_code = extract_ifsc(ifsc_text)
    amount = extract_amount(amount_text)
    date = extract_date(date_text)
    bank_name = extract_bank_name(full_text, ifsc_code)

    return {
        "Filename": os.path.basename(image_path),
        "Bank Name": bank_name,
        "IFSC Code": ifsc_code,
        "Amount": amount,
        "Date": date
    }

# === Excel Append ===
def append_to_excel(new_data, excel_path="cheque_data_output.xlsx"):
    if os.path.exists(excel_path):
        df = pd.read_excel(excel_path)
    else:
        df = pd.DataFrame(columns=new_data.keys())

    if new_data["Filename"] not in df["Filename"].values:
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        df.to_excel(excel_path, index=False)

# === Batch Run ===
def process_folder(folder_path):
    for filename in os.listdir(folder_path):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            image_path = os.path.join(folder_path, filename)
            print(f"Processing: {filename}")
            result = process_cheque(image_path)
            append_to_excel(result)
    print("✅ All cheques processed and saved to Excel.")

# Example usage:
process_folder("../CHEQUE_OCR/Images")
