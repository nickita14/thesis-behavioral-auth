#!/usr/bin/env bash
set -euo pipefail

# Build thesis.docx from markdown chapters
# Usage: bash docs/thesis/scripts/build.sh

THESIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHAPTERS_DIR="$THESIS_DIR/chapters"
OUTPUT_DIR="$THESIS_DIR/output"
REFERENCE_DOCX="$THESIS_DIR/reference_examples/reference_template.docx"
METADATA="$THESIS_DIR/metadata.yaml"

mkdir -p "$OUTPUT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Thesis build pipeline"
echo "  thesis dir: $THESIS_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Step 1: Concatenate all chapter md files in order
echo ""
echo "→ [1/3] Concatenating chapters..."
python3 "$THESIS_DIR/scripts/concat_chapters.py" \
    --chapters-dir "$CHAPTERS_DIR" \
    --output "$OUTPUT_DIR/thesis_combined.md"

# Step 2: Run pandoc
echo ""
echo "→ [2/3] Running pandoc..."

PANDOC_ARGS=(
    "$OUTPUT_DIR/thesis_combined.md"
    --from "markdown+raw_attribute"
    --to docx
    --output "$OUTPUT_DIR/thesis_raw.docx"
    --resource-path="$THESIS_DIR:$CHAPTERS_DIR"
)

if [ -f "$REFERENCE_DOCX" ]; then
    PANDOC_ARGS+=(--reference-doc "$REFERENCE_DOCX")
    echo "  Using reference template: $(basename "$REFERENCE_DOCX")"
else
    echo "  ⚠ No reference template found — using pandoc defaults"
    echo "    To add one: python3 $THESIS_DIR/scripts/extract_reference_template.py --source /path/to/Erica_thesis.docx"
fi

pandoc "${PANDOC_ARGS[@]}"
echo "  pandoc OK → $(du -h "$OUTPUT_DIR/thesis_raw.docx" | cut -f1) thesis_raw.docx"

# Step 3: Python postprocessing
echo ""
echo "→ [3/3] Postprocessing..."
python3 "$THESIS_DIR/scripts/postprocess.py" \
    --input "$OUTPUT_DIR/thesis_raw.docx" \
    --output "$OUTPUT_DIR/thesis.docx" \
    --metadata "$METADATA"

FINAL_SIZE="$(du -h "$OUTPUT_DIR/thesis.docx" | cut -f1)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Done: $OUTPUT_DIR/thesis.docx  ($FINAL_SIZE)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
