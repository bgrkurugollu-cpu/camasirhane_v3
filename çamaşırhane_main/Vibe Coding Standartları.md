tags: #ai #kavram #vibecoding

# Teknik Tasarım Şablonu & Mimari Standartlar

> **Bu dosyayı projenizin köküne koyun.**
> Tasarım dokümanınızı yazarken her bölümü doldurun.
> Eksik bıraktığınız her madde, mimari gate'te blocker veya uyarı olarak döner.

---

## 0. Proje Tanımı ✏️

> Bu bölüm tasarımın ilk sayfası olmalı. Okuyucuyu teknik detaylara çekmeden önce projeyi anlamasını sağlar.

| Alan                  | Yanıt                                                                            |
| --------------------- | -------------------------------------------------------------------------------- |
| **Kısa tanım**        | Bu uygulama ne yapıyor? (1-3 cümle, teknik jargonsuz)                            |
| **Amaç**              | Hangi iş/kullanıcı sorununu çözüyor?                                             |
| **Kapsam**            | Faz 1'de ne var, ne yok? Kapsam dışı kalemler neler?                             |
| **Kullanıcı kitlesi** | Kim kullanacak? (dahili çalışan / müşteri / partner / sistem — tahmini büyüklük) |
| **Uygulama tipi**     | Web SPA / Web SSR / Mobil native / Mobil hybrid / Masaüstü / API-only / Hybrid   |

---

## 1. Mimari Stil & Katman Ayrımı ✏️

**Seçilen stil:** `Modüler Monolith` / `Mikroservis` / `Diğer: ___`
> Mikroservis seçildiyse gerekçe yaz: bağımsız ölçekleme, farklı ekip sahipliği, farklı release cycle.

**Katmanlar:**

| Katman        | Teknoloji | Sorumluluk |
| ------------- | --------- | ---------- |
| Frontend      |           |            |
| BFF *(varsa)* |           |            |
| Backend       |           |            |
| Veritabanı    |           |            |

**BFF gerekli mi?**
- [ ] Frontend birden fazla backend servisini doğrudan çağırıyor → BFF gerekli
- [ ] Tek backend, tek frontend → BFF gerekmez

