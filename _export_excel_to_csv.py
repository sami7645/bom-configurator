import pandas as pd
from pathlib import Path


def main() -> None:
    root = Path(".")
    excel_path = root / "Stammdaten_Regelwerk_Lookups_Einzelteile_v2-3.xlsx"
    out_dir = root / "excel_files"
    out_dir.mkdir(exist_ok=True)

    if not excel_path.exists():
        raise SystemExit(f"Excel file not found: {excel_path}")

    xls = pd.ExcelFile(excel_path)
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        safe = (
            sheet.replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
        )
        out_file = out_dir / f"{safe}.csv"
        df.to_csv(out_file, index=False)
        print(f"Written {out_file}")


if __name__ == "__main__":
    main()

