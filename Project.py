"""FIN 400 Project One: inspect the raw Compustat download.

X will be R&D expense / sales in year t.
Y will be the firm's total stock return in the following year.
The current CSV contains inputs for X; CRSP returns and linking data are
still needed for Y. This step diagnoses the data without removing rows.
"""

from pathlib import Path

import pandas as pd


def main():
    # Find the CSV beside this script, even when run from another directory.
    data_path = Path(__file__).resolve().parent / "Project1Data.csv"
    # GVKEY identifies firms. Keep its leading zeros for the later CRSP link.
    df = pd.read_csv(data_path, dtype={"gvkey": "string"})

    print("FIRST FIVE ROWS")
    print(df.head().to_string(index=False))
    print(f"\nOriginal rows: {len(df):,}")
    print(f"Distinct firms (GVKEY): {df['gvkey'].nunique():,}")
    print(f"Fiscal years: {df['fyear'].min()} through {df['fyear'].max()}")
    print("Columns:", df.columns.tolist())

    print("\nMISSING VALUES")
    print(df[["fyear", "sale", "xrd"]].isna().sum().to_string())
    # Missing R&D does not automatically mean zero R&D.
    print(f"\nRows with sales <= 0: {df['sale'].le(0).sum():,}")
    print(f"Rows with negative R&D: {df['xrd'].lt(0).sum():,}")

    print("\nCOUNTRY OF INCORPORATION (fic)")
    print(df["fic"].value_counts(dropna=False).to_string())
    print("\nREPORTING CURRENCY (curcd)")
    print(df["curcd"].value_counts(dropna=False).to_string())

    print("\nDATA FORMATS")
    print(df[["datafmt", "indfmt", "consol"]].value_counts(dropna=False).to_string())
    print(f"\nExact duplicate rows: {df.duplicated().sum():,}")
    print(
        "Repeated firm-year rows beyond the first: "
        f"{df.duplicated(['gvkey', 'fyear']).sum():,}"
    )
    # Different reporting formats can create repeated firm-years. Investigate
    # these before choosing a consistent format; do not just keep the first row.
    repeated = df.duplicated(["gvkey", "fyear"], keep=False)
    print("\nEXAMPLES OF REPEATED FIRM-YEARS")
    print(
        df.loc[repeated, ["gvkey", "fyear", "datadate", "indfmt", "sale", "xrd"]]
        .head(10)
        .to_string(index=False)
    )

    print("\nNext: define the sample and return timing, then obtain CRSP returns")
    print("and the Compustat/CRSP link. No rows have been changed or excluded.")


if __name__ == "__main__":
    main()
