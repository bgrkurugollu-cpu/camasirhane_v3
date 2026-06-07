# LaundroStar - AI Geliştirme Bağlamı ve Proje Hafızası

Bu dosya, LaundroStar projesinin AI destekli "Faz 2 Vibecoding Standartları" uyarınca üretildiğine dair bağlam bilgisini barındırır ve yeni eklenecek geliştirici veya yapay zeka asistanlarına yol göstermesi amacıyla hazırlanmıştır.

## Mimari Prensipler
1. **Modüler Monolith:** Tüm özellikler `app/modules/` dizini altında kendi klasöründe (auth, islem, calisan, kiyafet, audit vb.) toplanmıştır. Her modül kendi içinde `router.py` (HTTP Katmanı), `service.py` (İş Mantığı) ve `repository` mantığı ile katmanlanmıştır. Bu kuralı bozacak şekilde controller (router) içine iş kuralları sızdırılamaz.
2. **Stateless Güvenlik:** Session tutulmaz. Yetkilendirme sadece RS256 algoritmasıyla imzalanmış JWT token ile yapılır (HS256/SECRET_KEY yasak — ADR 0001). Frontend, API çağrılarında bu token'ı memory state üzerinden iletir, refresh token httpOnly cookie'dedir. CSRF için Double Submit Cookie kullanılır. Admin hesapları için TOTP tabanlı MFA mevcuttur (ADR 0007); MFA aktif kullanıcıda login `mfa_required` döner ve `/auth/mfa/verify` ile ikinci faktör doğrulanır.
3. **Standart Hata Yönetimi:** Hatalar sadece `AppException` (ve onun BusinessLogicException, AuthException vb. alt sınıfları) fırlatılarak yönetilir. `exceptions.py` dışında HTTP status code ile manuel dönüş yapılmamalıdır.
4. **Vanilla JS Frontend:** Frontend için herhangi bir UI framework (React/Vue) kullanılmamaktadır. DOM helper fonksiyonları (`refactor_frontend_dom.py` ile oluşturulmuştur) aracılığıyla safe DOM manipülasyonu yapılır. `innerHTML` kesinlikle yasaktır (XSS önlemi).

## Prompt Log Politikası ve Karar Alma (ADRs)
Projede "Vibecoding" (AI güdümlü kodlama) yapıldığı için, mimariyi etkileyen tüm kararlar, AI ile müzakere edilmiş bile olsa `docs/adr/` klasörü altına "Architecture Decision Record" (ADR) olarak eklenmek zorundadır. Yeni bir kütüphane ekleneceği zaman, yeni bir algoritma kurulacağı zaman (Örn. Raf Atama algoritması) önce tartışma yürütülmeli, onaylandıktan sonra ADR yazılmalıdır.

### Dikkat Edilmesi Gereken Kritik Modüller
- `app/main.py`: CORS, Middleware ve Rate Limiter (slowapi) burada tanımlıdır. `allow_origins=["*"]` gibi güvenlik açıkları asla kabul edilemez, her zaman env üzerinden kontrol edilmelidir.
- `app/security.py`: RS256 özel/açık anahtarlarını, token üretim/doğrulama ve TOTP MFA yardımcılarını (pyotp) barındırır.
- `app/modules/auth/`: Login (1. faktör), MFA (2. faktör — `/auth/mfa/*`), refresh ve logout mantığı.
- İş Akışı Algoritması: `app/modules/islem/shelf_service.py` içerisindeki `assign_shelf` fonksiyonu kıyafetlerin raflara atanmasını sağlar (ADR 0004: cinsiyet baş harfi 'K' → E rafı, diğerleri → A–D,F–H). Cinsiyet hem `'K'/'E'` kodu hem `'Kadın'/'Erkek'` kelimesi olarak gelebilir; normalize edilir.
- `tests/`: Kod coverage oranı **en az %80** tutulmalıdır (`pytest.ini: --cov-fail-under=80`). Testler PostgreSQL (`TEST_DATABASE_URL`) veya sqlite fallback ile çalışır; her test fonksiyonu şemayı sıfırlayarak izole çalışır. Yeni iş mantığı yazılırken `pytest` testleri `tests/` klasörüne aynı anda eklenmelidir.

Yeni geliştirme yapacak ekip üyesi / AI modeli, kodlamaya başlamadan önce bu prensipleri ve mevcut ADR'leri mutlaka okumalıdır.
