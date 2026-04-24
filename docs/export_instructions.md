# DOCX export instructions

`pandoc` is not required by the application runtime, but it is the simplest way
to export the assembled thesis draft from Markdown to Word.

## Install Pandoc in WSL

```bash
sudo apt update
sudo apt install pandoc -y
```

## Source file

```text
docs/drafts/full_thesis_draft.md
```

## Output file

```text
docs/thesis_draft.docx
```

## Basic export

Run from the repository root:

```bash
pandoc docs/drafts/full_thesis_draft.md \
  --from markdown \
  --to docx \
  --output docs/thesis_draft.docx
```

## Export with a Word reference template

If a university-formatted Word template is available, save it as
`docs/reference.docx` and run:

```bash
pandoc docs/drafts/full_thesis_draft.md \
  --from markdown \
  --to docx \
  --reference-doc docs/reference.docx \
  --output docs/thesis_draft.docx
```

`docs/reference.docx` is created manually in Word or LibreOffice, or generated
with the helper script:

```bash
python docs/tools/create_reference_docx.py
```

The script uses Pandoc's default `reference.docx` and patches Word styles using
Python standard library XML/ZIP tools, so it does not require `python-docx`.

The reference document should contain the styles used by Pandoc during export:

- `Normal`
- `Heading 1`
- `Heading 2`
- `Table`
- `Caption`

See `docs/reference_style_guide.md` for the target formatting rules.

## Manual check after export

1. Open `docs/thesis_draft.docx` in Word or LibreOffice.
2. Verify that the table of contents text appears at the beginning.
3. Verify that headings for introduction, chapters I-IV, conclusion, and bibliography are converted as headings.
4. Check Markdown tables, especially decision matrices, for correct column layout.
5. Confirm that the bibliography section is at the end of the document.
6. Apply final university formatting in Word: page numbers, generated table of contents, captions, margins, and bibliography style.

## Manual fallback without pandoc

If `pandoc` is not available, open `docs/drafts/full_thesis_draft.md`, copy the
content into Word, and apply heading styles manually. Insert figures and
screenshots from `docs/figures/` and `docs/screenshots/` after the text layout is
stable.
