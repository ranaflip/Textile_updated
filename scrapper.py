import requests
import fitz  # PyMuPDF
import pdfplumber
import json
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# URLs of the PDFs
pdf_urls = {
    "import_silk": "https://csb.gov.in/wp-content/uploads/2024/07/Import-of-Silk-and-Silk-Goods.pdf",
    "export_silk": "https://csb.gov.in/wp-content/uploads/2024/07/Export-Earnings-from-Silk-and-Silk-Goods-1.pdf"
}

# Function to download PDFs with SSL verification disabled
def download_pdf(url, filename):
    try:
        response = requests.get(url, verify=False)  # Disable SSL verification
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)

        with open(filename, "wb") as file:
            file.write(response.content)
        print(f"Downloaded: {filename}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {filename}: {e}")

# Function to extract text from PDF
def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text("text") for page in doc])
    return text

# Function to extract tables (if needed)
def extract_tables(pdf_path):
    extracted_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            extracted_tables.extend(tables)
    return extracted_tables

# Download PDFs
for key, url in pdf_urls.items():
    filename = f"{key}.pdf"
    download_pdf(url, filename)

# Extract data
data = {}
for key in pdf_urls.keys():
    pdf_path = f"{key}.pdf"
    data[key] = {
        "text": extract_text(pdf_path),
        "tables": extract_tables(pdf_path)
    }

# Save extracted data to JSON
with open("silk_data.json", "w") as f:
    json.dump(data, f, indent=4)

print("Data extraction completed and saved.")
