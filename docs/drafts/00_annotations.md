# ADNOTARE

Tema lucrarii este „Utilizarea analizei comportamentale bazate pe AI pentru autentificarea tranzactiilor si prevenirea atacurilor de phishing”. Lucrarea include introducere, patru capitole, concluzii, bibliografie si anexe.

Cuvinte-cheie: analiza comportamentala, inteligenta artificiala, autentificarea tranzactiilor, phishing, biometrie comportamentala, keystroke dynamics, mouse dynamics, detectarea anomaliilor, XGBoost, Isolation Forest, securitate cibernetica.

Actualitatea cercetarii este determinata de cresterea numarului de atacuri de tip phishing si de limitarile metodelor clasice de autentificare in sistemele digitale. Parolele si verificarile statice nu sunt suficiente pentru a confirma in mod continuu ca operatia este efectuata de utilizatorul legitim, mai ales in scenarii de tranzactii online.

Scopul lucrarii consta in proiectarea si implementarea unui prototip de sistem care combina detectarea phishing-ului cu analiza comportamentala pentru evaluarea riscului unei tranzactii. Pentru atingerea acestui scop au fost stabilite urmatoarele sarcini: analiza domeniului, proiectarea arhitecturii, colectarea evenimentelor comportamentale, extragerea caracteristicilor, integrarea modelelor ML, implementarea API-urilor si testarea sistemului.

Rezultatele obtinute includ un backend functional pentru detectarea URL-urilor phishing, colectarea evenimentelor de tastatura si mouse, extragerea caracteristicilor comportamentale, detectarea anomaliilor cu Isolation Forest si formarea unei decizii finale pentru tranzactie. A fost implementata si o interfata frontend demonstrativa pentru autentificare, dashboard si initierea tranzactiilor.

Semnificatia practica a lucrarii consta in demonstrarea unui mecanism suplimentar de securitate pentru sisteme de banking digital, e-commerce si servicii fintech. Sistemul nu inlocuieste parola sau MFA, ci adauga un nivel de analiza a comportamentului utilizatorului si a riscului URL-ului asociat tranzactiei.

# АННОТАЦИЯ

Тема работы: «Использование поведенческого анализа на основе AI для аутентификации транзакций и предотвращения phishing-атак». Работа включает введение, четыре главы, заключение, библиографию и приложения.

Ключевые слова: поведенческий анализ, искусственный интеллект, аутентификация транзакций, phishing, поведенческая биометрия, keystroke dynamics, mouse dynamics, обнаружение аномалий, XGBoost, Isolation Forest, кибербезопасность.

Актуальность исследования обусловлена ростом phishing-атак и ограничениями классических методов аутентификации в цифровых системах. Пароли и статические проверки не позволяют непрерывно подтверждать, что транзакцию выполняет легитимный пользователь, особенно в условиях онлайн-банкинга и удалённых финансовых операций.

Цель работы заключается в проектировании и реализации прототипа системы, которая объединяет обнаружение phishing-риска и поведенческий анализ пользователя для принятия решения по транзакции. Для достижения цели были поставлены задачи анализа предметной области, проектирования архитектуры, реализации сбора поведенческих событий, извлечения признаков, интеграции ML-модулей, разработки API и проверки системы тестами.

Полученные результаты включают backend-модуль phishing detection, подсистему сбора событий клавиатуры и мыши, модуль извлечения поведенческих признаков, baseline detector аномалий на основе Isolation Forest и механизм итогового решения по транзакции. Также реализован frontend-демо flow: вход пользователя, dashboard и страница создания транзакции.

Практическая значимость работы состоит в демонстрации дополнительного слоя защиты для цифрового банкинга, e-commerce и fintech-сервисов. Разработанная система не заменяет пароль или MFA, а дополняет их анализом поведения пользователя и проверкой риска URL, связанного с операцией.

# ANNOTATION

The thesis topic is "Using AI-based behavioral analysis for transaction authentication and phishing attack prevention". The thesis includes an introduction, four chapters, conclusions, bibliography and appendices.

Keywords: behavioral analysis, artificial intelligence, transaction authentication, phishing, behavioral biometrics, keystroke dynamics, mouse dynamics, anomaly detection, XGBoost, Isolation Forest, cybersecurity.

The relevance of the research is determined by the increasing number of phishing attacks and the limitations of classical authentication methods in digital systems. Passwords and static checks are not sufficient to continuously confirm that a transaction is being performed by a legitimate user, especially in online banking and remote financial operations.

The aim of the thesis is to design and implement a prototype system that combines phishing risk detection with user behavioral analysis for transaction decision-making. The main tasks include domain analysis, architecture design, behavioral event collection, feature extraction, ML module integration, API implementation and system testing.

The achieved results include a backend phishing detection module, keystroke and mouse event collection, behavioral feature extraction, a baseline anomaly detector based on Isolation Forest, and final transaction risk decision logic. A demonstration frontend flow was also implemented, including login, dashboard and transaction creation pages.

The practical significance of the thesis is the demonstration of an additional security layer for digital banking, e-commerce and fintech services. The system does not replace passwords or MFA, but complements them with user behavior analysis and URL risk verification related to the transaction.
