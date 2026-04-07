# LaundroStar - Çamaşırhane Otomasyon Sistemi

LaundroStar, fabrikaların ve işletmelerin çamaşırhane süreçlerini otomatikleştirip personellerin kıyafetlerinin temizlik durumunu takip etmesini sağlayan, Dockerize edilmiş modern bir web uygulamasıdır.

## Mimari ve Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| **Backend** | Python 3.11, FastAPI (async/await, RESTful API) |
| **Veritabanı** | PostgreSQL 16 Alpine, SQLAlchemy (ORM) |
| **Cache / Rate Limit** | Redis 7 Alpine |
| **Web Sunucusu** | Nginx (Reverse Proxy, SSL/TLS, Security Headers) |
| **Güvenlik** | JWT + Token Blacklist, Bcrypt, SlowAPI + Redis, RBAC, Şifre Politikası |
| **Frontend** | HTML5, Tailwind CSS, Vanilla JavaScript, Chart.js, jsPDF, QRious |
| **Konteynerizasyon** | Docker, Docker Compose |

## Proje Yapısı

```
camasirhane_v2/
├── app/
│   ├── main.py         # API uç noktaları ve iş mantığı
│   ├── models.py       # SQLAlchemy veritabanı tablo tanımlamaları
│   ├── schemas.py      # Pydantic veri doğrulama ve yanıt modelleri
│   ├── security.py     # Auth, RBAC, JWT blacklist, Redis, şifre politikası
│   ├── database.py     # Veritabanı bağlantısı ve oturum yönetimi
│   └── static/         # Frontend dosyaları (app.js, style.css, index.html vb.)
├── nginx/
│   ├── Dockerfile      # Nginx imaj kuralları
│   └── nginx.conf      # Reverse proxy, SSL ve güvenlik header'ları
├── docs/               # Proje dökümantasyonları
├── Dockerfile          # Web servisi imaj kuralları (non-root appuser)
├── docker-compose.yml  # Servis orkestrasyonu (db, redis, web, nginx)
├── requirements.txt    # Python bağımlılıkları
└── .env.example        # Ortam değişkenleri şablonu
```

## Kurulum

```bash
# Repoyu klonla
git clone https://github.com/bgrkurugollu-cpu/camasirhane_v2.git
cd camasirhane_v2

# Ortam değişkenlerini ayarla
cp .env.example .env
# .env dosyasını düzenle: SECRET_KEY, POSTGRES_PASSWORD

# SSL sertifikası oluştur (ilk kurulumda bir kez)
mkdir -p nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certs/key.pem -out nginx/certs/cert.pem -subj "/CN=localhost"

# Servisleri başlat
docker compose up -d --build
```

## Güvenlik Mimarisi

- **RBAC:** `admin` ve `user` rolleri. Admin; personel, RFID ve raporları yönetir.
- **JWT + Token Blacklist:** Logout sonrası token Redis'e blacklist'e alınır, süre dolana kadar geçersizdir.
- **Rate Limiting:** SlowAPI + Redis backend ile IP bazlı istek sınırlaması (restart-safe, dağıtık).
- **Şifre Politikası:** Büyük/küçük harf, rakam ve özel karakter zorunlu; 90 günde bir değiştirme zorunluluğu; son 3 şifre tekrar kullanılamaz.
- **Nginx Reverse Proxy:** API doğrudan internete açık değil; HSTS, CSP, X-Frame-Options, X-Content-Type-Options header'ları aktif.
- **Non-root Container:** Web servisi `appuser` (UID 1000) olarak çalışır.
- **Audit Log:** Tüm kritik işlemler (kim, hangi IP, ne zaman) PostgreSQL'e yazılır.

## Temel Çalışma Akışı

1. **Kirli Giriş:** İşçinin RFID/sicil numarası okutulduğunda kıyafet sisteme "kirli" olarak girer.
2. **Temizlendi İşareti:** Yıkama sonrası arayüzden "Temizlendi" seçilir; kayıt `kirli_kiyafetler`'den `temiz_kiyafetler` tablosuna taşınır ve otomatik raf ataması yapılır.
3. **Teslim:** Kıyafet çalışana teslim edildiğinde kayıt kapanır.

## Detaylı Dokümantasyon

Geliştirici kılavuzu, API referansı ve deployment rehberi için: [docs/developer_guide.md](docs/developer_guide.md)