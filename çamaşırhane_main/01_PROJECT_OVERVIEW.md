# LaundroStar — Proje Özeti

> Bu doküman platformun ne olduğunu, kime hizmet ettiğini, neyin v4'te olduğunu, neyin olmadığını ve başarıyı nasıl ölçtüğümüzü tanımlar. Diğer on dokümanın tamamı bu dokümanın okunmuş olduğunu varsayar.

---

## Proje Tanıtımı

LaundroStar, fabrikalardaki ve tesislerdeki çamaşırhane operasyonlarını dijitalleştiren bir RFID tabanlı otomasyon ve takip sistemidir. Personele zimmetlenen üniformalar ve iş kıyafetleri; **Kirli Giriş → Yıkama Onayı → Personele Teslim** döngüsü boyunca gerçek zamanlı olarak izlenir.

Ürün, **tek bir tesis için** geliştirilen dahili bir iç kurumsal uygulamadır; multi-tenant SaaS değildir. Sistemin ayırt edici değer önerisi şunlardır: RFID etiket ile kıyafet-personel bağlantısı, cinsiyete göre otomatik raf atama, anlık doluluk haritası ve tüm işlemlerin izlenebilir denetim kaydı.

MVP bir web uygulaması olarak teslim edilmiştir; mobil uygulama bu faz kapsamında değildir. Ödeme ve abonelik sistemi kapsam dışıdır.

---

## Hedef Kullanıcılar

**Admin (Çamaşırhane Yöneticisi).** Sistemin tüm yetkilerine sahip, sınırlı sayıda kullanıcı. Kullanıcı yönetimi, RFID eşleştirme, tüm tablo ve kayıtlara erişim, audit log görüntüleme, istatistik takibi bu rolde toplanır.

**User (Görevli / Operatör).** Günlük çamaşırhane operasyonlarını yürüten personel. Kirli giriş yapabilir, yıkama tamamlandığında kıyafeti "Temiz" olarak onaylayabilir, temiz kıyafeti personele teslim edebilir. Audit log ve kullanıcı yönetimine erişimi yoktur.

---

## Kapsam

### v4 Kapsamı (in-scope)

