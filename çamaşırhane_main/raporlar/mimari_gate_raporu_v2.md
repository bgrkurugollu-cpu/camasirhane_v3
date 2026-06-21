# Mimari Gate Raporu: LaundroStar v3

**Tarih:** 2026-06-14  
**Doküman Paketi:** `docs/ozet.md`, `docs/topoloji.md`, `docs/developer_guide.md`, `docs/kurulum_rehberi.md`, `docs/adr/0001–0007`  
**Gate Kararı:** ❌ GEÇEMEDİ

---

## Özet

LaundroStar, fabrika çamaşırhaneleri için geliştirilmiş modüler monolith bir RFID otomasyon sistemidir. Önceki gate'de blocker olarak işaretlenen MFA (TOTP) ve CSRF eksiklikleri ADR 0007 ve ADR 0005 ile kapatılmış; mimari genel olarak olgunlaşmış ve doküman kalitesi belirgin şekilde artmıştır. Bu turda iki blocker tespit edilmiştir: profil fotoğrafı yükleme endpoint'i için virus tarama politikası tanımlanmamıştır ve deployment modeli (tek tesis on-premise mi, çok-tesis merkezi kurulum mu) hiçbir dokümanda tanımlanmamıştır. İkinci blocker mimari seçimlerin tamamını etkileyen temel bir kapsam sorusudur ve ADR 0008 ile netleştirilmesi gerekmektedir.

---

## Skor Tablosu

