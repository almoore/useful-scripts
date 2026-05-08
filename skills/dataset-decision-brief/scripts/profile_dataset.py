#!/usr/bin/env python3
"""
profile_dataset.py — deterministic profiling for the dataset-decision-brief skill.

Loads a CSV / XLSX / JSON file, produces:
  - <output-dir>/<stem>-profile.json   (structured profile the model interprets)
  - <output-dir>/<stem>-charts.pdf     (multi-page chart PDF for the brief)

Usage:
    python profile_dataset.py <input-file> [--output-dir DIR] [--sample N]
                              [--sheet NAME] [--max-categories K]

Why a script: every invocation of this skill needs the same numerical work
(shape, dtypes, null counts, descriptive stats, top-K value counts, basic
charts). Doing it in code is faster, deterministic, and frees the model to
focus on the interpretation — which is where its judgment actually adds value.
"""

import argparse
import json
import sys
from pathlib import Path

REQUIRED = ["pandas", "numpy", "matplotlib"]


def _check_deps():
    missing = []
    for pkg in REQUIRED:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        sys.stderr.write(
            "Missing required packages: "
            + ", ".join(missing)
            + "\nInstall with: pip install pandas numpy matplotlib openpyxl\n"
        )
        sys.exit(2)


_check_deps()

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402


SAMPLE_THRESHOLD = 50_000


def load(path: Path, sheet: str | None) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet or 0)
    if suffix == ".json":
        try:
            return pd.read_json(path)
        except ValueError:
            return pd.read_json(path, lines=True)
    raise ValueError(f"Unsupported file type: {suffix}")


def maybe_sample(df: pd.DataFrame, sample: int | None) -> tuple[pd.DataFrame, dict]:
    n = len(df)
    if sample and n > sample:
        sampled = df.sample(n=sample, random_state=42)
        return sampled, {"sampled": True, "method": "random", "size": sample, "original_rows": n}
    if not sample and n > SAMPLE_THRESHOLD:
        sampled = df.sample(n=SAMPLE_THRESHOLD, random_state=42)
        return sampled, {
            "sampled": True,
            "method": "random (auto, dataset > 50k rows)",
            "size": SAMPLE_THRESHOLD,
            "original_rows": n,
        }
    return df, {"sampled": False, "original_rows": n}


def _is_textlike(s: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)


def detect_datetime_cols(df: pd.DataFrame) -> list[str]:
    out = []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            out.append(col)
            continue
        if _is_textlike(df[col]):
            sample_vals = df[col].dropna().astype(str).head(50)
            if len(sample_vals) == 0:
                continue
            try:
                parsed = pd.to_datetime(sample_vals, errors="raise", format="mixed")
                if parsed.notna().mean() > 0.9:
                    out.append(col)
            except (ValueError, TypeError):
                pass
    return out


def numeric_summary(df: pd.DataFrame) -> dict:
    nums = df.select_dtypes(include=[np.number])
    out = {}
    for col in nums.columns:
        s = nums[col].dropna()
        if s.empty:
            out[col] = {"count": 0, "note": "all null"}
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        outlier_mask = (s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)
        out[col] = {
            "count": int(s.count()),
            "min": float(s.min()),
            "max": float(s.max()),
            "mean": float(s.mean()),
            "median": float(s.median()),
            "std": float(s.std()) if s.count() > 1 else 0.0,
            "q1": float(q1),
            "q3": float(q3),
            "outlier_count_iqr": int(outlier_mask.sum()),
        }
    return out


def categorical_summary(df: pd.DataFrame, max_categories: int) -> dict:
    out = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        s = df[col].dropna().astype(str)
        if s.empty:
            out[col] = {"unique": 0, "note": "all null"}
            continue
        counts = s.value_counts().head(max_categories)
        out[col] = {
            "unique": int(s.nunique()),
            "top_values": [
                {"value": str(idx), "count": int(val)} for idx, val in counts.items()
            ],
        }
    return out


def quality_flags(df: pd.DataFrame) -> dict:
    n = len(df)
    flags = {
        "rows": int(n),
        "duplicate_rows": int(df.duplicated().sum()),
        "fully_empty_rows": int(df.isna().all(axis=1).sum()),
        "missing_per_column": {},
        "mostly_empty_columns": [],
        "mixed_type_columns": [],
    }
    for col in df.columns:
        miss = int(df[col].isna().sum())
        pct = miss / n if n else 0
        flags["missing_per_column"][col] = {"count": miss, "pct": round(pct, 4)}
        if pct > 0.5:
            flags["mostly_empty_columns"].append(col)
        if _is_textlike(df[col]):
            non_null = df[col].dropna()
            if len(non_null):
                types = set(type(v).__name__ for v in non_null.head(200))
                if len(types) > 1:
                    flags["mixed_type_columns"].append({"column": col, "types": sorted(types)})
    return flags


