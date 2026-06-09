from __future__ import annotations

import html
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "defense_presentation.pptx"
FIGURES = ROOT / "docs" / "figures"

EMU_PER_INCH = 914400
SLIDE_W = 13.333333
SLIDE_H = 7.5
SW = int(SLIDE_W * EMU_PER_INCH)
SH = int(SLIDE_H * EMU_PER_INCH)

BG = "0B1220"
PANEL = "111827"
PANEL_2 = "172033"
TEXT = "F8FAFC"
MUTED = "CBD5E1"
SUBTLE = "94A3B8"
CYAN = "22D3EE"
GREEN = "34D399"
YELLOW = "FBBF24"
RED = "FB7185"
BLUE = "60A5FA"


def emu(inches: float) -> int:
    return int(inches * EMU_PER_INCH)


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return width, height


@dataclass
class Rel:
    rid: str
    type: str
    target: str


@dataclass
class Slide:
    title: str
    elements: list[str] = field(default_factory=list)
    rels: list[Rel] = field(default_factory=list)
    next_id: int = 2
    next_rel: int = 2

    def shape_id(self) -> int:
        self.next_id += 1
        return self.next_id

    def add_rel(self, rel_type: str, target: str) -> str:
        rid = f"rId{self.next_rel}"
        self.next_rel += 1
        self.rels.append(Rel(rid, rel_type, target))
        return rid


def paragraph(text: str, size: int, color: str = TEXT, bold: bool = False) -> str:
    return (
        "<a:p><a:pPr>"
        f'<a:defRPr sz="{size * 100}" dirty="0">'
        f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        f"<a:latin typeface=\"Aptos\"/><a:cs typeface=\"Aptos\"/>"
        "</a:defRPr></a:pPr>"
        f"<a:r><a:rPr lang=\"ru-RU\" sz=\"{size * 100}\" dirty=\"0\""
        f"{' b=\"1\"' if bold else ''}>"
        f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        f"<a:latin typeface=\"Aptos\"/><a:cs typeface=\"Aptos\"/>"
        f"</a:rPr><a:t>{esc(text)}</a:t></a:r></a:p>"
    )


def add_text(
    slide: Slide,
    x: float,
    y: float,
    w: float,
    h: float,
    lines: list[str],
    size: int = 22,
    color: str = TEXT,
    bold: bool = False,
    name: str = "Text",
) -> None:
    sid = slide.shape_id()
    paras = "".join(paragraph(line, size, color, bold) for line in lines)
    slide.elements.append(
        f"""
        <p:sp>
          <p:nvSpPr><p:cNvPr id="{sid}" name="{esc(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
          <p:spPr>
            <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
            <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
            <a:noFill/><a:ln><a:noFill/></a:ln>
          </p:spPr>
          <p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0"><a:spAutoFit/></a:bodyPr><a:lstStyle/>{paras}</p:txBody>
        </p:sp>
        """
    )


def add_rect(
    slide: Slide,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str = PANEL,
    line: str = CYAN,
    radius: str = "roundRect",
    alpha: int | None = None,
) -> None:
    sid = slide.shape_id()
    alpha_xml = f'<a:alpha val="{alpha}"/>' if alpha is not None else ""
    slide.elements.append(
        f"""
        <p:sp>
          <p:nvSpPr><p:cNvPr id="{sid}" name="Panel"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
          <p:spPr>
            <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
            <a:prstGeom prst="{radius}"><a:avLst/></a:prstGeom>
            <a:solidFill><a:srgbClr val="{fill}">{alpha_xml}</a:srgbClr></a:solidFill>
            <a:ln w="11430"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>
          </p:spPr>
        </p:sp>
        """
    )


def add_title(slide: Slide, title: str, subtitle: str | None = None) -> None:
    add_text(slide, 0.55, 0.32, 11.6, 0.45, [title], size=28, color=TEXT, bold=True, name="Slide title")
    if subtitle:
        add_text(slide, 0.58, 0.78, 11.4, 0.28, [subtitle], size=12, color=SUBTLE, name="Subtitle")
    add_rect(slide, 0.55, 1.03, 2.0, 0.035, fill=CYAN, line=CYAN, radius="rect")


