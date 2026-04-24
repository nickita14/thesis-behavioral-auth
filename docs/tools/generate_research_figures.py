from __future__ import annotations

import ast
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FIGURES_DIR = ROOT / "docs" / "figures"
PHISHING_ARTIFACT = ROOT / "data" / "models" / "phishing_xgboost_v1.joblib"
URL_FEATURES_FILE = ROOT / "backend" / "apps" / "phishing" / "extractors" / "base.py"
BEHAVIOR_FEATURES_FILE = ROOT / "backend" / "apps" / "ml_engine" / "behavior_features.py"


def ensure_runtime() -> None:
    """Re-run with the project venv when the current Python lacks plotting deps."""
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    try:
        import joblib  # noqa: F401
        import matplotlib  # noqa: F401
    except ModuleNotFoundError:
        venv_python = ROOT / ".venv" / "bin" / "python"
        if venv_python.exists() and os.environ.get("RESEARCH_FIGURES_REEXECED") != "1":
            os.environ["RESEARCH_FIGURES_REEXECED"] = "1"
            os.execv(str(venv_python), [str(venv_python), *sys.argv])
        raise


ensure_runtime()

import joblib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


@dataclass(frozen=True)
class FigureResult:
    path: Path
    note: str


PHISHING_GROUPS = {
    "Lexical": [
        "having_ip_address",
        "url_length",
        "shortining_service",
        "having_at_symbol",
        "double_slash_redirecting",
        "prefix_suffix",
        "having_sub_domain",
        "https_token",
    ],
    "SSL / Domain": [
        "sslfinal_state",
        "domain_registration_length",
        "favicon",
        "port",
        "age_of_domain",
        "dnsrecord",
    ],
    "HTML / JS": [
        "request_url",
        "url_of_anchor",
        "links_in_tags",
        "sfh",
        "submitting_to_email",
        "abnormal_url",
        "redirect",
        "on_mouseover",
        "rightclick",
        "popupwindow",
        "iframe",
    ],
    "External / Reputation": [
        "web_traffic",
        "page_rank",
        "google_index",
        "links_pointing_to_page",
        "statistical_report",
    ],
}

BEHAVIOR_GROUPS = {
    "Session": [
        "session_duration_ms",
    ],
    "Keystroke": [
        "keystroke_count",
        "keydown_count",
        "keyup_count",
        "avg_dwell_time_ms",
        "std_dwell_time_ms",
        "avg_flight_time_ms",
        "std_flight_time_ms",
        "typing_speed_keys_per_second",
    ],
    "Mouse": [
        "mouse_event_count",
        "mouse_move_count",
        "mouse_click_count",
        "mouse_scroll_count",
        "mouse_path_length",
        "avg_mouse_speed",
        "max_mouse_speed",
    ],
}


