---
name: dataset-decision-brief
description: >
  Turn a raw dataset (CSV, Excel, JSON) into a decision brief with charts.
  Trigger this skill whenever the user has a data file they want analyzed,
  profiled, or summarized — including phrases like "explore this CSV",
  "profile this dataset", "what's in this spreadsheet", "build me a decision
  brief from this data", "analyze this Excel file", "find issues in this
  data", "summarize this dataset for the team", or "I have a dataset and
  need to make a decision". Also trigger on "data quality check", "data
  audit", or "give me an exec summary of this data". Even when the user
  doesn't explicitly say "brief" — if they have a tabular file and an
  unclear path forward, this skill is the answer.
---

# Dataset → Decision Brief

Take a raw tabular file (CSV / XLSX / JSON) and produce two artifacts that
sit next to the source:

- `<dataset-name>-analysis.md` — a 6-section decision brief
- `<dataset-name>-charts.pdf` — a multi-page chart deck

The skill bundles a Python profiling script (`scripts/profile_dataset.py`)
that does all the deterministic work — loading, profiling, descriptive
stats, quality flags, and chart generation. Your job is the part the script
can't do: interpret what the numbers mean *for the user's specific
business question* and write a brief that's actually useful for a decision.

## Step 1 — Locate the file

The user will usually tell you a folder (Downloads, Desktop, or a path)
and a partial filename or topic. If they don't:

- Ask which folder to search (default `~/Downloads`).
- Ask for the **business question** if not given. This is non-negotiable
  — without it you'll write a generic profile, which is worse than the
  user just running `pandas.describe()` themselves. The whole point of
  the brief is that it answers a specific question.

Search:

```bash
find <folder> -maxdepth 3 -type f \
  \( -iname "*<keyword>*" \) \
  \( -iname "*.csv" -o -iname "*.xlsx" -o -iname "*.xls" -o -iname "*.json" \) \
  -mtime -90 -print0 \
  | xargs -0 ls -lt 2>/dev/null | head -20
```

Disambiguation:

- One match → confirm the file with the user before reading it.
- Multiple → show top results by mtime + size, ask which.
- None → broaden the search (drop keyword, widen date) before asking.

## Step 2 — Run the profiling script

```bash
python <path-to-skill>/scripts/profile_dataset.py <input-file>
```

By default the script writes both outputs to the same folder as the input.
Override with `--output-dir`. For Excel files with multiple sheets, pass
`--sheet "<name>"` (default is the first sheet). For datasets you know are
huge, pass `--sample 50000` (the script auto-samples above 50k anyway, but
you can force a smaller sample).

The script prints a small JSON to stdout with the paths it wrote and
whether it sampled. Read the `<stem>-profile.json` it wrote — that's where
all the structured data lives. Don't try to recompute these numbers
yourself; you'll be slower and inconsistent across runs.

### If dependencies are missing

The script needs `pandas`, `numpy`, `matplotlib`, and (for `.xlsx`)
`openpyxl`. If it exits with the missing-deps message, install them:

```bash
pip install pandas numpy matplotlib openpyxl
```

Use `pipenv` or the project's chosen Python tooling if appropriate; don't
silently install into the system Python without checking.

## Step 3 — Read the profile and view the charts

The profile JSON has these top-level keys:

- `shape` — rows × columns
- `sampling` — whether the script sampled and from what original size
- `columns` — name + dtype for each column
- `datetime_columns` — columns the script detected as datetime-like
- `numeric_summary` — min/max/mean/median/std/IQR + outlier counts per
  numeric column
- `categorical_summary` — top values per non-numeric column
- `quality` — duplicates, missing values per column, mixed-type columns,
  mostly-empty columns
- `charts` — the chart titles in `<stem>-charts.pdf`, in order

Open the chart PDF with the Read tool (it supports PDFs) so you can speak
to specific charts in the brief.

## Step 4 — Write the decision brief

Use this exact 6-section structure. Section order matters — the user
probably reads the Decision Brief, decides whether to keep going, then
drills into 2–6 only if needed.