**Kontrol listesi:**
- [ ] Controller → Service → Repository katmanları ayrı
- [ ] İş kuralları service katmanında (controller'da değil)
- [ ] Service içinde HTTP Request/Response objesi yok
- [ ] Her katman ayrı ayrı deploy edilebilir container

---

## 2. Tech Stack ✏️

### Backend
| Alan | Seçim | Versiyon |
|------|-------|----------|
| Dil | Node.js (TS) / Java / Python | |
| Framework | NestJS / Spring Boot / FastAPI | |
| ORM | Prisma / Hibernate / SQLAlchemy | |
| Veritabanı | PostgreSQL (AWS RDS) | |

> **Not:** Onaylı diller: Node.js+TypeScript, Java 17/21, Python 3.10+. Farklı seçim için gerekçe ekle.

### Frontend
| Alan | Seçim |
|------|-------|
| Framework | React + TypeScript / Next.js |
| State (sunucu) | React Query |
| State (istemci) | Zustand / Context |

### Altyapı Bileşenleri
| İhtiyaç               | Seçim                                   | Gerekçe |
| --------------------- | --------------------------------------- | ------- |
| Caching               | Redis / Yok                             |         |
| Kuyruk                | AWS SQS / Yok                           |         |
| Log toplama           | Elasticsearch / OpenSearch / Yok        |         |
| Doküman/dosya saklama | PostgreSQL jsonb / MinIO / AWS S3 / Yok |         |
|                       |                                         |         |
|                       |                                         |         |

> **Caching varsa:** Redis. **Kuyruk varsa:** AWS SQS (Kafka yalnızca yüksek hacimli streaming için). **Log aggregation varsa:** ELK veya OpenSearch.

---

## 3. Güvenlik ✏️

### Authentication
- [ ] **Kimlik doğrulama:** OAuth2 + JWT, Kurumsal Keycloak SSO'ya entegre
- [ ] **Test/Dev ortamı:** Mock OAuth SSO (prod'a çıkmadan Keycloak'a geçiş planı belirtilmiş)
- [ ] **Admin / Superuser sayfaları:** MFA zorunlu

### Yetkilendirme
- [ ] RBAC veya ACL modeli seçilmiş ve belgelenmiş
- [ ] Rol-yetki matrisi tablo halinde hazır:

| Rol | Ekran / Aksiyon | Erişim |
|-----|-----------------|--------|
| | | ✅ / ❌ |

### Diğer
- [ ] Input validation katmanı tanımlı (Zod / Joi / Bean Validation / Pydantic)
- [ ] Secret yönetimi: env variable / secret manager — kod içinde hardcoded YOK
- [ ] PII / KVKK kapsamındaki veri maskeleniyor
- [ ] **Dosya yükleme varsa:** Virus/malware tarama politikası tanımlı

---

## 4. Entegrasyon & API ✏️

### Entegrasyon Haritası
> Her harici bağlantı için aşağıdaki tabloyu doldur.

| Sistem | Yön | Protokol | Veri Interface'i | Hata Durumu |
|--------|-----|----------|-----------------|-------------|
| | → / ← | REST / gRPC / SQS / vb. | Request/Response şeması | Timeout / Retry / Fallback |

- [ ] Topoloji diyagramı çizildi (kutu-ok, metin yetmez)
- [ ] Her entegrasyon için protokol ve sync/async belirtildi
- [ ] Gelen & giden veri interface'leri tanımlandı

### API Katmanlaması
> Tüm endpoint'leri üç katmana ayır.

| Katman | Prefix | Auth | Kimin Erişir |
|--------|--------|------|--------------|
| **Internal** | `/internal/` | App context | Aynı modülün kendisi |
| **Private** | `/private/` | Service token / iç JWT | Diğer iç servisler |
| **Public** | `/api/v1/` | OAuth2 + JWT | Dış sistemler / kullanıcılar |

- [ ] Dışarıya API sunuluyorsa: **API Gateway** seçildi ve belgelendi
- [ ] Public API Gateway arkasında (rate limit, auth proxy, logging)

### Event-Driven Mimari *(varsa)*
- [ ] Event kaybını önleyen bir pattern seçildi:
  - `Outbox Pattern` — DB transaction içinde outbox tablosuna yaz, worker ilet
  - `At-least-once + Idempotent Consumer` — tekrar teslimde duplicate yok
  - `Saga + Compensation` — her adım geri alınabilir
- [ ] Dead-Letter Queue (DLQ) stratejisi tanımlı
- [ ] Retry politikası belirtildi (max deneme, backoff)

---

## 5. Ölçeklenebilirlik & Performans ✏️

- [ ] Beklenen yük belirtildi: `___ RPS`, `___ eşzamanlı kullanıcı`, `___ GB veri`
- [ ] Kritik sorgular için index stratejisi tanımlı
- [ ] N+1 query riski olan ilişkiler için strateji var (eager load / batch / DataLoader)
- [ ] Liste döndüren her endpoint'te pagination var (cursor-based veya offset)
- [ ] Cache stratejisi: neyi, ne kadar, TTL ne, nasıl invalidate?
- [ ] Eşzamanlı yazma riski olan resource'larda **Optimistic Locking** (ETag / If-Match)

**Stack'e özel kontrol:**

<details>
<summary>Node.js / NestJS</summary>

- [ ] CPU-bound işler (şifreleme, görüntü işleme) Worker Thread veya job queue'ya taşındı
- [ ] Büyük dosyalar stream ile işleniyor (Buffer'a çekilmiyor)
- [ ] `fs.readFileSync`, sync crypto API'ler request path'inde yok
- [ ] `Promise.all` ile paralel I/O (sıralı await zinciri yerine)

</details>

<details>
<summary>Java / Spring Boot</summary>

- [ ] Container ortamında JVM heap sınırı var (`-Xmx` veya `UseContainerSupport`)
- [ ] HikariCP pool boyutu konfigüre edildi
- [ ] JPA ilişkilerinde `LAZY` fetch; N+1 için `@EntityGraph` / JOIN FETCH planlandı
- [ ] Java 21 kullanılıyorsa Virtual Thread değerlendirildi

</details>

<details>
<summary>Python / FastAPI</summary>

- [ ] `async def` endpoint içinde senkron blocking kütüphane YOK (`requests.get()` vb.)
- [ ] CPU-bound iş `run_in_executor` veya `ProcessPoolExecutor` ile ayrıldı
- [ ] Async SQLAlchemy engine kullanılıyor (senkron engine + asyncio karışımı yok)
- [ ] Uvicorn worker sayısı konfigüre edildi

</details>

---

## 6. Test Stratejisi ✏️

| Seviye | Araç | Kapsam | Hedef |
|--------|------|--------|-------|
| Unit | | Service & utility | %80+ |
| Integration | | Kritik API patikalar | Endpoint + DB |
| E2E | | Top kritik akışlar | Uçtan uca |

- [ ] Bağımlılıklar Dependency Injection ile veriliyor (mock'lanabilir)
- [ ] Test verisi: factory / fixture / seed yöntemi belirtildi
- [ ] CI gate tanımlı: unit fail → merge blok, E2E fail → release blok

---

## 7. Loglama & Gözlemlenebilirlik ✏️

**Log kütüphanesi:** `Pino` (Node) / `Logback` (Java) / `structlog` (Python)
**Format:** JSON (düz metin log KABUL EDİLMEZ)
**Aggregation hedefi:** `Elasticsearch` / `OpenSearch`

**Üç log tipi:**

| Tip | Amaç | Saklama |
|-----|------|---------|
| **App Log** | Normal işleyiş (info/warn/error) | 30 gün |
| **Audit Log** | Kim ne zaman ne yaptı (KVKK) | ≥ 1 yıl |
| **Kritik Log** | Sistem tehdidi (fatal/critical) → PagerDuty | 90 gün |

- [ ] Her log kaydında: `timestamp`, `level`, `service`, `traceId`, `message`
- [ ] Hata kodları prefix'li ve tutarlı (örn. `AUTH_`, `DB_`, `PAYMENT_`)
- [ ] PII içeren alanlar log'da maskelendi (email, şifre, TC No)
- [ ] APM / Error tracking varsa: PII scrub + environment tag konfigüre edildi

---

## 8. Modülerlik ✏️

**Modüller:**

| Modül | Sorumluluk | Public API Yüzeyi |
|-------|------------|-------------------|
| | | |

- [ ] Modüller net sınırlarla ayrılmış
- [ ] Modüller arası iletişim yalnızca public API üzerinden
- [ ] Döngüsel bağımlılık yok (A→B ve B→A aynı anda olamaz)
- [ ] Cross-cutting concern'ler (auth, logging) merkezi — her modüle kopyalanmıyor

---

## 9. Deployment & Docker ✏️

**Ortamlar:** `Dev (Docker Compose)` / `Staging` / `Prod (K8s / ECS / vb.)`

Her container için Dockerfile kontrol listesi:
- [ ] Multi-stage build (build araçları prod image'ına girmiyor)
- [ ] Non-root user (`USER appuser` veya benzeri)
- [ ] Pinned base image (`node:20-alpine`, `eclipse-temurin:21-jre-alpine` vb.) — `latest` YASAK
- [ ] Secret'lar image içinde değil → env variable / secret manager
- [ ] `.dockerignore` mevcut (node_modules, .git, .env image dışında)
- [ ] Healthcheck endpoint tanımlı (`/health`, `/ready`)

**Bağımsız deploy:**
- [ ] Frontend, BFF (varsa), Backend → her biri ayrı image
- [ ] Sürümler birbirinden bağımsız ilerleyebiliyor

---

## 10. Klasör Yapısı ✏️

> Seçilen tech stack'e uygun dizin yapısını buraya ekleyin (ağaç veya tablo).

```
# Örnek: NestJS
apps/
  api/src/
    modules/
      <modül-adı>/
        <modül>.module.ts
        <modül>.controller.ts
        <modül>.service.ts
        dto/
    common/          # guard, interceptor, filter
    database/

# Örnek: Next.js
apps/
  web/src/
    app/             # Next.js App Router
    components/
    features/
    lib/
    hooks/
    types/
```

- [ ] Her modülün nerede olduğu görünür
- [ ] Shared/common kod ayrı, her modüle kopyalanmıyor
- [ ] Test dosyaları source ile aynı yerde (`*.spec.ts`)

---

## 11. Veri Modeli & Object Model ✏️

### Veri Modeli (DB Şeması)
> Tablolar, alanlar, tipler, ilişkiler, index'ler.
> ERD diyagramı veya tablo formatında.

### Object Model (Domain Sınıfları)
> Entity'ler, Value Object'ler, Aggregate'ler, aralarındaki ilişkiler.
> UML class diagram veya metin tablosu.

> ⚠️ Bu ikisi farklıdır. Sadece DB şeması yetmez, sadece sınıf diyagramı da yetmez.

---

## Kontrol — Gate'e Göndermeden Önce

```
[ ] Bölüm 0: Proje tanımı dolu (kısa tanım, amaç, kapsam, kitle, tip)
[ ] Bölüm 0: Tech stack kararı (versiyon dahil)
[ ] Bölüm 0: Veri modeli ve object model mevcut
[ ] Bölüm 0: Rol-yetki matrisi tablo halinde
[ ] Bölüm 0: Entegrasyon haritası (entegrasyon varsa)
[ ] Bölüm 0: Test stratejisi
[ ] Bölüm 0: Klasör yapısı
[ ] Bölüm 0: Deployment planı

[ ] Auth: Keycloak SSO planı belirtilmiş
[ ] Auth: Admin/superuser sayfaları için MFA tanımlı
[ ] Docker: Multi-stage, non-root, pinned image, secret dışarıda
[ ] API: Internal/Private/Public katmanlaması yapıldı
[ ] Event: Event-driven varsa → event garantisi pattern'i seçildi
[ ] Upload: Dosya yükleme varsa → virus tarama politikası tanımlı
[ ] Concurrent write: Eşzamanlı güncelleme → Optimistic Locking planlandı
```

---

*Mimari Gate için standartların tam listesi: [mimari-gate plugin — `references/standartlar.md`]*
