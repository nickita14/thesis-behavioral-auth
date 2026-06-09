# Ограничения системы — обнаруженные в acceptance testing

## Ограничение 1: Hunt-and-peck typists out of distribution

### Эмпирические данные
Acceptance check 19.05.2026 с третьим пользователем (guest1) выявил:

| Метрика | Validation set (3 typists) | Guest1 | Различие |
|---------|----------------------------|--------|----------|
| Median inter-keyup gap | 200-600ms | 4887ms | 8-24× |
| Max gap | ~1500ms | 16773ms | 11× |
| Gaps > 5000ms | 0% | 46% | — |
| Repetitions detected | 5/5 | 2-4/10 | — |

### Анализ корневой причины
Adaptive boundary detection (Tukey's fence: `median + 3*IQR`)
у guest1 даёт threshold ~13000-16000ms, потому что внутри одной
репетиции gaps уже превышают 5 секунд. Inter-character gap и
inter-repetition gap становятся неотличимы.

### Известность в литературе
CMU Keystroke Dynamics dataset (Killourhy & Maxion 2009) и
большинство production-систем исключают такие паттерны по дизайну:
hunt-and-peck typists сложны для **любой** keystroke dynamics
системы, не только нашей.

### Решение в production
Для пользователей с inter-character > 2000ms:
1. Использовать mouse dynamics features (уже есть в feature vector,
   не приоритизированы)
2. Альтернативные методы (graphic password, hardware token)
3. Специализированная модель для slow typists с другой phrase
   structure (более длинные фразы)

### Для текущей работы
Эта категория пользователей исключена из in-distribution валидации.
Описана как known limitation в Главе 4 диссертации.
