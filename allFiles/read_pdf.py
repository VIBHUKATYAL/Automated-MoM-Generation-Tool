import sys
from pypdf import PdfReader

def extract(pdf_name, out_name):
    try:
        reader = PdfReader(pdf_name)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        with open(out_name, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        print(f"Error extracting {pdf_name}: {e}")

extract("Documentation.pdf", "doc_output.txt")
extract("automated_mom_training_dataset (1).pdf", "dataset_output.txt")
