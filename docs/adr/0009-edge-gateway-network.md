# ADR 0009: Edge Gateway Network — Outbound-Only Cihaz Kaydı, Onayı ve Ingestion

**Tarih:** 2026-06-15
**Durum:** Kabul Edildi

## Bağlam
Topoloji (`docs/LaundroStar_Mimari_Topoloji_Duzenlenmis.svg`), fabrika ortamında RFID okuyucular ve Zebra yazıcılarla haberleşen bir **Edge Sunucu** öngörür. Edge, okuduğu verileri merkezi uygulamaya iletmelidir; ancak topoloji kuralı nettir: *"DC → Fabrika yönünde başlatılan bağlantı yoktur; DB sunucusuna sadece App erişir."* Ayrıca Edge'in merkezde bir cihaz olarak **kaydedilip onaylanması** istenmektedir (Inductive Automation Gateway Network'teki incoming connection approval modeli). Mevcut sistemde cihaz kavramı, kayıt/onay akışı veya makine-makine kimlik doğrulaması yoktu.

## Karar
Ana uygulamaya, Edge cihazlarını yöneten **outbound-only gateway** modülü (`app/modules/edge/`) ve `edge_devices` + `edge_reading_receipts` tabloları eklenir. Akış:

1. **enroll** (`POST /api/v1/edge/enroll`, kimlik doğrulamasız): Edge kendini `device_uid` + RS256 **public key** + donanım bilgisiyle tanıtır → `pending` kayıt.
2. **status** (`GET /api/v1/edge/status`, cihaz JWT'si): Edge onay durumunu sorgular.
3. **ingest** (`POST /api/v1/edge/ingest`, cihaz JWT'si, yalnızca `approved`): Edge okuma gönderir; ana app mevcut `islem` iş mantığıyla `kirli_kiyafetler`'e yazar. `client_reading_id` ile idempotent.
4. **approve/revoke** (`POST /api/v1/edge/devices/{id}/approve|revoke`, admin + CSRF): Admin SPA'daki "Edge Cihazlar" ekranından cihazı onaylar/iptal eder.

Cihaz kimliği **RS256 cihaz anahtar çifti** ile yapılır (ADR 0001 ile tutarlı; HS256 yasak): Edge isteklerini özel anahtarıyla imzalar, ana app saklı public key ile doğrular. `enroll`/`ingest` makine-makine olduğundan `CSRFMiddleware` exempt listesine eklenir; güvenlik CSRF yerine imza + approval ile sağlanır. Tüm olaylar `audit_logs`'a yazılır (`EDGE_ENROLL/APPROVE/REVOKE/INGEST`).

## Alternatifler

### Alternatif A — Outbound API ingestion + approval (SEÇİLDİ)
Topolojiye ("DB'ye sadece App erişir", tek-yönlü transfer) tam uyumlu. İş kuralları (RFID doğrulama, audit, idempotency) tek yerde — ana app `islem` servisinde — kalır. Onay/iptal ve audit merkezîdir.

### Alternatif B — Edge'in PostgreSQL'e doğrudan yazması (REDDEDİLDİ)
Topolojiyi ihlal eder (fabrikadan DC DB'sine bağlantı), DB credential'ını fabrikaya dağıtır, approval modelini anlamsızlaştırır ve iş kurallarının Edge'de kopyalanmasını gerektirir (drift riski).

### Alternatif C — Edge'i normal kullanıcı yapıp `/auth/token` ile login (REDDEDİLDİ)
İnsan-odaklı login modeli (MFA, şifre rotasyonu, hesap kilitleme) makine kimliğiyle çakışır ve cihaz onay/iptal yaşam döngüsünü ifade edemez.

## Sonuçlar
- **Olumlu:** Topoloji ve güvenlik sınırı korunur; tek doğruluk kaynağı ana app; onay/audit merkezî; mevcut RS256 altyapısı yeniden kullanılır. Multi-tenant varsayımı (ADR 0008) ihlal edilmez — `tenant_id` eklenmez.
- **Olumsuz / azaltım:** Yeni tablolar ve makine-makine kimlik yüzeyi eklenir. Azaltım: yalnızca `approved` cihaz yazabilir (ApprovedOnly); public key değişimi yeniden onaya düşürülür; `enroll` rate-limit'e uygun konumlanır; tüm olaylar audit'lenir.
- **Test:** `tests/test_edge.py` enroll/pending-red/approve-yazım/RFID-red/revoke/idempotency/JWT senaryolarını kapsar; %80 coverage gate korunur (mevcut ~%88).

## AI Rolü
AI, veri-yolu ve cihaz-kimliği alternatiflerini topoloji uyumu, güvenlik ve iş-kuralı tekrarı açısından analiz edip outbound API ingestion + RS256 cihaz anahtar çifti + admin approval modelini önerdi. **İnsan kararı:** Proje sahibi, topolojinin tek-yönlü veri transferi kuralı ve cihaz onay gereksinimi doğrultusunda Alternatif A'yı kabul etti; doğrudan DB yazımı ve kullanıcı-login alternatifleri reddedildi. (İlgili Edge tarafı kararları: `camasirhane edge/docs/adr/0002`, `0003`.)