```markdown
# [Dataset Name] — Decision Brief

> **Business question:** [verbatim from user]
> **Source:** [absolute path to source file]
> **Rows × cols:** N × M [• Sampled to K rows from N — note this clearly if true]
> **Generated:** YYYY-MM-DD

## 1. Decision Brief
- **3 most important findings** (each tied directly to the business question)
- **Biggest risk if nothing changes** (one item, concrete)
- **2 fastest wins available right now** (specific, actionable)

## 2. Data Overview
- Row count, column count, dtypes
- Date range if time-series (use the chart "Records over time: <col>")
- Mostly-empty columns and clearly-malformed columns

## 3. Key Distributions & Patterns
- Per numeric column: min, max, mean, median, std (from `numeric_summary`)
- Per categorical column: top values + counts (from `categorical_summary`)
- Notable correlations from the correlation chart, *only if they matter
  to the business question*. Don't list every above-zero correlation.

## 4. Data Quality Issues
- Missing values: where, how many, whether random or clustered
- Duplicates: count + likely cause
- Mixed types or impossible values: flag with column name
- For each issue: a one-line guess at root cause (collection bug, merge,
  human entry, schema drift). Mark guesses as guesses.

## 5. Chart Summary
- List each chart in `<stem>-charts.pdf` in PDF page order
- One sentence per chart: what it shows + why it matters for the question

## 6. Collection Recommendations
- Only fill this section if the user owns the data pipeline (ask if unclear).
- What should change in collection? What fields to add/remove? What
  validation rules would have prevented the issues found in §4?
- If the user doesn't own the pipeline, replace this section with a one-line
  note: "User does not own the pipeline — section omitted."
```

### What "good" looks like

- **Findings are claims with evidence**, not observations. "Average order
  value is $42" is an observation. "Average order value dropped 18% after
  the March pricing change — see histogram p.3" is a finding.
- **The biggest risk is one risk.** If you can't pick one, the brief
  isn't done — keep working on the data.
- **Fast wins are specific.** "Improve data quality" is not a fast win.
  "Add a NOT NULL constraint on `customer_email` — 12% of rows are
  missing it" is a fast win.
- **Don't include charts the brief doesn't reference.** If the script
  produced 8 charts but only 4 are relevant, say so in §5 and tell the
  user to skim the rest.
- **When the data can't answer the question, say so.** A brief that
  honestly says "this dataset doesn't have the columns you'd need to
  answer X — here's what would" is more valuable than one that fabricates
  signal from noise. Recommend what to collect next.

### Sampling discipline

If the script sampled, every conclusion is a sample-based claim. Add a
short note at the top of §1 — something like *"Findings are based on a
random sample of 50,000 of 2.3M rows; aggregate counts in §3 are scaled
estimates."* Don't quietly hide the sampling from the reader.

## Step 5 — Save and report

Save the markdown to `<source-folder>/<dataset-stem>-analysis.md`. The
chart PDF is already there from step 2.

If a brief with that name already exists, don't overwrite. Append a date
suffix (`-2026-05-07`) and tell the user.

After saving, give the user a 3-line summary in chat:
1. The single most important finding (one sentence)
2. The biggest risk (one sentence)
3. Where the brief and chart PDF were saved

This way they can decide in 10 seconds whether to open the file now.

## Edge cases

- **Multi-sheet Excel without `--sheet`.** The script defaults to sheet 0.
  If the file looks like it has multiple meaningful sheets (check with
  the Read tool first or `xlsx2csv -l`), confirm with the user which
  sheet to analyze before running the script.
- **JSON that isn't tabular.** The script tries normal JSON then JSON
  Lines. If both fail or the data is deeply nested, tell the user the
  shape isn't tabular and ask whether to flatten (and how) or pick a
  specific sub-array.
- **Single-column or near-empty files.** Run the script anyway, but
  shorten the brief — there's no story in 3 rows of one column. Tell the
  user the data is too thin for a useful decision brief and suggest what
  to add.
- **PII in the data.** If columns clearly hold emails, phone numbers, or
  other PII, mention this in §4 and recommend masking before sharing the
  brief externally. Don't refuse to analyze — but don't paste raw PII
  into the brief.
- **Time series with gaps.** If "Records over time" shows obvious gaps,
  call them out in §4 (collection outage? holiday? deletion?). They're
  often the most decision-relevant signal in the file.
