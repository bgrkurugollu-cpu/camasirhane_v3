# LaundroStar - Çamaşırhane Otomasyon Sistemi

LaundroStar, fabrikaların ve işletmelerin çamaşırhane süreçlerini otomatikleştirip personellerin kıyafetlerinin temizlik durumunu takip etmesini sağlayan, Docker tabanlı modern bir web uygulamasıdır.

## Mimari ve Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| **Backend** | Python 3.11, FastAPI |
| **Veritabanı** | PostgreSQL 16 (Alpine), SQLAlchemy ORM |
| **Güvenlik** | JWT (JSON Web Tokens), bcrypt (şifre hashleme), slowapi (rate limiting) |
| **Frontend** | HTML5, Tailwind CSS, Vanilla JavaScript, Chart.js |
| **Proxy / TLS** | Nginx (HTTP→HTTPS yönlendirme, self-signed TLS) |
| **Konteynerizasyon** | Docker, Docker Compose (3 servis: db, web, nginx) |

## Proje Yapısı

```
camasirhane/
├── app/
│   ├── main.py         # API uç noktaları ve iş mantığı
│   ├── models.py       # SQLAlchemy veritabanı tablo tanımlamaları
│   ├── schemas.py      # Pydantic veri doğrulama ve yanıt modelleri
│   ├── security.py     # JWT, RBAC ve şifre yönetimi
│   ├── database.py     # Veritabanı bağlantısı ve oturum yönetimi
│   └── static/         # Frontend dosyaları (index.html, app.js, style.css)
├── nginx/
│   ├── nginx.conf      # Nginx proxy ve TLS konfigürasyonu
│   └── certs/          # TLS sertifika dosyaları (gitignored)
├── docs/               # Proje dokümantasyonları
├── .env.example        # Ortam değişkenleri şablonu
├── Dockerfile          # Web servisi imaj kuralları
├── docker-compose.yml  # Servis orkestrasyon dosyası
└── requirements.txt    # Python bağımlılıkları
```

## Temel Çalışma Akışı

Sistem, kıyafet döngüsünü üç aşamada takip eder:

1. **Kirli Girişi:** Personelin RFID etiketi veya sicil numarası okutulduğunda kıyafet `kirli_kiyafetler` tablosuna eklenir.
2. **Temizlendi İşlemi:** Kirli listedeki kayıt "Temizlendi" olarak işaretlenir; kayıt `temiz_kiyafetler` ve `teslim_edilenler` tablolarına aktarılır. Sistem, personelin cinsiyetine göre otomatik olarak bir raf konumu atar.
3. **Teslim:** Teslim edilecekler listesindeki kayıt teslim edildiğinde döngü tamamlanır.

## Raf Sistemi

Çamaşırhane rafları 8 bölümden oluşur (**A–H**), her bölüm 7 kat × 5 kompartıman = 35 göze sahiptir. Göze kapasitesi: Kat 7 → 1 adet, Kat 1–6 → 3 adet.

- **Cinsiyet yönlendirme:** Kadın personellerin kıyafetleri yalnızca **E rafı**na atanır. Erkek personellerin kıyafetleri A–D ve F–H raflarına atanır.
- Atama algoritması boş/kısmi gözleri kapasite dolma sırasına göre doldurur.

## Kullanıcı Rolleri

| Rol | Yetkiler |
|---|---|
| **admin** | Tüm personel/RFID yönetimi, istatistikler, kullanıcı yönetimi |
| **user** | Günlük kıyafet operasyonları (kirli girişi, temizlendi, teslim) |

## Öne Çıkan Özellikler

- **2D Raf Simülasyonu:** A–H raflarının interaktif görsel haritası; gözlerin doluluk durumu renk kodlu gösterilir, üzerine gelindiğinde popup ile içerik listelenir.
- **RFID Oku Simülasyonu:** Kirli kıyafet girişinde "RFID Oku" butonu ile 10'a kadar rastgele personel taranır.
- **Tablo Arama:** Tüm tablo ekranlarında (kirli, temiz, teslim, personel, RFID) anlık metin araması.
- **Raf Arama:** Sicil numarası veya ad soyad ile raf konumu araması; sonuç bulunduğunda ilgili raf ve göze otomatik yönlendirir.
- **Denetim Logu:** Tüm kritik işlemler kullanıcı adı ve IP adresiyle kayıt altına alınır.
