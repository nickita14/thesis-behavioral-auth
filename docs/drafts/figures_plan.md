# ПЛАН РИСУНКОВ, СХЕМ И СКРИНШОТОВ ДЛЯ ДИПЛОМНОЙ РАБОТЫ

## Глава 1. Теоретическая часть

Рис. 1.1. Общая схема phishing-атаки
Назначение: показать путь пользователя от phishing-ссылки до передачи учётных данных злоумышленнику.
Где использовать: раздел 1.2.

Рис. 1.2. Сравнение классической и непрерывной аутентификации
Назначение: показать разницу между проверкой только при входе и анализом поведения во время всей сессии.
Где использовать: раздел 1.3 или 1.4.

Рис. 1.3. Примеры поведенческих признаков пользователя
Назначение: показать keystroke dynamics, mouse dynamics и transaction behavior.
Где использовать: раздел 1.4.

## Глава 2. Проектирование системы

Рис. 2.1. Высокоуровневая архитектура системы
Компоненты:
- Frontend
- Behavior Collector
- Django REST API
- Behavior Storage
- Phishing Detection Pipeline
- ML Engine
- Transaction Risk Engine
- PostgreSQL
- Dashboard/Admin

Где использовать: раздел 2.2.

Рис. 2.2. Поток обработки транзакции
Шаги:
1. Пользователь заполняет форму транзакции
2. Frontend отправляет transaction request
3. Backend проверяет пользователя
4. Извлекаются behavior features
5. Выполняется behavior anomaly detection
6. Выполняется phishing URL check
7. Создаётся TransactionAttempt
8. Создаётся RiskAssessment
9. Возвращается ALLOW / CHALLENGE / DENY

Где использовать: раздел 2.2 и 2.7.

Рис. 2.3. ER-диаграмма основных сущностей
Сущности:
- User
- BehaviorSession
- KeystrokeEvent
- MouseEvent
- PhishingEvent
- TransactionAttempt
- RiskAssessment

Где использовать: раздел 2.3.

Рис. 2.4. Архитектура phishing detection pipeline
Компоненты:
- URL input
- LexicalExtractor
- SSLExtractor
- WhoisExtractor
- HTMLExtractor
- ExternalExtractor
- URLFeatures
- FeatureCache
- XGBoostPhishingDetector
- PhishingEvent audit

Где использовать: раздел 2.5.

Рис. 2.5. Архитектура behavioral AI pipeline
Компоненты:
- BehaviorSession
- KeystrokeEvent
- MouseEvent
- BehaviorFeatureExtractor
- BehaviorFeatures
- IsolationForest BehaviorAnomalyDetector
- BehaviorAnomalyResult

Где использовать: раздел 2.6.

Рис. 2.6. Матрица принятия решения по транзакции
Показать правила:
- phishing → DENY
- suspicious URL → CHALLENGE
- phishing error → CHALLENGE
- anomalous behavior → CHALLENGE
- suspicious behavior + high amount → CHALLENGE
- otherwise → ALLOW

Где использовать: раздел 2.7.

Рис. 2.7. Схема практического внедрения risk engine
Компоненты:
- Existing banking/e-commerce frontend
- Risk Engine
- Core Transaction Backend
- MFA/OTP Service
- Audit/Monitoring

Где использовать: раздел 2.10.

## Глава 3. Реализация

Рис. 3.1. Структура backend-приложения в проекте
Скриншот дерева:
- apps/behavior
- apps/phishing
- apps/ml_engine
- apps/transactions

Рис. 3.2. Страница входа в систему
Скриншот frontend login page.

Рис. 3.3. Dashboard с поведенческими событиями
Скриншот dashboard после логина.

Рис. 3.4. Форма создания транзакции
Скриншот transaction page.

Рис. 3.5. Результат анализа транзакции
Скриншот result card с final decision, phishing block, behavior block, reasons.

Рис. 3.6. Django Admin: BehaviorSession
Скриншот админки с привязкой сессии к пользователю.

Рис. 3.7. Django Admin: RiskAssessment
Скриншот risk assessment с behavior_score, phishing_score, model_versions/reasons.

Рис. 3.8. Пример ответа API /api/phishing/check/
Скриншот curl/Postman/браузера с JSON-ответом.

Рис. 3.9. Пример ответа API /api/transactions/attempts/
Скриншот JSON-ответа с ALLOW/CHALLENGE/DENY.

## Глава 4. Тестирование и результаты

Рис. 4.1. Результат запуска backend-тестов
Скриншот terminal: 228 passed.

Рис. 4.2. Результат сборки frontend
Скриншот terminal: npm run build passed.

Рис. 4.3. Сценарий ALLOW
Скриншот транзакции с легитимным URL и нормальным behavior result.

Рис. 4.4. Сценарий CHALLENGE
Скриншот транзакции с suspicious behavior или suspicious URL.

Рис. 4.5. Сценарий DENY
Скриншот транзакции с phishing decision.

## Для презентации

Минимальный набор слайдов:
1. Проблема: phishing + stolen credentials
2. Почему password/MFA недостаточно
3. Идея решения: phishing AI + behavioral AI
4. Архитектура системы
5. Поведенческий collector
6. Phishing detection pipeline
7. Transaction risk decision
8. Демонстрация dashboard
9. Демонстрация transaction result
10. Тестирование
11. Практическое применение
12. Ограничения и развитие
13. Выводы