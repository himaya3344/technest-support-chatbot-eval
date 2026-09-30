"""Generate evaluation charts from scored results and metric tables."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _save_chart(name: str, draw: Callable[[plt.Axes], None], figures_dir: Path) -> None:
	"""Draw and save one chart, reporting missing or empty inputs gracefully."""
	try:
		figure, axes = plt.subplots(figsize=(8, 5))
		draw(axes)
		figure.tight_layout()
		figure.savefig(figures_dir / name, dpi=200, bbox_inches="tight")
		plt.close(figure)
		print(f"Saved chart: {figures_dir / name}")
	except (KeyError, IndexError, OSError, ValueError) as exc:
		plt.close("all")
		print(f"Skipped {name}: {exc}")


def _require(frame: pd.DataFrame, columns: list[str], label: str) -> None:
	"""Require non-empty data and named columns for a chart."""
	if frame.empty:
		raise ValueError(f"{label} is empty")
	missing = [column for column in columns if column not in frame]
	if missing:
		raise KeyError(f"missing columns: {', '.join(missing)}")


def plot_accuracy_by_category(by_category: pd.DataFrame, figures_dir: Path) -> None:
	"""Plot action accuracy by test-case category."""
	def draw(axes: plt.Axes) -> None:
		_require(by_category, ["category", "action_accuracy"], "category accuracy")
		axes.bar(by_category["category"], by_category["action_accuracy"])
		axes.set_xlabel("Test case category")
		axes.set_ylabel("Action accuracy")
		axes.set_title("Action Accuracy by Test Category")
		axes.set_ylim(0, 1)
		axes.tick_params(axis="x", rotation=35)
	_save_chart("accuracy_by_category.png", draw, figures_dir)


def plot_confusion_matrix(metrics: dict, figures_dir: Path) -> None:
	"""Plot the action confusion matrix as a heatmap."""
	def draw(axes: plt.Axes) -> None:
		confusion = metrics.get("confusion_matrix", {})
		labels = confusion.get("labels", [])
		matrix = np.asarray(confusion.get("matrix", []))
		if not labels or matrix.size == 0:
			raise ValueError("confusion matrix is empty")
		image = axes.imshow(matrix, cmap="Blues")
		axes.figure.colorbar(image, ax=axes, label="Count")
		axes.set_xticks(range(len(labels)), labels=labels, rotation=35)
		axes.set_yticks(range(len(labels)), labels=labels)
		axes.set_xlabel("Predicted action")
		axes.set_ylabel("Expected action")
		axes.set_title("Action Confusion Matrix")
		for row in range(matrix.shape[0]):
			for column in range(matrix.shape[1]):
				axes.text(column, row, int(matrix[row, column]), ha="center", va="center")
	_save_chart("confusion_matrix.png", draw, figures_dir)


def plot_failure_frequency(frequency: pd.DataFrame, figures_dir: Path) -> None:
	"""Plot failure categories from highest to lowest frequency."""
	def draw(axes: plt.Axes) -> None:
		_require(frequency, ["failure_category", "count"], "failure frequency")
		ordered = frequency.sort_values("count")
		axes.barh(ordered["failure_category"], ordered["count"])
		axes.set_xlabel("Failure count")
		axes.set_ylabel("Failure category")
		axes.set_title("Failure Type Frequency")
	_save_chart("failure_frequency.png", draw, figures_dir)


def plot_mean_judge_scores(scored: pd.DataFrame, figures_dir: Path) -> None:
	"""Plot mean judge scores for each rubric dimension."""
	dimensions = ["correctness", "groundedness", "completeness", "tone"]
	def draw(axes: plt.Axes) -> None:
		_require(scored, dimensions, "judge scores")
		means = pd.to_numeric(scored[dimensions].stack(), errors="coerce").groupby(level=1).mean()
		means = means.dropna()
		if means.empty:
			raise ValueError("judge scores are empty")
		axes.bar(means.index, means.values)
		axes.set_xlabel("Judge dimension")
		axes.set_ylabel("Mean score (1-5)")
		axes.set_title("Mean Judge Scores by Dimension")
		axes.set_ylim(0, 5)
		axes.tick_params(axis="x", rotation=25)
	_save_chart("mean_judge_scores.png", draw, figures_dir)


def plot_latency_distribution(scored: pd.DataFrame, figures_dir: Path) -> None:
	"""Plot the distribution of recorded request latency."""
	def draw(axes: plt.Axes) -> None:
		_require(scored, ["latency_s"], "latency")
		values = pd.to_numeric(scored["latency_s"], errors="coerce").dropna()
		if values.empty:
			raise ValueError("latency is empty")
		axes.hist(values, bins=min(20, max(1, len(values))))
		axes.set_xlabel("Latency (seconds)")
		axes.set_ylabel("Number of results")
		axes.set_title("Latency Distribution")
	_save_chart("latency_distribution.png", draw, figures_dir)


def plot_consistency_by_category(
	run_consistency: pd.DataFrame,
	cases_path: Path,
	figures_dir: Path,
) -> None:
	"""Plot the share of consistent runs by test-case category."""
	def draw(axes: plt.Axes) -> None:
		_require(run_consistency, ["case_id", "all_actions_agree"], "run consistency")
		with cases_path.open(encoding="utf-8") as file:
			cases = pd.DataFrame(json.load(file))[["id", "category"]].rename(columns={"id": "case_id"})
		joined = run_consistency.merge(cases, on="case_id", how="left")
		joined["all_actions_agree"] = joined["all_actions_agree"].map(
			lambda value: value if isinstance(value, bool) else str(value).lower() == "true"
		)
		grouped = joined.groupby("category", dropna=False)["all_actions_agree"].mean().dropna()
		if grouped.empty:
			raise ValueError("category consistency is empty")
		axes.bar(grouped.index, grouped.values)
		axes.set_xlabel("Test case category")
		axes.set_ylabel("All runs agree")
		axes.set_title("Run-to-Run Consistency by Category")
		axes.set_ylim(0, 1)
		axes.tick_params(axis="x", rotation=35)
	_save_chart("consistency_by_category.png", draw, figures_dir)


def plot_all(
	scored: pd.DataFrame,
	metrics: dict,
	tables: dict[str, pd.DataFrame],
	cases_path: Path,
	figures_dir: Path,
) -> None:
	"""Generate all requested figures, skipping unavailable charts individually."""
	figures_dir.mkdir(parents=True, exist_ok=True)
	plot_accuracy_by_category(tables.get("by_category", pd.DataFrame()), figures_dir)
	plot_confusion_matrix(metrics, figures_dir)
	plot_failure_frequency(tables.get("failure_frequency", pd.DataFrame()), figures_dir)
	plot_mean_judge_scores(scored, figures_dir)
	plot_latency_distribution(scored, figures_dir)
	plot_consistency_by_category(tables.get("run_consistency", pd.DataFrame()), cases_path, figures_dir)
