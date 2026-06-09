# ADNOTARE

**MIRONOV NICHITA.** Utilizarea analizei comportamentale AI pentru autentificarea tranzacțiilor și prevenirea atacurilor phishing. Teză de master. Chișinău, 2026.

Lucrarea include introducere, 4 capitole, concluzie, bibliografie din 19 surse. Volumul total: 89 pagini de text de bază, 5 figuri, 9 tabele.

**Cuvinte-cheie:** biometrie comportamentală, autentificare a tranzacțiilor, detectare atacuri phishing, învățare automată, Isolation Forest, XGBoost, autentificare bazată pe risc, dinamica apăsărilor de taste.

**Scopul și obiectivele lucrării.** Elaborarea unui prototip web al sistemului de autentificare a tranzacțiilor bazat pe risc, care combină clasificarea ML a URL-urilor cu analiza comportamentală a utilizatorului pentru a forma un verdict explicabil (ALLOW / CHALLENGE / DENY). Obiectivele: arhitectură modulară SOLID; pipeline comportamental cu 16 trăsături; detector phishing XGBoost cu 30 trăsături; RiskDecisionEngine; validare pe benchmark standardizat; testare de acceptare.

**Metodologia cercetării.** Stivă: Django 5.1, Django REST Framework, PostgreSQL, React 19, TypeScript, Vite. Analiza comportamentală — Isolation Forest (one-class anomaly detection), 16 trăsături per-repetare, segmentare prin Tukey's fence. Detectarea phishing — XGBoost, 30 trăsături lexicale și host-based ale URL. Validare cross-utilizator pe CMU Keystroke Dynamics Benchmark [KILLOURHY & MAXION 2009] prin LOSO. Modelele serializate cu joblib.

**Noutatea științifică și originalitatea.** Arhitectură hibridă bazată pe risc în care detectarea phishing-ului și biometria comportamentală sunt semnale complementare în motorul de decizie unificat. Mecanism challenge-typing pentru alinierea domeniului de antrenare și inferență. Validare reproductibilă pe benchmark standardizat cu documentarea cazurilor limită.

**Problema rezolvată.** Metodele clasice de autentificare confirmă cunoașterea unui secret sau posesia unui dispozitiv, dar nu garantează că operatorul curent este proprietarul legitim. Lucrarea abordează această problemă printr-o evaluare continuă a riscului care combină profilul comportamental al utilizatorului cu contextul operației.

**Semnificația teoretică.** Sistematizarea abordărilor biometriei comportamentale, detectării phishing și autentificării adaptive într-un model unificat de evaluare a riscului. Rezultate de validare: EER 14,4% și AUC ROC 0,916 pe CMU Benchmark [KILLOURHY & MAXION 2009]; acuratețe phishing 97,24% pe UCI Phishing Websites Dataset [MOHAMMAD et al. 2014].

**Valoarea aplicativă.** 277 de teste automate acoperind toate endpoint-urile API publice, interfețele ML și logica de decizie. Prototipul funcțional poate servi drept bază pentru cercetări în biometria comportamentală și adaptarea la sisteme bancare reale, e-commerce și fintech.
