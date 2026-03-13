"""
Full pipeline runner — generates data then runs all analyses.

Usage:
    python run_all.py            # generate data + run all analyses
    python run_all.py --no-data  # skip data generation (data already exists)
"""

import argparse
import sys
from pathlib import Path

DATA_DIR = Path("data")
OUT_DIR  = Path("outputs")
OUT_DIR.mkdir(exist_ok=True)


def step(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main(generate: bool = True):
    if generate:
        step("Step 1/6 — Generating synthetic data")
        import importlib.util, runpy
        runpy.run_path(str(DATA_DIR / "generate_data.py"), run_name="__main__")
    else:
        print("Skipping data generation (--no-data flag set).")

    step("Step 2/6 — Sales Trend Analysis")
    from analysis.sales_trends import run as run_sales
    run_sales()

    step("Step 3/6 — RFM Customer Segmentation")
    from analysis.rfm_analysis import run as run_rfm
    run_rfm()

    step("Step 4/6 — Product Performance Analytics")
    from analysis.product_analytics import run as run_products
    run_products()

    step("Step 5/6 — Cohort Retention Analysis")
    from analysis.cohort_analysis import run as run_cohort
    run_cohort()

    step("Step 6/6 — A/B Testing Simulation")
    from analysis.ab_testing import run as run_ab
    run_ab()

    print(f"\n{'='*60}")
    print("  All analyses complete!")
    print(f"  Outputs saved to: {OUT_DIR.resolve()}")
    print(f"\n  Launch dashboard:")
    print(f"    streamlit run dashboard/app.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the full analytics pipeline.")
    parser.add_argument("--no-data", action="store_true",
                        help="Skip synthetic data generation")
    args = parser.parse_args()
    main(generate=not args.no_data)
