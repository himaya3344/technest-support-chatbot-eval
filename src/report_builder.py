"""Build the TechNest evaluation report from generated artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


TABLE_FILES = [
	"by_action.csv",
	"by_category.csv",
	"failure_frequency.csv",
	"failure_crosstab.csv",
	"judge_by_category.csv",
	"run_consistency.csv",
]
FIGURE_FILES = [
	"accuracy_by_category.png",
	"confusion_matrix.png",
	"failure_frequency.png",
	"mean_judge_scores.png",
	"latency_distribution.png",
	"consistency_by_category.png",
]


def _to_markdown(frame: pd.DataFrame) -> str:
	"""Render a DataFrame as Markdown without requiring tabulate."""
	if frame.empty:
		return "_Available, but empty._"
	columns = [str(column) for column in frame.columns]
	rows = [[str(value) for value in row] for row in frame.fillna("").itertuples(index=False, name=None)]
	lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
	lines.extend("| " + " | ".join(row) + " |" for row in rows)
	return "\n".join(lines)


def _markdown_table(path: Path) -> str:
	"""Render a CSV file as a Markdown table."""
	frame = pd.read_csv(path)
	if frame.empty:
		return "_Available, but empty._"
	return _to_markdown(frame)


def _artifact_note(path: Path, kind: str) -> str:
	"""Describe a missing or empty generated artifact."""
	if not path.exists():
		return f"_Skipped: {kind} `{path.name}` is missing._"
	if path.suffix == ".csv" and pd.read_csv(path).empty:
		return f"_Skipped: {kind} `{path.name}` is empty._"
	return ""


def _render_tables(metrics_dir: Path) -> str:
	"""Render all requested metric tables, noting unavailable tables."""
	sections: list[str] = []
	for filename in TABLE_FILES:
		path = metrics_dir / filename
		if not path.exists():
			sections.append(f"### {filename}\n{_artifact_note(path, 'metric table')}")
			continue
		sections.append(f"### {filename}\n{_markdown_table(path)}")
	return "\n\n".join(sections)


def _render_table(metrics_dir: Path, filename: str) -> str:
	"""Render one named metric table or its unavailable-artifact note."""
	path = metrics_dir / filename
	return _markdown_table(path) if path.exists() else _artifact_note(path, "metric table")


def _render_figures(figures_dir: Path) -> str:
	"""Render relative Markdown links for available figures."""
	links: list[str] = []
	for filename in FIGURE_FILES:
		path = figures_dir / filename
		if path.exists():
			links.append(f"![{filename}](../results/figures/{filename})")
		else:
			links.append(f"- {_artifact_note(path, 'figure')}")
	return "\n".join(links)


def _render_json_summary(metrics_path: Path) -> str:
	"""Render scalar and nested JSON metrics as a compact Markdown table."""
	if not metrics_path.exists():
		return "_Skipped: `metrics.json` is missing._"
	data: dict[str, Any] = json.loads(metrics_path.read_text(encoding="utf-8"))
	rows: list[dict[str, str]] = []
	for key, value in data.items():
		if isinstance(value, (dict, list)):
			value = json.dumps(value, ensure_ascii=False)
		rows.append({"metric": key, "value": str(value)})
	return _to_markdown(pd.DataFrame(rows))


def _render_appendix(data_dir: Path) -> str:
	"""Render full test cases, system prompt, and judge rubric."""
	case_path = data_dir / "test_cases.json"
	if case_path.exists():
		cases = pd.DataFrame(json.loads(case_path.read_text(encoding="utf-8")))
		case_table = _to_markdown(cases) if not cases.empty else "_Test case file is empty._"
	else:
		case_table = "_Skipped: test_cases.json is missing._"
	parts = [f"### Full test case table\n{case_table}"]
	for title, filename in (("System prompt", "system_prompt.txt"), ("Judge rubric", "judge_rubric.md")):
		path = data_dir / filename
		content = path.read_text(encoding="utf-8") if path.exists() else f"[Skipped: {filename} is missing.]"
		parts.append(f"### {title}\n\n```text\n{content}\n```")
	return "\n\n".join(parts)


def build_report(root: Path, scored_path: Path) -> str:
	"""Build the complete report Markdown from repository artifacts."""
	metrics_dir = root / "results" / "metrics"
	figures_dir = root / "results" / "figures"
	data_dir = root / "data"
	return f"""# TechNest Chatbot Evaluation Report

## 1. Introduction and business problem

[WRITE MANUALLY] Describe TechNest's customer-support quality and risk problem, intended users, and business impact.

## 2. Methodology

[WRITE MANUALLY] Document the selected model, temperature, prompts, number of runs, judge model, and reproducibility settings.

Scored input: `{scored_path.as_posix()}`

## 3. Test set design and labeling process

[WRITE MANUALLY] Describe categories, difficulty levels, case construction, expected actions, required phrases, forbidden phrases, and human-labeling procedures.

## 4. Results

### Metric summary

{_render_json_summary(metrics_dir / 'metrics.json')}

### Auto-generated metric tables

{_render_tables(metrics_dir)}

### Figures

{_render_figures(figures_dir)}

## 5. Failure pattern analysis

[WRITE MANUALLY] Discuss root causes, severity, and operational implications of the observed failures.

### Ranked failure frequency

{_render_table(metrics_dir, 'failure_frequency.csv')}

### Failure cross-tabulation

{_render_table(metrics_dir, 'failure_crosstab.csv')}

### Representative cases

{_markdown_table(metrics_dir / 'failures.csv') if (metrics_dir / 'failures.csv').exists() else '_Skipped: failures.csv is missing._'}

## 6. Limitations and threats to validity

[WRITE MANUALLY] Discuss sample size, synthetic cases, judge reliability, model/version drift, annotation limitations, and generalizability.

## 7. Recommendations

[WRITE MANUALLY] Provide prioritized engineering, policy, monitoring, and evaluation recommendations.

## 8. Appendix

{_render_appendix(data_dir)}
"""


def write_report(root: Path, scored_path: Path, output_path: Path | None = None) -> Path:
	"""Build and write report/report.md."""
	target = output_path or root / "report" / "report.md"
	target.parent.mkdir(parents=True, exist_ok=True)
	target.write_text(build_report(root, scored_path), encoding="utf-8")
	return target
