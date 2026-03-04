import argparse
from pathlib import Path

import pandas as pd


def convert_sheet(sheet_name: str, excel_path: Path, out_dir: Path) -> Path:
    if not excel_path.exists():
        raise SystemExit(f"Excel file not found: {excel_path}")

    out_dir.mkdir(parents=True, exist_ok=True)

    xls = pd.ExcelFile(excel_path)
    if sheet_name not in xls.sheet_names:
        raise SystemExit(
            f"Sheet '{sheet_name}' not found. Available sheets: {', '.join(xls.sheet_names)}"
        )

    df = xls.parse(sheet_name)
    out_path = out_dir / f"{sheet_name}.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sheet",
        required=True,
        help="Name of the sheet in main.xlsx to export (e.g. 'Sondenbeschriftung' or 'WPA')",
    )
    parser.add_argument(
        "--excel",
        default=str(Path("main excel") / "main.xlsx"),
        help="Path to the main Excel file (default: 'main excel/main.xlsx')",
    )
    parser.add_argument(
        "--out-dir",
        default="csv_files",
        help="Output directory for generated CSV (default: csv_files)",
    )
    args = parser.parse_args()

    excel_path = Path(args.excel)
    out_dir = Path(args.out_dir)

    convert_sheet(args.sheet, excel_path, out_dir)


if __name__ == "__main__":
    main()

