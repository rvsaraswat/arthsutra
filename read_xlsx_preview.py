from __future__ import annotations

from pathlib import Path


def preview_lock_file(path: Path) -> None:
    print(f"Lock exists: {path.exists()}")
    if not path.exists():
        return
    size = path.stat().st_size
    print(f"Lock size: {size} bytes")
    try:
        data = path.read_bytes()[:256]
        print("Lock first 256 bytes (hex):")
        print(data.hex(" "))
    except PermissionError as e:
        print("Lock file is currently locked by Excel; cannot read bytes.")
        print(f"PermissionError: {e}")


def preview_workbook(path: Path) -> None:
    print(f"Workbook exists: {path.exists()}")
    if not path.exists():
        return
    print(f"Workbook size: {path.stat().st_size} bytes")

    import pandas as pd

    xl = pd.ExcelFile(path)
    print("Sheets:", xl.sheet_names)

    for sheet in xl.sheet_names[:3]:
        df = xl.parse(sheet, nrows=10)
        print(f"\n== {sheet} ==")
        print("shape:", df.shape)
        print("columns:", list(df.columns))
        print(df.to_string(index=False))


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    preview_lock_file(root / "~$Fin_details - Copy.xlsx")
    print()
    preview_workbook(root / "Fin_details - Copy.xlsx")