| #   | Boyut                                       | Skor | Not                                                                                                                     |
| --- | ------------------------------------------- | ---- | ----------------------------------------------------------------------------------------------------------------------- |
| 0   | Doküman tamlığı (önkoşul)                   | ⚠️   | Deployment modeli (tek tesis / çok-tesis) kapsam dışı bırakılmış; tüm teknik kararların zemini olan bu soru yanıtsız    |
| 1   | Katmanlı mimari & sorumluluk ayrımı         | ✅    | Router/Service/Repository net ayrılmış; AppException hiyerarşisi düzgün                                                 |
| 2   | Tech stack, DB, ORM                         | ⚠️   | Vanilla JS kurumsal standarttan sapma (ADR 0002 gerekçeli); Keycloak yerine standalone auth (ADR 0003 gerekçeli)        |
| 3   | Güvenlik — Auth / MFA / Rol matrisi         | ❌    | Profil fotoğrafı upload var, virus tarama politikası yok — BLOCKER                                                      |
| 4   | Entegrasyon — Topoloji / API katmanları     | ✅    | Dahili sistem; topoloji diyagramı, Public/Private/Internal katmanlama topoloji.md §11'de                                |
| 5   | Ölçeklenebilirlik & performans              | ⚠️   | Beklenen yük tek tesis için belirtilmiş; çok-tesis senaryosunda yük tahmini geçersiz; connection pool ayarları belgesiz |
| 6   | Test edilebilirlik                          | ⚠️   | tests/ klasörü ve %80 hedef var (CLAUDE.md'de); doküman paketi içinde test stratejisi yüzeysel                          |
| 7   | Loglama — JSON / aggregation / hata kodları | ⚠️   | structlog + audit log + OpenSearch hedefi var; "kritik log" kategorisi ve PII maskeleme stratejisi belirsiz             |
| 8   | Modülerlik                                  | ✅    | modules/ yapısı net; cross-cutting concern'ler ayrılmış                                                                 |
| 9   | Deployment & Docker                         | ✅    | Multi-stage, non-root (appuser), pinned images, healthcheck, 3 ayrı container                                           |
| 10  | Klasör yapısı                               | ✅    | Python/FastAPI standardına uygun; modüller görünür                                                                      |

**Genel Uygunluk:** 5/11 yeşil, 5/11 sarı, 1/11 kırmızı

---

## Özel Kontrol Bulguları

### ⚡ Tespit Edilen Çelişkiler

- **localStorage vs. memory-state çelişkisi** — `topoloji.md §8` "State: `localStorage` — JWT token saklanır" derken `developer_guide.md` ve `CLAUDE.md` "token'ların `localStorage` saklanması iptal edilmiştir, memory-only state (`AppState`) kullanılmaktadır" diyor. `topoloji.md §8` güncellenmemiş. 🟡

- **Endpoint prefix tutarsızlığı** — `topoloji.md §3.2` "Kullanıcı Yönetimi (Admin)" tablosunda uçlar `/api/users` şeklinde `v1` öneksiz; aynı dokümanın §11'i ve `developer_guide.md` tüm uçların `/api/v1/...` ile başladığını söylüyor. 🟡

- **main.py açıklaması yanıltıcı** — `topoloji.md §10` dizin yapısında `main.py` "FastAPI uygulama giriş noktası + **tüm endpoint'ler**" olarak açıklanmış; gerçekte endpoint'ler `modules/*/router.py` içinde. 🟡

---

### 🧠 AI Destekli Geliştirme & Kurumsal Hafıza

| Kontrol | Durum | Not |
|---|---|---|
| C.1 ADR Kalitesi | ⚠️ | 7 ADR var, yapısal format tam; bazılarında "AI önerdi ve uyguladı" formatı — insan kararının gerekçesi yüzeysel |
| C.2 AI Bağlam Dosyası | ✅ | `CLAUDE.md` mevcut ve kapsamlı |
| C.3 Prompt Log Politikası | ✅ | ADR'lere entegre "AI Rolü" alanı politika yerine geçiyor |
| C.4 Devralınabilirlik | ⚠️ | ADR 0003 ve ADR 0007 iyi gerekçelendirilmiş; ADR 0001, 0002, 0005, 0006'da insan kararının gerekçesi eksik |
| C.5 Test Coverage Niyeti | ✅ | %80 hedef, pytest.ini'de fail-under=80 |

Proje CLAUDE.md ve kapsamlı ADR paketiyle genel olarak devredilebilir durumda. ADR 0001, 0002, 0005, 0006'daki "AI Rolü" alanlarının "AI önerdi → insan şu gerekçeyle kabul etti" formatına güncellenmesi yeterli.

---

## Detaylı Bulgular

### 🔴 Blocker'lar (kodlamadan önce mutlaka çözülmeli)

**1. Profil fotoğrafı upload — virus tarama politikası yok**

`topoloji.md §3.2`'de `POST /api/v1/users/me/photo` endpoint'i var (PNG yükleme). Hiçbir dokümanda yüklenen dosya için virus/malware tarama politikası tanımlanmamış. PNG format kısıtlaması tek başına yeterli koruma değildir; polyglot dosya saldırıları (PNG başlıklı kötücül içerik) bu denetimi atlatabilir.

- **Öneri:** Magic byte doğrulaması + boyut limiti minimum olarak eklenmeli. Tarama başarısız olduğunda davranış (red/karantina/admin alert) politikaya bağlanmalı. `topoloji.md §7` ve `developer_guide.md` güvenlik bölümüne yazılmalı.

---

**2. Deployment modeli tanımlanmamış — ADR 0008 gerekli**

Doküman paketi boyunca tek bir tesis varsayımıyla yazılmış (`topoloji.md §12`: "Faz 1 hedef tesis"). `ozet.md §1` ise sistemin amacını "fabrika**ların** ve tesis**lerin** çamaşırhane süreçlerini dijitalleştirme" olarak tanımlıyor. Bu iki ifade çelişiyor ve temel bir mimari soru yanıtsız kalıyor:

> **Uygulama tek tesise mi kurulacak, birden fazla tesise mi?**

Bu sorunun cevabı mevcut mimari kararların büyük bölümünü doğrudan etkiliyor.

#### İki Alternatifin Değerlendirmesi

**Alternatif A — On-premise, her tesiste ayrı kurulum**

Her tesis kendi `docker-compose`'u ile bağımsız çalışır. Veri izolasyonu ve ağ bağımsızlığı (ADR 0003) avantajları korunur. Ancak bu modelin operasyonel gerçeği çoğu zaman göz ardı edilir:

*SDLC ve versiyon yönetimi:* N tesis = N bağımsız deployment pipeline'ı demektir. Yeni bir özellik çıktığında her tesise ayrı ayrı uygulanması gerekir. Tesis A v1.4 çalışırken Tesis B hâlâ v1.2'de kalabilir. Destek sorgusunda "hangi versiyondasın?" sorusu zorunlu hale gelir; regression testi farklı sürümler için çarpanla çoğalır.

*Security patch yönetimi:* Bir güvenlik açığı tespit edildiğinde (örneğin JWT kütüphanesinde CVE), tüm tesislere eş zamanlı patch uygulanamaz. Her tesis için ayrı SSH bağlantısı, ayrı `docker-compose pull && docker-compose up`, ayrı doğrulama. Bir tesis güncellenmeden kaldığı sürece risk tüm ekosistemi tehdit etmeye devam eder. Bu, bir güvenlik zafiyetini "yamadık" yerine "büyük ihtimalle yamadık" noktasına çeker.

*Sertifika ve config drift:* Her tesiste ayrı SSL sertifikası expiry takvimi, ayrı `.env` yönetimi, ayrı nginx config. Zamanla tesisler arasında konfigürasyon farklılıkları (config drift) kaçınılmaz olur ve bir tesiste çalışan şeyin diğerinde neden çalışmadığını anlamak ciddi debug yükü yaratır.

*Penetration testing ve güvenlik denetimleri:* Her tesis ayrı kurulum olduğundan teknik olarak her biri ayrı test kapsamı gerektirir. Pratikte "referans kurulumu test ettik, diğerleri aynı" kabulü yapılsa da bu bir güvenlik riski ve uyumluluk boşluğudur.

*Monitoring körü:* Her tesisin log'ları o tesiste kalır. Tek bir tesis sessizce çöktüğünde merkezi bir uyarı mekanizması yoktur. `topoloji.md §13`'teki OpenSearch hedefi bu modelde her tesisin kendi OpenSearch'ini gerektiriyor — ya da tesis log'larını merkeze göndermek için ek altyapı.

**Sonuç: Teknik olarak çalışır; operasyonel olarak ölçeklenmez. 2–3 tesis için yönetilebilir, 5+ tesis için bakım yükü kabul edilemez hale gelir.**

---

**Alternatif B — Merkezi, çok-tesis (multi-tenant) kurulum**

Tek uygulama, tüm tesisler; merkezi deployment, tek SSL, tek security patch. Operasyonel yük tesis sayısından bağımsız hale gelir. Ancak mevcut kod tabanında hiçbir tenant izolasyonu yok — tek PostgreSQL şeması, tek `users` tablosu. Bu alternatif şunları gerektirir: tüm tablolara `tenant_id` eklenmesi, Keycloak entegrasyonu (ADR 0003 geçersiz kalır), raf konfigürasyonunun config-driven hale getirilmesi (ADR 0004 kırılır), API katmanında tenant doğrulaması. Mevcut kod tabanına göreli büyük bir yatırım gerektirir; kapalı devre ağ gereksinimini karşılamaz.

---

#### Önerilen Yaklaşım: Fleet-managed On-premise (Alternatif C)

İki alternatifin ikisi de kendi başına yetersiz. Gerçekçi öneri, on-premise veri izolasyonu avantajını merkezi operasyonel verimlilikle birleştiren **fleet management katmanıdır:**

- Her tesis kendi izole instance'ında çalışmaya devam eder (veri izolasyonu, ağ bağımsızlığı)
- Tüm tesislere deployment, Ansible veya benzeri IaC araçlarıyla **tek komutla** yapılır
- Versiyon tutarlılığı pipeline tarafından zorlanır; tesis başına sapma engellenir
- Tüm tesis log'ları merkezi OpenSearch'e Fluent Bit üzerinden akar (tek monitoring panosu)
- SSL sertifika yönetimi otomatize edilir (internal CA veya Let's Encrypt + certbot)
- Security patch'ler tüm fleet'e eş zamanlı uygulanır, doğrulaması tek pipeline'dan yapılır

Bu yaklaşım için Faz 1'de kod değişikliği gerekmez; gereken yatırım IaC ve CI/CD pipeline'dır. Ekip 3–5 tesis aşamasına geçmeden bu altyapıyı kurmazsa Alternatif A'nın operasyonel yükü altında ezilir.

**ADR 0008'de netleştirilmesi gereken sorular:** Kaç tesis hedefleniyor (şimdi ve 2 yıl içinde)? Fleet management için IaC yatırımı bütçelendi mi? Kapalı devre ağ kısıtı tüm tesislerde geçerli mi? Bu sorular yanıtlanmadan deployment modeli kararı verilemez.

---

### 🟡 Uyarılar

- **localStorage / memory-state doküman tutarsızlığı** — `topoloji.md §8` eski bilgi içeriyor; `"State: memory-only (AppState) · refresh token httpOnly cookie"` olarak güncellenmeli.

- **Endpoint prefix tutarsızlığı** — `topoloji.md §3.2` "Kullanıcı Yönetimi" tablosundaki `/api/users` uçları `/api/v1/users` olarak düzeltilmeli.

- **main.py açıklaması** — `topoloji.md §10`'daki açıklama `"FastAPI giriş noktası; endpoint'ler modules/*/router.py içinde"` şeklinde güncellenmeli.

- **TOTP secret plaintext DB'de** — ADR 0007'de bilinçle belgelenmiş; v5 planı var. Kabul edilebilir, not olarak tutulmalı.

- **Connection pool ayarları belgesiz** — `pool_size`, `max_overflow`, `pool_timeout` env'den alınmıyor veya dokümante edilmemiş. Faz 1 yükü için kritik değil.

- **"Kritik log" kategorisi belirsiz** — App log ve Audit log iyi tanımlanmış; alarm seviyesi (DB çöküşü, güvenlik ihlali şüphesi) kategorisi ve alerting entegrasyonu belirtilmemiş.

- **ADR'lerde insan kararı gerekçesi yüzeysel** — ADR 0001, 0002, 0005, 0006'daki "AI Rolü" alanları "AI önerdi ve uyguladı" formatında; "insan neden kabul etti" sorusu yanıtsız. ADR 0003 ve ADR 0007 model alınmalı.

---

### 🟢 İyi Yapılmış

- **Önceki gate blocker'ları tamamen kapatıldı** — MFA (ADR 0007) ve CSRF (ADR 0005) eksiksiz uygulanmış; 2. faktör akışı, devre dışı bırakma ve `ADMIN_MFA_REQUIRED` politikası dahil.
- **7 ADR — yapısal ve kapsamlı** — Özellikle ADR 0003 ve ADR 0007 bu paketin en güçlü belgeleri; bağlam, alternatif ve sonuç detayları eksiksiz.
- **Docker best practices** — Multi-stage build, non-root user (`appuser`), pinned image tag'leri, healthcheck zinciri — tümü doğru uygulanmış.
- **API katmanlama (Public / Private / Internal)** — `topoloji.md §11` tablo halinde net belgelenmiş.
- **Audit log append-only** — PostgreSQL RULE ile append-only zorunluluğu ve OpenSearch/ELK aggregation hedefi standartla örtüşüyor.
- **Beklenen yük belgelenmiş** — `topoloji.md §12` RPS, eşzamanlı kullanıcı ve veri büyüme projeksiyonu ile performans kararlarını bağlamlandırmış.
- **CORS wildcard yasak** — `CORS_ORIGINS` env'den okunuyor, `*` açıkça yasaklanmış.

---

## Gate Kararı Gerekçesi

İki blocker var. Birincisi (virus tarama) teknik bir uygulama politikası eksiği — kısa sürede kapatılabilir. İkincisi (deployment modeli) mimari bir kapsam sorusu olup ADR 0008 yazılmadan diğer kararların sağlamlığı tartışmaya açık kalır: Vanilla JS seçimi, standalone auth, raf algoritmasının hardcoded olması — hepsinin gerekçesi "tek tesis, dahili araç" varsayımına dayanıyor. Bu varsayım dokümante edilmediği sürece proje yön değiştirdiğinde hangi kararların yeniden değerlendirileceği bilinemez.

---

## Sonraki Adımlar

- [ ] **[BLOCKER]** Profil fotoğrafı upload için virus/malware tarama politikası tanımla ve `topoloji.md §7` ile `developer_guide.md`'ye ekle
- [ ] **[BLOCKER]** ADR 0008: Deployment modeli kararı yaz — on-premise ayrı kurulum olarak netleştir; Alternatif B'nin neden reddedildiğini gerekçelendir; Faz 2 merkezi raporlama taslağını not et
- [ ] `topoloji.md §8` → `localStorage` satırını memory-state / httpOnly cookie olarak güncelle
- [ ] `topoloji.md §3.2` → `/api/users` → `/api/v1/users` düzeltmesi
- [ ] `topoloji.md §10` → `main.py` açıklamasını modüler yapıya uygun güncelle
- [ ] ADR 0001, 0002, 0005, 0006 → "AI Rolü" alanlarını "AI önerdi → insan şu gerekçeyle kabul etti" formatına yükselt
- [ ] Revize doküman paketi ile tekrar gate başvurusu

---

*Rapor: mimari-gate skill v1 — LaundroStar v3 — 2026-06-14*
