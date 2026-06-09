"""Extract pandoc reference template from a real thesis docx.

Pandoc copies styles from a reference docx when generating output.
Use a classmate's thesis (Erica Negaliuc) as the style source.

Usage:
    python3 extract_reference_template.py --source /path/to/Erica_thesis.docx

Output:
    docs/thesis/reference_examples/reference_template.docx
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy reference thesis docx as pandoc style template"
    )
    parser.add_argument("--source", required=True, help="Path to reference docx (e.g. Erica thesis)")
    parser.add_argument(
        "--output",
        default="docs/thesis/reference_examples/reference_template.docx",
        help="Destination path for the template",
    )
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output)

    if not source.exists():
        raise SystemExit(f"Source file not found: {source}")

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(source, output)

    size_kb = output.stat().st_size // 1024
    print(f"✓ Copied {source.name} → {output}  ({size_kb} KB)")
    print("\nNext steps:")
    print("  bash docs/thesis/scripts/build.sh")


if __name__ == "__main__":
    main()
