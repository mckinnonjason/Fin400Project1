"""Build the FIN 400 Project One firm-year analysis dataset.

Inputs are the three original downloads. The output, Project1FinalData.csv,
contains one firm-fiscal-year observation per row and the two project variables:
X = R&D expense / sales, and Y = the following 12-month stock return.

For a fiscal year ending in month t, Y compounds returns from the next calendar
month through the same month in the following year.
"""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUTPUT_FILE = ROOT / "Project1FinalData.csv"
AUDIT_FILE = ROOT / "Project1DataAudit.txt"


def compound_return(monthly_returns):
    """Compound a sequence of monthly stock returns into one total return."""
    return (1 + monthly_returns).prod() - 1


def main():
    # Create X from annual Compustat fundamentals.
    fundamentals = pd.read_csv(
        ROOT / "Project1Data.csv", dtype={"gvkey": "string"}, parse_dates=["datadate"]
    )
    original_fundamental_rows = len(fundamentals)
    base_sample = fundamentals.loc[
        fundamentals["fyear"].between(1990, 2024)
        & fundamentals["fic"].eq("USA")
        & fundamentals["curcd"].eq("USD")
        & fundamentals["datafmt"].eq("STD")
        & fundamentals["indfmt"].eq("INDL")
        & fundamentals["consol"].eq("C")
    ].copy()
    # Do not treat missing R&D as zero R&D: a blank value is not a valid X.
    valid_x = base_sample.loc[
        base_sample["sale"].gt(0) & base_sample["xrd"].ge(0)
    ].copy()
    valid_x["rd_intensity"] = valid_x["xrd"] / valid_x["sale"]

    # Link a firm-year to CRSP's PERMNO only when the link is valid.
    links = pd.read_csv(
        ROOT / "datasetlink.csv", dtype={"gvkey": "string"}, parse_dates=["LINKDT"]
    )
    links["LINKENDDT"] = pd.to_datetime(
        links["LINKENDDT"].replace("E", "2025-12-31")
    )
    links = links.loc[
        links["LINKTYPE"].isin(["LC", "LU"])
        & links["LINKPRIM"].isin(["P", "C"])
    ].copy()
    valid_x["return_start"] = valid_x["datadate"] + pd.offsets.MonthEnd(1)
    linked = valid_x.merge(
        links, on="gvkey", how="inner", validate="many_to_many", suffixes=("", "_link")
    )
    linked = linked.loc[
        linked["return_start"].between(linked["LINKDT"], linked["LINKENDDT"])
    ].copy()
    if linked.duplicated(["gvkey", "fyear"]).any():
        raise ValueError("More than one valid CRSP link was found for a firm-year.")
    linked["return_start_month"] = linked["return_start"].dt.to_period("M")

    # Retain CRSP U.S. equity returns and make one record per security-month.
    returns = pd.read_csv(
        ROOT / "Project1Y.csv",
        usecols=["PERMNO", "MthCalDt", "MthRet", "USIncFlg", "SecurityType"],
        parse_dates=["MthCalDt"],
    )
    original_return_rows = len(returns)
    returns = returns.loc[
        returns["USIncFlg"].eq("Y") & returns["SecurityType"].eq("EQTY")
    ].copy()
    returns["return_month"] = returns["MthCalDt"].dt.to_period("M")
    returns = returns.drop_duplicates(["PERMNO", "return_month"], keep="first")

    # Every linked firm-year requires exactly the following 12 calendar months.
    windows = linked[["gvkey", "fyear", "LPERMNO", "return_start_month"]].copy()
    windows["return_month"] = windows.apply(
        lambda row: pd.period_range(row["return_start_month"], periods=12, freq="M"),
        axis=1,
    )
    windows = windows.explode("return_month", ignore_index=True)
    monthly = windows.merge(
        returns[["PERMNO", "return_month", "MthRet"]],
        left_on=["LPERMNO", "return_month"],
        right_on=["PERMNO", "return_month"],
        how="left",
        validate="many_to_one",
    )
    coverage = monthly.groupby(["gvkey", "fyear"], as_index=False).agg(
        months_found=("MthRet", "count"),
        next_year_return=("MthRet", compound_return),
    )
    complete_returns = coverage.loc[coverage["months_found"].eq(12)].copy()

    # Save one final row per firm-year containing the two required variables.
    final_data = linked.merge(
        complete_returns[["gvkey", "fyear", "next_year_return"]],
        on=["gvkey", "fyear"],
        how="inner",
        validate="one_to_one",
    )
    final_data["return_end"] = (
        final_data["return_start_month"] + 11
    ).dt.to_timestamp("M")
    final_data = final_data[
        [
            "gvkey", "conm", "tic", "fyear", "datadate", "sale", "xrd",
            "rd_intensity", "LPERMNO", "return_start", "return_end", "next_year_return",
        ]
    ].sort_values(["gvkey", "fyear"])
    final_data.to_csv(OUTPUT_FILE, index=False)

    audit = [
        "FIN 400 Project One data audit",
        f"Original Compustat rows: {original_fundamental_rows:,}",
        f"Rows after sample-format/year filters: {len(base_sample):,}",
        f"Rows with valid sales and R&D (valid X): {len(valid_x):,}",
        f"Rows with a valid primary Compustat-CRSP link: {len(linked):,}",
        f"Original CRSP monthly-return rows: {original_return_rows:,}",
        f"CRSP rows after U.S. equity filter and de-duplication: {len(returns):,}",
        f"Rows with all 12 next-year monthly returns: {len(final_data):,}",
        f"Rows excluded from original Compustat download: {original_fundamental_rows - len(final_data):,}",
        "",
        "X = rd_intensity = xrd / sale.",
        "Y = next_year_return = compounded return from the month after datadate",
        "through the same month in the following calendar year.",
    ]
    AUDIT_FILE.write_text("\n".join(audit), encoding="utf-8")

    print("Created:", OUTPUT_FILE.name)
    print("Created:", AUDIT_FILE.name)
    print(f"Final firm-year observations: {len(final_data):,}")
    print("\nFinal data preview:")
    print(final_data.head().to_string(index=False))
    print("\nX and Y summary:")
    print(final_data[["rd_intensity", "next_year_return"]].describe().to_string())


if __name__ == "__main__":
    main()