def add_footer(slide: Slide, idx: int) -> None:
    add_text(slide, 0.55, 7.04, 8.0, 0.22, ["AI behavioral authentication + phishing prevention"], size=9, color=SUBTLE)
    add_text(slide, 12.25, 7.04, 0.6, 0.22, [str(idx).zfill(2)], size=9, color=SUBTLE)


def add_bullets(slide: Slide, x: float, y: float, w: float, bullets: list[str], size: int = 18, color: str = MUTED) -> None:
    add_text(slide, x, y, w, 0.34 * len(bullets) + 0.25, [f"• {b}" for b in bullets], size=size, color=color)


def add_kicker(slide: Slide, x: float, y: float, w: float, text: str, color: str = CYAN) -> None:
    add_text(slide, x, y, w, 0.24, [text.upper()], size=10, color=color, bold=True)


def add_metric(slide: Slide, x: float, y: float, w: float, value: str, label: str, color: str = CYAN) -> None:
    add_rect(slide, x, y, w, 1.0, fill=PANEL, line=color)
    add_text(slide, x + 0.18, y + 0.18, w - 0.36, 0.32, [value], size=26, color=color, bold=True)
    add_text(slide, x + 0.18, y + 0.58, w - 0.36, 0.25, [label], size=11, color=MUTED)


def add_image(slide: Slide, path: Path, media_name: str, x: float, y: float, w: float, h: float) -> None:
    sid = slide.shape_id()
    rid = slide.add_rel(
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
        f"../media/{media_name}",
    )
    slide.elements.append(
        f"""
        <p:pic>
          <p:nvPicPr><p:cNvPr id="{sid}" name="{esc(path.name)}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>
          <p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
          <p:spPr>
            <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
            <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
          </p:spPr>
        </p:pic>
        """
    )


def add_image_fit(slide: Slide, path: Path, media_name: str, x: float, y: float, w: float, h: float) -> None:
    iw, ih = png_size(path)
    box_ratio = w / h
    img_ratio = iw / ih
    if img_ratio > box_ratio:
        final_w = w
        final_h = w / img_ratio
        final_x = x
        final_y = y + (h - final_h) / 2
    else:
        final_h = h
        final_w = h * img_ratio
        final_x = x + (w - final_w) / 2
        final_y = y
    add_image(slide, path, media_name, final_x, final_y, final_w, final_h)


def slide_xml(slide: Slide) -> str:
    sp_tree = "\n".join(slide.elements)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="{BG}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {sp_tree}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"""


