import pandas as pd
from pathlib import Path


def main() -> None:
    """Export the 'GN X - Articles' sheet from the new Excel file into excel_files as CSV."""
    root = Path(".")
    excel_path = root / "26.02.10 - Stammdaten_Regelwerk_Lookups_Einzelteile.xlsx"
    out_dir = root / "excel_files"
    out_dir.mkdir(exist_ok=True)

    if not excel_path.exists():
        raise SystemExit(f"Excel file not found: {excel_path}")

    # The sheet in the new file is called 'GN X - Articles' (per user description)
    sheet_name = "GN X - Articles"

    xls = pd.ExcelFile(excel_path)
    if sheet_name not in xls.sheet_names:
        raise SystemExit(f"Sheet '{sheet_name}' not found in {excel_path}. Available: {xls.sheet_names}")

    df = xls.parse(sheet_name)

    # Write CSV with the new, clearer name
    out_file = out_dir / "GN X - Articles.csv"
    df.to_csv(out_file, index=False)
    print(f"Written {out_file}")


if __name__ == "__main__":
    main()

import pandas as pd
from pathlib import Path


def main() -> None:
    """Export the 'GN X - Articles' sheet from the new Excel file into excel_files as CSV."""
    root = Path(".")
    excel_path = root / "26.02.10 - Stammdaten_Regelwerk_Lookups_Einzelteile.xlsx"
    out_dir = root / "excel_files"
    out_dir.mkdir(exist_ok=True)

    if not excel_path.exists():
        raise SystemExit(f"Excel file not found: {excel_path}")

    # The sheet in the new file is called 'GN X - Articles' (per user description)
    sheet_name = "GN X - Articles"

    xls = pd.ExcelFile(excel_path)
    if sheet_name not in xls.sheet_names:
        raise SystemExit(f"Sheet '{sheet_name}' not found in {excel_path}. Available: {xls.sheet_names}")

    df = xls.parse(sheet_name)

    # Write CSV with the new, clearer name
    out_file = out_dir / "GN X - Articles.csv"
    df.to_csv(out_file, index=False)
    print(f"Written {out_file}")


if __name__ == "__main__":
    main()