def build_charts(df: pd.DataFrame, datetime_cols: list[str], pdf_path: Path) -> list[dict]:
    """Generate charts to a single PDF. Return a list of chart descriptions."""
    descriptions = []
    nums = df.select_dtypes(include=[np.number])
    cats = [
        c
        for c in df.columns
        if c not in nums.columns
        and c not in datetime_cols
        and not pd.api.types.is_datetime64_any_dtype(df[c])
    ]

    with PdfPages(pdf_path) as pdf:
        for col in nums.columns:
            s = nums[col].dropna()
            if s.empty:
                continue
            fig, ax = plt.subplots(figsize=(8, 4.5))
            ax.hist(s, bins=min(40, max(10, int(np.sqrt(len(s))))), edgecolor="white")
            ax.set_title(f"Distribution: {col}")
            ax.set_xlabel(col)
            ax.set_ylabel("Frequency")
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
            descriptions.append({"chart": f"Distribution: {col}", "type": "histogram"})

        for col in cats:
            s = df[col].dropna().astype(str)
            if s.empty:
                continue
            n_unique = s.nunique()
            # Skip high-cardinality columns (likely IDs, emails, free text):
            # a "top 15" chart of 500 unique values shows nothing useful.
            if n_unique > max(30, len(s) * 0.5):
                continue
            counts = s.value_counts().head(15)
            if len(counts) < 2:
                continue
            fig, ax = plt.subplots(figsize=(8, 4.5))
            counts.iloc[::-1].plot(kind="barh", ax=ax)
            ax.set_title(f"Top values: {col}")
            ax.set_xlabel("Count")
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
            descriptions.append({"chart": f"Top values: {col}", "type": "bar"})

        for tcol in datetime_cols:
            try:
                ts = pd.to_datetime(df[tcol], errors="coerce", format="mixed").dropna()
            except Exception:
                continue
            if ts.empty:
                continue
            counts_by_day = ts.dt.floor("D").value_counts().sort_index()
            if len(counts_by_day) < 2:
                continue
            fig, ax = plt.subplots(figsize=(9, 4))
            counts_by_day.plot(ax=ax)
            ax.set_title(f"Records over time: {tcol}")
            ax.set_xlabel(tcol)
            ax.set_ylabel("Records per day")
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
            descriptions.append({"chart": f"Records over time: {tcol}", "type": "timeseries"})

        if nums.shape[1] >= 2:
            corr = nums.corr(numeric_only=True)
            fig, ax = plt.subplots(figsize=(min(10, 1.2 * len(corr)), min(10, 1.2 * len(corr))))
            im = ax.imshow(corr.values, vmin=-1, vmax=1, cmap="coolwarm")
            ax.set_xticks(range(len(corr.columns)))
            ax.set_xticklabels(corr.columns, rotation=45, ha="right")
            ax.set_yticks(range(len(corr.columns)))
            ax.set_yticklabels(corr.columns)
            ax.set_title("Correlation between numeric columns")
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
            descriptions.append({"chart": "Correlation matrix", "type": "heatmap"})

    return descriptions


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--sample", type=int, default=None)
    p.add_argument("--sheet", type=str, default=None)
    p.add_argument("--max-categories", type=int, default=20)
    args = p.parse_args()

    if not args.input.exists():
        sys.exit(f"File not found: {args.input}")

    output_dir = args.output_dir or args.input.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.input.stem

    df = load(args.input, args.sheet)
    df, sampling = maybe_sample(df, args.sample)
    datetime_cols = detect_datetime_cols(df)

    profile = {
        "source_file": str(args.input),
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "sampling": sampling,
        "columns": [
            {"name": c, "dtype": str(df[c].dtype)}
            for c in df.columns
        ],
        "datetime_columns": datetime_cols,
        "numeric_summary": numeric_summary(df),
        "categorical_summary": categorical_summary(df, args.max_categories),
        "quality": quality_flags(df),
    }

    charts_pdf = output_dir / f"{stem}-charts.pdf"
    profile["charts"] = build_charts(df, datetime_cols, charts_pdf)

    profile_path = output_dir / f"{stem}-profile.json"
    profile_path.write_text(json.dumps(profile, indent=2, default=str))

    print(json.dumps({
        "profile_json": str(profile_path),
        "charts_pdf": str(charts_pdf),
        "rows": profile["shape"]["rows"],
        "columns": profile["shape"]["columns"],
        "sampled": sampling.get("sampled", False),
    }, indent=2))


if __name__ == "__main__":
    main()