- **Kimlik doğrulama ve oturum yönetimi** — email + şifre login; JWT access token (15 dk, RS256) + refresh token (7 gün, rotation); httpOnly cookie; CSRF double-submit; hesap kilitleme (5 başarısız → 15 dk kilit); şifre sıfırlama. Admin (ve isteğe bağlı tüm) hesaplar için TOTP tabanlı MFA ikinci faktörü uygulanmıştır (ADR 0007).
- **Kullanıcı yönetimi** — Admin tarafından kullanıcı CRUD; profil güncelleme (email, telefon, unvan, şirket). Profil avatarı kullanıcının ad/soyad baş harfleriyle gösterilir (fotoğraf yükleme özelliği kaldırıldı).
- **Çalışan (Calisan) yönetimi** — Sicil numarası bazlı personel kaydı; ad, soyad, cinsiyet attribute'ları.
- **RFID eşleştirme** — RFID tag → sicil numarası eşleştirme CRUD; yeni personel kaydı ile eş zamanlı eşleştirme; çakışma kontrolü.
- **Kirli kıyafet girişi** — RFID okutarak veya sepet simülasyonu (rastgele 10 kıyafet) ile kirli giriş; `kirli_kiyafetler` tablosuna kayıt. **Yalnızca admin** yetkisiyle yapılır (test/operasyon amaçlı, admin'e özel "Test Ekranları" menüsünden açılır).
- **Yıkama onayı** — Kirli bekleyenler listesinden tek tıkla onaylama; otomatik raf atama (cinsiyet bazlı); `temiz_kiyafetler` tablosuna aktarım.
- **Teslim** — Temiz listesinden sicil doğrulayarak teslim; `teslim_edilenler` tablosuna kayıt.
- **Raf yönetimi** — 8 raf (A-H) × 7 kat × 5 bölme = 280 göz; cinsiyete göre raf atama (K→E, E→A,B,C,D,F,G,H); 2D interaktif doluluk haritası; raf detay drill-down.
- **İstatistik ve dashboard** — Bugünkü kirli/temiz/teslim sayıları; 7 ve 30 günlük geçmiş grafik.
- **Tablo ve arama** — Kirli, temiz, teslim, kıyafet listelerinde metin araması ve sayfalama.
- **Audit log** — Admin'e özel; tüm kritik işlemlerin kullanıcı adı, IP hash, zaman damgası ile kayıt altına alınması; filtreleme (kullanıcı, aksiyon).
- **Güvenlik altyapısı** — OWASP ASVS Level 1 hedef; security header'ları (CSP, X-Frame-Options, HSTS, Referrer-Policy); rate limiting kritik endpointlerde; structured JSON logging; bcrypt (cost 12) + minimum 12 karakter şifre politikası.
- **Veritabanı migrations** — Alembic tabanlı, auto-create yerine versiyonlanmış migration geçmişi.
- **Docker altyapısı** — Multi-stage build; non-root kullanıcı; pinned image; .dockerignore; Nginx TLS reverse proxy.

### Kapsam Dışı (v5+ veya reddedilen)

- **Mobil uygulama** — Teknoloji seçimi mobile genişlemeye izin verir; v4'te yalnızca web.
- **Gerçek RFID donanım entegrasyonu** — v4'te RFID okuma simülasyon bazlı (rastgele seçim); gerçek tünel okuyucu entegrasyonu v5 planında.
- **SAP / ERP / İK entegrasyonu** — Personel bilgileri manuel girilir; API tabanlı senkronizasyon kapsam dışı.
- **MFA operasyonel devreye alma / SSO** — TOTP MFA backend'i uygulanmıştır (ADR 0007, bkz. in-scope); kalan operasyonel adımlar (kayıt UI, `ADMIN_MFA_REQUIRED` zorunlu kılma, MFA reset ucu) ve opsiyonel Keycloak/SSO entegrasyonu Faz 10'a bırakılmıştır.
- **Email bildirim sistemi** — Yıkama tamamlandığında SMS/email bildirimi kapsam dışı.
- **Rapor export (PDF/Excel)** — Dashboard verileri görsel olarak sunulur; export v5'te.
- **Kıyafet versiyonlama** — Aynı RFID tag'in eşleşmesi değişirse tarihçe tutulmaz; v4'te yalnızca son durum.
- **Doküman yönetimi** — Hiçbir dosya/belge eki veya yükleme yüzeyi yoktur.
- **Multi-tenant** — Tek tesis, tek veritabanı; çok kiracılı yapı reddedildi.
- **Çoklu dil** — v4 yalnızca Türkçe.
- **Public API** — Dışarıya açık API yok; tüm endpointler kimlik doğrulama gerektirir.

---

## Ölçek ve Kısıtlar

- **Toplam personel (Calisan):** ~500–2.000
- **Toplam RFID kayıt:** ~1.000–5.000
- **Günlük işlem:** ~100–500 (kirli giriş + onay + teslim)
- **Eşzamanlı kullanıcı:** < 20
- **Raf kapasitesi:** 280 göz (8 × 7 × 5; 7. kat gözleri kapasitesi 1, diğerleri 3)
- **Coğrafya:** Türkiye, tek tesis
- **Uyumluluk:** KVKK (IP adresi ve kişisel veri maskeleme); OWASP Top 10 referans
- **Uptime SLA:** %99 (iş saatleri bazlı)
- **Dil:** Yalnızca Türkçe

---

## Başarı Kriterleri

| Kriter | Hedef | Ölçüm yöntemi |
|--------|-------|----------------|
| API p95 latency | < 500 ms | Uvicorn/Nginx access log |
| Uptime | %99 | Docker health check + restart policy |
| Auth modülü test coverage | Line %85+ | pytest-cov raporu |
| Güvenlik modülü test coverage | Line %90+ | pytest-cov raporu |
| Proje genel coverage | Line %80+ (CI gate `--cov-fail-under=80`; ölçülen %85) | pytest-cov raporu |
| Dependency güvenlik açığı (high/critical) | 0 (build fail) | `pip-audit` CI adımı |
| Docker non-root user | Zorunlu | Dockerfile denetimi |
| JWT localStorage kullanımı | 0 | Manuel kod denetimi |
| Audit log kaydı başarı oranı | %100 | Entegrasyon testi |

---

## Kısıtlamalar (Teknik ve Organizasyonel)

- **Geliştirme modeli:** Solo developer + AI-assisted (vibe coding). Cursor / Claude Code agent ile kod üretimi; developer test onayı olmadan merge yasak.
- **Backend runtime:** Python 3.11 + FastAPI + Uvicorn. Node.js veya JVM tabanlı geçiş bu versiyon kapsamında değil.
- **Frontend:** Mevcut Vanilla JS + HTML + Tailwind CSS korunur (v4 kapsamı). React / Next.js migrasyonu v5 planında değerlendirilecek. Bkz. [[10_DEV_WORKFLOW#ADR-001]].
- **Veritabanı:** PostgreSQL 16. Cloud managed service (AWS RDS / Aurora) v5'te değerlendirilir; v4 Docker Compose içinde local PostgreSQL.
- **Deployment platformu:** Docker Compose + Nginx. Kubernetes / ECS geçişi v5+ için operasyonel karar olarak ayrılmıştır.
- **Email altyapısı:** v4'te email bildirimi yok; şifre sıfırlama akışı v4.1'e ertelenmiştir.
- **Secret yönetimi:** `.env` dosyası + Docker secret. AWS Secrets Manager entegrasyonu v5'te.

---

## Doküman Haritası

| Doküman | İçerik | Ne zaman bakılır |
|---------|--------|-----------------|
| [[01_PROJECT_OVERVIEW]] | Proje tanıtımı, kapsam, başarı kriterleri | Projeye ilk giriş; kapsam sorusu |
| [[02_DOMAIN_MODEL]] | Entity'ler, ilişkiler, iş kuralları, state machine'ler | Yeni entity veya iş kuralı eklerken |
| [[03_DATABASE_SCHEMA]] | Tablolar, alanlar, index'ler, migration stratejisi | DB'ye dokunmadan önce |
| [[03_API_CONTRACTS]] | Tüm endpoint'ler, request/response şemaları, hata kodları | Yeni endpoint açarken, fetch kodu yazarken |
| [[05_BACKEND_SPEC]] | FastAPI klasör yapısı, router/service/repository pattern'leri | Backend kodu yazarken |
| [[06_FRONTEND_SPEC]] | Vanilla JS modüler yapısı, fetch pattern, state yönetimi | Frontend feature geliştirirken |
| [[07_SCREEN_CATALOG]] | Tüm ekranların detayı, alan ve buton tanımları | Yeni ekran yaparken |
| [[08_SECURITY_IMPLEMENTATION]] | Auth akışı, JWT, CSRF, güvenlik header'ları, audit log | Güvenlik kritik kod değişikliğinde |
| [[09_TESTING_STRATEGY]] | Test piramidi, araçlar, coverage hedefleri | Test yazarken; PR öncesi self-check |
| [[10_DEV_WORKFLOW]] | Git flow, Docker setup, commit standardı, ADR'lar | Yeni iş başlarken |
| [[11_IMPLEMENTATION_ROADMAP]] | v3→v4 geçiş fazları, bağımlılık grafiği, risk kaydı | Sprint planlama; hangi modül önce |

---

Dokümanlar canlı artifact'lerdir. Mimari kararlarda değişiklik olduğunda ilgili doküman güncellenir; büyük yapısal değişikliklerde set yeniden üretilir.
