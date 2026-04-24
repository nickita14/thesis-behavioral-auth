from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "reference.docx"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
ET.register_namespace("w", W_NS)
BLACK_TEXT_STYLES = (
    "Title",
    "Subtitle",
    "Heading1",
    "Heading2",
    "Heading3",
    "Heading4",
    "Heading5",
    "Heading6",
    "Heading7",
    "Heading8",
    "Heading9",
    "Caption",
    "TableCaption",
)


def w_tag(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def find_or_create(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(f"w:{tag}", NS)
    if child is None:
        child = ET.SubElement(parent, w_tag(tag))
    return child


def remove_children(parent: ET.Element, tag: str) -> None:
    for child in list(parent.findall(f"w:{tag}", NS)):
        parent.remove(child)


def set_bool(parent: ET.Element, tag: str) -> None:
    remove_children(parent, tag)
    ET.SubElement(parent, w_tag(tag))


def set_fonts(rpr: ET.Element, size_half_points: int, *, bold: bool = False) -> None:
    fonts = find_or_create(rpr, "rFonts")
    for attr in ("ascii", "hAnsi", "cs", "eastAsia"):
        fonts.set(w_tag(attr), "Times New Roman")

    sz = find_or_create(rpr, "sz")
    sz.set(w_tag("val"), str(size_half_points))

    sz_cs = find_or_create(rpr, "szCs")
    sz_cs.set(w_tag("val"), str(size_half_points))

    if bold:
        set_bool(rpr, "b")
        set_bool(rpr, "bCs")
    else:
        remove_children(rpr, "b")
        remove_children(rpr, "bCs")


def set_black_color(rpr: ET.Element) -> None:
    color = find_or_create(rpr, "color")
    for attr in ("themeColor", "themeTint", "themeShade"):
        color.attrib.pop(w_tag(attr), None)
    color.set(w_tag("val"), "000000")


def set_paragraph(
    ppr: ET.Element,
    *,
    alignment: str,
    before: int,
    after: int,
    line: int | None,
    first_line_twips: int,
) -> None:
    jc = find_or_create(ppr, "jc")
    jc.set(w_tag("val"), alignment)

    spacing = find_or_create(ppr, "spacing")
    spacing.set(w_tag("before"), str(before))
    spacing.set(w_tag("after"), str(after))
    if line is None:
        spacing.attrib.pop(w_tag("line"), None)
        spacing.attrib.pop(w_tag("lineRule"), None)
    else:
        spacing.set(w_tag("line"), str(line))
        spacing.set(w_tag("lineRule"), "auto")

    ind = find_or_create(ppr, "ind")
    ind.set(w_tag("firstLine"), str(first_line_twips))


def get_style(root: ET.Element, style_id: str) -> ET.Element | None:
    return root.find(f".//w:style[@w:styleId='{style_id}']", NS)


def patch_style(
    root: ET.Element,
    style_id: str,
    *,
    size_half_points: int,
    bold: bool,
    alignment: str,
    before: int,
    after: int,
    line: int | None,
    first_line_twips: int,
) -> None:
    style = get_style(root, style_id)
    if style is None:
        return

    ppr = find_or_create(style, "pPr")
    rpr = find_or_create(style, "rPr")
    set_paragraph(
        ppr,
        alignment=alignment,
        before=before,
        after=after,
        line=line,
        first_line_twips=first_line_twips,
    )
    set_fonts(rpr, size_half_points, bold=bold)
    set_black_color(rpr)


def force_style_black(root: ET.Element, style_id: str) -> None:
    style = get_style(root, style_id)
    if style is None:
        return
    rpr = find_or_create(style, "rPr")
    set_black_color(rpr)


def patch_styles_xml(styles_xml: bytes) -> bytes:
    root = ET.fromstring(styles_xml)

    patch_style(
        root,
        "Normal",
        size_half_points=28,
        bold=False,
        alignment="both",
        before=0,
        after=0,
        line=360,
        first_line_twips=709,
    )
    patch_style(
        root,
        "Heading1",
        size_half_points=32,
        bold=True,
        alignment="center",
        before=240,
        after=240,
        line=None,
        first_line_twips=0,
    )
    patch_style(
        root,
        "Heading2",
        size_half_points=28,
        bold=True,
        alignment="center",
        before=120,
        after=120,
        line=None,
        first_line_twips=0,
    )
    patch_style(
        root,
        "Caption",
        size_half_points=24,
        bold=False,
        alignment="center",
        before=0,
        after=0,
        line=None,
        first_line_twips=0,
    )

    for table_style_id in ("Table", "TableNormal"):
        patch_style(
            root,
            table_style_id,
            size_half_points=24,
            bold=False,
            alignment="left",
            before=0,
            after=0,
            line=240,
            first_line_twips=0,
        )

    for style_id in BLACK_TEXT_STYLES:
        force_style_black(root, style_id)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def create_reference_docx() -> None:
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        raise RuntimeError("pandoc is required to generate the base reference.docx")

    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        base_docx = temp_dir / "reference-base.docx"
        patched_docx = temp_dir / "reference.docx"

        with base_docx.open("wb") as output:
            subprocess.run(
                [pandoc, "--print-default-data-file", "reference.docx"],
                check=True,
                stdout=output,
            )

        with zipfile.ZipFile(base_docx, "r") as zin, zipfile.ZipFile(
            patched_docx, "w", zipfile.ZIP_DEFLATED
        ) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/styles.xml":
                    data = patch_styles_xml(data)
                zout.writestr(item, data)

        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(patched_docx, OUTPUT)


if __name__ == "__main__":
    create_reference_docx()
    print(f"created {OUTPUT.relative_to(ROOT)}")
