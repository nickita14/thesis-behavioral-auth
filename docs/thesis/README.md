# Thesis Build Pipeline

## Quick start

```bash
bash docs/thesis/scripts/build.sh
# → docs/thesis/output/thesis.docx
```

## Однократная подготовка

### 1. Reference template (когда получите docx от Erici)

```bash
python3 docs/thesis/scripts/extract_reference_template.py \
    --source /path/to/Erica_thesis.docx
```

Это скопирует файл в `reference_examples/reference_template.docx`.
После этого pandoc будет использовать стили из него.

### 2. Заполнить metadata.yaml

Откройте `docs/thesis/metadata.yaml` и заполните:
- `author_ru` / `author_ro` — ваше имя
- `group` — номер группы

### 3. Зависимости Python

```bash
pip install python-docx pyyaml
```

## Структура

```
docs/thesis/
├── chapters/          # Главы в порядке 00_, 01_, 02_, ...
├── figures/           # PNG для вставки в главы
├── metadata.yaml      # Автор, тема, supervisor
├── reference_examples/reference_template.docx  (добавить вручную)
├── output/
│   ├── thesis_combined.md   # промежуточный
│   ├── thesis_raw.docx      # pandoc output до постобработки
│   └── thesis.docx          # финальный артефакт
└── scripts/
    ├── build.sh                      # главная команда
    ├── concat_chapters.py            # склейка глав
    ├── postprocess.py                # docx-правки (Sprint 3.1+)
    └── extract_reference_template.py # однократно: копирует reference docx
```

## Вставка figures в главы

Из файла в `chapters/`, ссылка на figure:

```markdown
![Рисунок 4.1. ROC curves](../figures/fig02_roc_curves.png)
```

## PDF preview (для проверки)

```bash
libreoffice --headless --convert-to pdf \
    --outdir docs/thesis/output/ \
    docs/thesis/output/thesis.docx
```
