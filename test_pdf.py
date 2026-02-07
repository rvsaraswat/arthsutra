import pdfplumber
import sys

filepath = r'c:\Users\rvsar\Downloads\AMEX CARD STATEMENT-1015.pdf'

print("=== Test 1: Open without password ===")
try:
    pdf = pdfplumber.open(filepath)
    print(f"  Opened OK. Pages: {len(pdf.pages)}")
    page = pdf.pages[0]
    text = page.extract_text() or ""
    print(f"  Text length: {len(text)}")
    print(f"  First 300 chars:\n{text[:300]}")
    tables = page.extract_tables()
    print(f"  Tables found on page 1: {len(tables)}")
    for i, t in enumerate(tables):
        print(f"    Table {i}: {len(t)} rows, headers: {t[0] if t else 'empty'}")
    pdf.close()
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")

print("\n=== Test 2: Open with dummy password ===")
try:
    pdf = pdfplumber.open(filepath, password="test123")
    print(f"  Opened OK. Pages: {len(pdf.pages)}")
    page = pdf.pages[0]
    text = page.extract_text() or ""
    print(f"  Text length: {len(text)}")
    print(f"  First 300 chars:\n{text[:300]}")
    tables = page.extract_tables()
    print(f"  Tables found on page 1: {len(tables)}")
    for i, t in enumerate(tables):
        print(f"    Table {i}: {len(t)} rows, headers: {t[0] if t else 'empty'}")
    pdf.close()
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")
