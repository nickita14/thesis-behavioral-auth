"""Concatenate chapter md files in sorted filename order.

Files like 00_titulnyi.md, 01_*.md, etc. are concatenated with
double-newline separators and a page break marker between each chapter.
"""
from __future__ import annotations

from pathlib import Path
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Concatenate thesis chapter .md files in order"
    )
    parser.add_argument("--chapters-dir", required=True, help="Directory with *.md chapter files")
    parser.add_argument("--output", required=True, help="Output combined .md file path")
    args = parser.parse_args()

    chapters_dir = Path(args.chapters_dir)
    output_path = Path(args.output)

    md_files = sorted(chapters_dir.glob("*.md"))
    if not md_files:
        raise SystemExit(f"No .md files found in {chapters_dir}")

    print(f"Found {len(md_files)} chapter files:")

    combined_parts: list[str] = []
    for md_file in md_files:
        print(f"  {md_file.name}")
        content = md_file.read_text(encoding="utf-8").strip()
        combined_parts.append(content)

    # Separate chapters with a page break (pandoc raw block)
    separator = "\n\n```{=openxml}\n<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>\n```\n\n"
    combined = separator.join(combined_parts)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(combined, encoding="utf-8")

    print(f"\nWrote {len(combined):,} chars → {output_path}")


if __name__ == "__main__":
    main()