def rels_xml(rels: list[Rel]) -> str:
    body = "\n".join(
        f'<Relationship Id="{rel.rid}" Type="{rel.type}" Target="{rel.target}"/>'
        for rel in rels
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{body}
</Relationships>
"""


def add_pipeline(slide: Slide, y: float, labels: list[str], colors: list[str]) -> None:
    x = 0.85
    width = 2.25
    gap = 0.28
    for i, label in enumerate(labels):
        add_rect(slide, x, y, width, 0.86, fill=PANEL, line=colors[i])
        add_text(slide, x + 0.16, y + 0.24, width - 0.32, 0.25, [label], size=16, color=TEXT, bold=True)
        if i < len(labels) - 1:
            add_text(slide, x + width + 0.05, y + 0.28, gap, 0.22, ["→"], size=22, color=CYAN, bold=True)
        x += width + gap


def build_slides() -> list[Slide]:
    slides: list[Slide] = []

    s = Slide("Титульный слайд")
    add_rect(s, 0, 0, 13.333, 7.5, fill=BG, line=BG, radius="rect")
    add_text(s, 0.72, 0.65, 11.8, 1.35, ["Использование поведенческого анализа на основе AI", "для аутентификации транзакций и предотвращения phishing-атак"], size=31, color=TEXT, bold=True)
    add_rect(s, 0.76, 2.25, 4.2, 0.04, fill=CYAN, line=CYAN, radius="rect")
    add_text(s, 0.78, 2.55, 6.0, 1.25, ["Магистерская дипломная работа", "Студент: [ФИО]", "Группа: [группа]", "Руководитель: [ФИО, степень]"], size=17, color=MUTED)
    add_text(s, 0.78, 6.42, 8.3, 0.36, ["Moldova State University / Государственный университет Молдовы"], size=13, color=SUBTLE)
    add_text(s, 10.25, 6.42, 2.2, 0.36, ["2027"], size=13, color=SUBTLE)
    slides.append(s)

    s = Slide("Актуальность")
    add_title(s, "Актуальность", "почему транзакции требуют risk-based проверки")
    add_metric(s, 0.75, 1.55, 2.55, "Phishing", "компрометация учётных данных", RED)
    add_metric(s, 3.65, 1.55, 2.55, "MFA ≠ всё", "OTP может быть передан атакующему", YELLOW)
    add_metric(s, 6.55, 1.55, 2.55, "Session risk", "после входа действия не всегда легитимны", BLUE)
    add_metric(s, 9.45, 1.55, 2.55, "Fraud", "несанкционированные транзакции", CYAN)
    add_rect(s, 1.35, 4.15, 10.6, 1.2, fill=PANEL_2, line=CYAN)
    add_text(s, 1.65, 4.48, 10.0, 0.42, ["Ключевая проблема: корректный пароль не доказывает, что критическую операцию выполняет легитимный пользователь"], size=21, color=TEXT, bold=True)
    add_footer(s, 2)
    slides.append(s)

    s = Slide("Цель и задачи")
    add_title(s, "Цель и задачи", "практическая цель и исследовательские шаги")
    add_kicker(s, 0.75, 1.35, 3.5, "Цель")
    add_rect(s, 0.75, 1.65, 5.6, 1.1, fill=PANEL, line=CYAN)
    add_text(s, 1.0, 1.93, 5.1, 0.42, ["Разработать прототип risk-based transaction authentication system"], size=20, color=TEXT, bold=True)
    add_kicker(s, 7.0, 1.35, 3.5, "Задачи")
    add_bullets(s, 7.0, 1.7, 5.3, ["анализ угроз", "выбор признаков", "phishing detection", "behavior collection", "behavioral features", "anomaly detection", "transaction decision", "тестирование"], size=16)
    add_footer(s, 3)
    slides.append(s)

    s = Slide("Исследовательская идея")
    add_title(s, "Исследовательская идея", "не web demo, а полный ML/risk pipeline")
    add_pipeline(s, 2.05, ["Dataset / events", "Features", "ML model", "Risk score", "Decision"], [BLUE, CYAN, GREEN, YELLOW, RED])
    add_bullets(s, 1.15, 4.05, 10.8, ["URL-признаки используются для phishing-классификации", "События браузера агрегируются в behavioral feature vector", "Итоговое решение объединяет два независимых risk-сигнала"], size=20, color=MUTED)
    add_footer(s, 4)
    slides.append(s)

    s = Slide("Архитектура")
    add_title(s, "Общая архитектура системы", "frontend → backend API → ML modules → audit")
    add_rect(s, 0.75, 1.25, 11.85, 5.42, fill="FFFFFF", line=CYAN)
    add_image_fit(s, FIGURES / "end_to_end_flow.png", "image1.png", 0.95, 1.45, 11.45, 5.02)
    add_footer(s, 5)
    slides.append(s)

    s = Slide("Phishing признаки")
    add_title(s, "Phishing detection: признаки", "URLFeatures: несколько групп сигналов")
    add_rect(s, 0.75, 1.25, 7.0, 4.95, fill="FFFFFF", line=CYAN)
    add_image_fit(s, FIGURES / "phishing_feature_groups.png", "image2.png", 0.95, 1.45, 6.6, 4.55)
    add_bullets(s, 8.15, 1.55, 4.3, ["lexical", "SSL / domain", "HTML / JS", "external / reputation"], size=24, color=TEXT)
    add_text(s, 8.15, 4.7, 4.1, 0.72, ["Pipeline устойчив к ошибкам отдельных extractor-ов и использует кэширование признаков"], size=17, color=MUTED)
    add_footer(s, 6)
    slides.append(s)

    s = Slide("XGBoost")
    add_title(s, "Phishing detection: XGBoost model", "feature importance из реального model artifact")
    add_rect(s, 0.75, 1.25, 8.15, 5.2, fill="FFFFFF", line=GREEN)
    add_image_fit(s, FIGURES / "phishing_feature_importance.png", "image3.png", 0.95, 1.45, 7.75, 4.8)
    add_metric(s, 9.35, 1.55, 2.65, "XGBoost", "URL classification", GREEN)
    add_text(s, 9.35, 3.15, 2.8, 1.0, ["Feature importance построен из реального XGBoost model artifact (`feature_importances_`)"], size=16, color=MUTED)
    add_text(s, 9.35, 4.55, 2.8, 0.8, ["Результат: legitimate / suspicious / phishing"], size=17, color=TEXT, bold=True)
    add_footer(s, 7)
    slides.append(s)

    s = Slide("Behavioral признаки")
    add_title(s, "Behavioral analysis: признаки", "keystroke dynamics + mouse dynamics")
    add_rect(s, 0.75, 1.25, 7.0, 4.95, fill="FFFFFF", line=BLUE)
    add_image_fit(s, FIGURES / "behavior_feature_groups.png", "image4.png", 0.95, 1.45, 6.6, 4.55)
    add_bullets(s, 8.15, 1.55, 4.3, ["Session duration", "dwell / flight time", "typing speed", "mouse path length", "clicks / scrolls", "average / max speed"], size=18)
    add_footer(s, 8)
    slides.append(s)

    s = Slide("Behavioral anomaly")
    add_title(s, "Behavioral anomaly detection", "baseline-модель для отклонений от нормального поведения")
    add_pipeline(s, 1.85, ["Browser events", "BehaviorSession", "BehaviorFeatures", "IsolationForest", "Anomaly score"], [BLUE, CYAN, GREEN, YELLOW, RED])
    add_rect(s, 1.1, 4.25, 11.0, 1.25, fill=PANEL_2, line=GREEN)
    add_text(s, 1.4, 4.58, 10.4, 0.5, ["IsolationForest используется как baseline: модель выявляет сессии, статистически отличающиеся от ожидаемого поведения пользователя"], size=20, color=TEXT, bold=True)
    add_footer(s, 9)
    slides.append(s)

    s = Slide("Risk decision")
    add_title(s, "Transaction risk decision", "ALLOW / CHALLENGE / DENY")
    add_rect(s, 0.75, 1.25, 8.35, 5.2, fill="FFFFFF", line=YELLOW)
    add_image_fit(s, FIGURES / "transaction_decision_matrix.png", "image5.png", 0.95, 1.45, 7.95, 4.8)
    add_metric(s, 9.5, 1.45, 2.4, "ALLOW", "низкий риск", GREEN)
    add_metric(s, 9.5, 2.8, 2.4, "CHALLENGE", "доп. проверка", YELLOW)
    add_metric(s, 9.5, 4.15, 2.4, "DENY", "блокировка", RED)
    add_footer(s, 10)
    slides.append(s)

    s = Slide("Прототип")
    add_title(s, "Реализованный прототип", "web-система + ML-инференс + audit")
    add_metric(s, 0.85, 1.4, 2.6, "Backend", "Django, DRF, PostgreSQL", CYAN)
    add_metric(s, 3.75, 1.4, 2.6, "Frontend", "React, TypeScript", BLUE)
    add_metric(s, 6.65, 1.4, 2.6, "ML", "XGBoost, IsolationForest", GREEN)
    add_metric(s, 9.55, 1.4, 2.6, "Audit", "PhishingEvent, RiskAssessment", YELLOW)
    add_rect(s, 1.35, 4.25, 10.6, 1.05, fill=PANEL_2, line=RED)
    add_text(s, 1.65, 4.58, 10.0, 0.34, ["Privacy: raw key values не сохраняются; используются хеши, timing и агрегированные признаки"], size=20, color=TEXT, bold=True)
    add_footer(s, 11)
    slides.append(s)

    s = Slide("Демонстрация")
    add_title(s, "Демонстрация", "место под скриншоты реализованного прототипа")
    demo = [("Dashboard", CYAN), ("Transaction result card", GREEN), ("Django Admin: RiskAssessment", YELLOW)]
    for i, (label, color) in enumerate(demo):
        x = 0.78 + i * 4.18
        add_rect(s, x, 1.55, 3.68, 4.2, fill=PANEL, line=color)
        add_text(s, x + 0.25, 1.88, 3.15, 0.35, [label], size=18, color=TEXT, bold=True)
        add_text(s, x + 0.25, 3.35, 3.15, 0.55, ["screenshot placeholder"], size=16, color=SUBTLE)
    add_footer(s, 12)
    slides.append(s)

    s = Slide("Тестирование")
    add_title(s, "Тестирование и результаты", "проверены основные подсистемы и privacy-требования")
    add_metric(s, 1.0, 1.45, 3.0, "228 passed", "backend test suite", GREEN)
    add_metric(s, 4.45, 1.45, 3.0, "passed", "frontend production build", CYAN)
    add_metric(s, 7.9, 1.45, 3.0, "covered", "pipeline + decision + privacy", BLUE)
    add_bullets(s, 1.25, 3.65, 10.7, ["phishing pipeline", "behavior collection", "feature extraction", "anomaly detector", "transaction decision", "raw key values privacy"], size=20)
    add_footer(s, 13)
    slides.append(s)

    s = Slide("Практическое применение")
    add_title(s, "Практическое применение", "дополнительный risk engine, не замена MFA")
    add_bullets(s, 0.95, 1.45, 5.3, ["digital banking", "fintech", "e-commerce", "corporate systems"], size=24, color=TEXT)
    add_bullets(s, 7.0, 1.45, 5.0, ["денежные переводы", "новый получатель", "крупная сумма", "изменение реквизитов", "доступ к чувствительным данным"], size=20)
    add_rect(s, 1.3, 5.35, 10.7, 0.72, fill=PANEL_2, line=CYAN)
    add_text(s, 1.6, 5.55, 10.1, 0.26, ["Система добавляет адаптивный слой риска поверх существующей аутентификации"], size=18, color=TEXT, bold=True)
    add_footer(s, 14)
    slides.append(s)

    s = Slide("Ограничения")
    add_title(s, "Ограничения и развитие", "что требуется для production-уровня")
    add_bullets(s, 0.95, 1.35, 5.5, ["персональные behavior-модели", "больше пользовательских данных", "model lifecycle и версионирование", "интеграция MFA / OTP"], size=21)
    add_bullets(s, 7.05, 1.35, 5.2, ["защита collector-а", "production monitoring", "настройка порогов риска", "расширение phishing dataset"], size=21)
    add_footer(s, 15)
    slides.append(s)

    s = Slide("Выводы")
    add_title(s, "Выводы", "результат магистерской работы")
    add_rect(s, 1.0, 1.55, 11.25, 1.25, fill=PANEL_2, line=CYAN)
    add_text(s, 1.3, 1.92, 10.65, 0.42, ["Разработан end-to-end прототип, объединяющий phishing AI и behavioral AI для оценки риска транзакций"], size=22, color=TEXT, bold=True)
    add_bullets(s, 1.15, 3.45, 10.8, ["реализован ML pipeline для URL-классификации", "реализован сбор и агрегация поведенческих признаков", "risk decision объяснимо переводит score в ALLOW / CHALLENGE / DENY", "подход применим как дополнительный слой защиты в fintech и banking"], size=20)
    add_footer(s, 16)
    slides.append(s)

    return slides


def content_types_xml(slide_count: int) -> str:
    overrides = "\n".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  {overrides}
</Types>
"""


def presentation_xml(slide_count: int) -> str:
    ids = "\n".join(
        f'<p:sldId id="{255 + i}" r:id="rId{i + 1}"/>'
        for i in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
  <p:sldIdLst>{ids}</p:sldIdLst>
  <p:sldSz cx="{SW}" cy="{SH}" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>
"""


def presentation_rels_xml(slide_count: int) -> str:
    rels = [Rel("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster", "slideMasters/slideMaster1.xml")]
    for i in range(1, slide_count + 1):
        rels.append(Rel(f"rId{i + 1}", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide", f"slides/slide{i}.xml"))
    return rels_xml(rels)


def static_files() -> dict[str, str]:
    return {
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
""",
        "docProps/core.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Использование поведенческого анализа на основе AI для аутентификации транзакций и предотвращения phishing-атак</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
</cp:coreProperties>
""",
        "docProps/app.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex OpenXML generator</Application>
</Properties>
""",
        "ppt/slideLayouts/slideLayout1.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>
""",
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": rels_xml(
            [Rel("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster", "../slideMasters/slideMaster1.xml")]
        ),
        "ppt/slideMasters/slideMaster1.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{BG}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMap bg1="dk1" tx1="lt1" bg2="dk2" tx2="lt2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
  <p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>
</p:sldMaster>
""",
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": rels_xml(
            [
                Rel("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout", "../slideLayouts/slideLayout1.xml"),
                Rel("rId2", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme", "../theme/theme1.xml"),
            ]
        ),
        "ppt/theme/theme1.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Cyber Fintech">
  <a:themeElements>
    <a:clrScheme name="Cyber">
      <a:dk1><a:srgbClr val="0B1220"/></a:dk1><a:lt1><a:srgbClr val="F8FAFC"/></a:lt1>
      <a:dk2><a:srgbClr val="111827"/></a:dk2><a:lt2><a:srgbClr val="CBD5E1"/></a:lt2>
      <a:accent1><a:srgbClr val="22D3EE"/></a:accent1><a:accent2><a:srgbClr val="34D399"/></a:accent2>
      <a:accent3><a:srgbClr val="FBBF24"/></a:accent3><a:accent4><a:srgbClr val="FB7185"/></a:accent4>
      <a:accent5><a:srgbClr val="60A5FA"/></a:accent5><a:accent6><a:srgbClr val="94A3B8"/></a:accent6>
      <a:hlink><a:srgbClr val="22D3EE"/></a:hlink><a:folHlink><a:srgbClr val="60A5FA"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Aptos"><a:majorFont><a:latin typeface="Aptos"/><a:cs typeface="Aptos"/></a:majorFont><a:minorFont><a:latin typeface="Aptos"/><a:cs typeface="Aptos"/></a:minorFont></a:fontScheme>
    <a:fmtScheme name="Default"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
  </a:themeElements>
</a:theme>
""",
    }


def write_pptx(slides: list[Slide]) -> None:
    media_map = {
        "image1.png": FIGURES / "end_to_end_flow.png",
        "image2.png": FIGURES / "phishing_feature_groups.png",
        "image3.png": FIGURES / "phishing_feature_importance.png",
        "image4.png": FIGURES / "behavior_feature_groups.png",
        "image5.png": FIGURES / "transaction_decision_matrix.png",
    }
    for path in media_map.values():
        if not path.exists() or path.stat().st_size == 0:
            raise FileNotFoundError(path)

    tmp = OUT.with_suffix(".tmp")
    if tmp.exists():
        tmp.unlink()
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml(len(slides)))
        for name, content in static_files().items():
            zf.writestr(name, content)
        zf.writestr("ppt/presentation.xml", presentation_xml(len(slides)))
        zf.writestr("ppt/_rels/presentation.xml.rels", presentation_rels_xml(len(slides)))
        for idx, slide in enumerate(slides, start=1):
            slide.rels.insert(0, Rel("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout", "../slideLayouts/slideLayout1.xml"))
            zf.writestr(f"ppt/slides/slide{idx}.xml", slide_xml(slide))
            zf.writestr(f"ppt/slides/_rels/slide{idx}.xml.rels", rels_xml(slide.rels))
        for name, path in media_map.items():
            zf.write(path, f"ppt/media/{name}")
    shutil.move(tmp, OUT)


def main() -> None:
    slides = build_slides()
    write_pptx(slides)
    print(f"Created {OUT.relative_to(ROOT)} with {len(slides)} slides")


if __name__ == "__main__":
    main()
