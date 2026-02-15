import os
import PyPDF2

pdf_files = [
    "/Users/milo/Desktop/BNP_BDD/student_documentation/BNP Paribas - CaseBrief - student version.pdf",
    "/Users/milo/Desktop/BNP_BDD/student_documentation/BDD BNP Paribas - Slides for kick off.pdf",
    "/Users/milo/Desktop/BNP_BDD/student_documentation/202502_BNP_Paribas_Foreword.pdf"
]

def extract_text(pdf_path):
    print(f"--- Extracting from: {os.path.basename(pdf_path)} ---")
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            print(f"Number of pages: {len(reader.pages)}")
            full_text = ""
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    full_text += f"\n[Page {i+1}]\n{text}"
            return full_text
    except Exception as e:
        return f"Error reading {pdf_path}: {e}"

all_text = ""
for pdf in pdf_files:
    if os.path.exists(pdf):
        text = extract_text(pdf)
        all_text += text + "\n\n" + "="*50 + "\n\n"
    else:
        print(f"File not found: {pdf}")

# Save to a file for easy reading
output_file = "extracted_case_text.txt"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(all_text)

print(f"Extraction complete. Text saved to {output_file}")