def dataclass_field_names(path: Path, class_name: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return [
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            ]
    raise RuntimeError(f"{class_name} not found in {path}")


def save_bar_chart(path: Path, title: str, labels: list[str], values: list[int]) -> FigureResult:
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.barh(labels, values)
    ax.set_xlabel("Number of features")
    ax.set_title(title)
    ax.invert_yaxis()
    for index, value in enumerate(values):
        ax.text(value + 0.1, index, str(value), va="center")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return FigureResult(path, f"created {path.name}")


def generate_phishing_feature_groups() -> FigureResult:
    feature_names = set(dataclass_field_names(URL_FEATURES_FILE, "URLFeatures"))
    grouped = {name for names in PHISHING_GROUPS.values() for name in names}
    missing = sorted(feature_names - grouped)
    extra = sorted(grouped - feature_names)
    if missing or extra:
        raise RuntimeError(f"URLFeatures grouping mismatch: missing={missing}, extra={extra}")

    return save_bar_chart(
        FIGURES_DIR / "phishing_feature_groups.png",
        "Phishing URL Feature Groups",
        list(PHISHING_GROUPS.keys()),
        [len(values) for values in PHISHING_GROUPS.values()],
    )


def load_feature_importance() -> tuple[list[str], list[float], str]:
    artifact = joblib.load(PHISHING_ARTIFACT)
    model: Any = artifact.get("model") if isinstance(artifact, dict) else artifact
    feature_names = artifact.get("feature_names") if isinstance(artifact, dict) else None
    if feature_names is None and hasattr(model, "feature_names_in_"):
        feature_names = list(model.feature_names_in_)
    if feature_names is None:
        feature_names = dataclass_field_names(URL_FEATURES_FILE, "URLFeatures")

    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        raise RuntimeError("model artifact has no feature_importances_")

    return list(feature_names), [float(value) for value in importances], "real XGBoost feature_importances_"


def generate_phishing_feature_importance() -> FigureResult:
    path = FIGURES_DIR / "phishing_feature_importance.png"
    try:
        feature_names, importances, note = load_feature_importance()
        top = sorted(zip(feature_names, importances, strict=False), key=lambda item: item[1])[-10:]
        labels = [name for name, _ in top]
        values = [value for _, value in top]

        fig, ax = plt.subplots(figsize=(10, 5.6))
        ax.barh(labels, values)
        ax.set_xlabel("Feature importance")
        ax.set_title("Top 10 XGBoost Phishing Feature Importances")
        for index, value in enumerate(values):
            ax.text(value + max(values) * 0.01, index, f"{value:.3f}", va="center")
        fig.tight_layout()
        fig.savefig(path, dpi=200)
        plt.close(fig)
        return FigureResult(path, f"created from {note}")
    except Exception as exc:
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.axis("off")
        ax.text(
            0.5,
            0.5,
            "Feature importance unavailable\n"
            f"{exc}\n"
            "Use the model artifact with feature_importances_ to regenerate this figure.",
            ha="center",
            va="center",
            wrap=True,
        )
        ax.set_title("Phishing Feature Importance")
        fig.tight_layout()
        fig.savefig(path, dpi=200)
        plt.close(fig)
        return FigureResult(path, f"placeholder: {exc}")


def generate_behavior_feature_groups() -> FigureResult:
    feature_names = set(dataclass_field_names(BEHAVIOR_FEATURES_FILE, "BehaviorFeatures"))
    grouped = {name for names in BEHAVIOR_GROUPS.values() for name in names}
    missing = sorted(feature_names - grouped)
    extra = sorted(grouped - feature_names)
    if missing or extra:
        raise RuntimeError(f"BehaviorFeatures grouping mismatch: missing={missing}, extra={extra}")

    return save_bar_chart(
        FIGURES_DIR / "behavior_feature_groups.png",
        "Behavior Feature Groups",
        list(BEHAVIOR_GROUPS.keys()),
        [len(values) for values in BEHAVIOR_GROUPS.values()],
    )


def generate_transaction_decision_matrix() -> FigureResult:
    path = FIGURES_DIR / "transaction_decision_matrix.png"
    rows = [
        ("Phishing = phishing", "DENY"),
        ("Phishing = suspicious", "CHALLENGE"),
        ("Phishing error + target_url", "CHALLENGE"),
        ("Behavior = anomalous", "CHALLENGE"),
        ("Behavior = suspicious + amount >= 1000", "CHALLENGE"),
        ("Otherwise", "ALLOW"),
    ]

    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.axis("off")
    table = ax.table(
        cellText=rows,
        colLabels=["Risk condition", "Final decision"],
        cellLoc="left",
        colLoc="left",
        loc="center",
        colWidths=[0.72, 0.28],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.7)
    for (row, _col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight="bold")
    ax.set_title("Transaction Decision Matrix", pad=20)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return FigureResult(path, "created rule matrix")


def add_node(ax, xy: tuple[float, float], text: str, width: float = 1.8) -> None:
    x, y = xy
    box = FancyBboxPatch(
        (x - width / 2, y - 0.28),
        width,
        0.56,
        boxstyle="round,pad=0.04",
        linewidth=1.2,
        facecolor="white",
        edgecolor="black",
    )
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center", fontsize=9)


def add_arrow(ax, start: tuple[float, float], end: tuple[float, float]) -> None:
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={"arrowstyle": "->", "linewidth": 1.2},
    )


def generate_end_to_end_flow() -> FigureResult:
    path = FIGURES_DIR / "end_to_end_flow.png"
    fig, ax = plt.subplots(figsize=(12.5, 5.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")

    nodes = {
        "ui": (1.1, 3.5, "Login / Transaction UI"),
        "collector": (3.0, 3.5, "Behavior Collector"),
        "events": (5.0, 3.5, "BehaviorSession\nEvents"),
        "features": (7.0, 3.5, "BehaviorFeature\nExtractor"),
        "iforest": (9.0, 3.5, "IsolationForest\nAnomaly Score"),
        "xgb": (5.0, 1.5, "Phishing XGBoost\nURL Risk"),
        "risk": (7.2, 1.5, "RiskAssessment"),
        "decision": (9.2, 1.5, "ALLOW /\nCHALLENGE /\nDENY"),
    }
    for x, y, label in nodes.values():
        add_node(ax, (x, y), label)

    add_arrow(ax, (2.0, 3.5), (2.1, 3.5))
    add_arrow(ax, (3.9, 3.5), (4.1, 3.5))
    add_arrow(ax, (5.9, 3.5), (6.1, 3.5))
    add_arrow(ax, (7.9, 3.5), (8.1, 3.5))
    add_arrow(ax, (1.8, 3.22), (4.2, 1.74))
    add_arrow(ax, (5.9, 1.5), (6.1, 1.5))
    add_arrow(ax, (7.95, 1.5), (8.25, 1.5))
    add_arrow(ax, (8.5, 3.22), (7.55, 1.82))

    ax.set_title("End-to-End Research Flow: Dataset -> Features -> Models -> Decision")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return FigureResult(path, "created flow diagram")


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    results = [
        generate_phishing_feature_groups(),
        generate_phishing_feature_importance(),
        generate_behavior_feature_groups(),
        generate_transaction_decision_matrix(),
        generate_end_to_end_flow(),
    ]

    print("Generated research figures:")
    for result in results:
        print(f"- {result.path.relative_to(ROOT)}: {result.note}")
    print()
    print("Limitations:")
    print("- UCI raw phishing dataset is not present under data/; figures use URLFeatures and model artifact metadata.")


if __name__ == "__main__":
    main()
