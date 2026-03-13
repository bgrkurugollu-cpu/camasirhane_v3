# LaundroStar - Çamaşırhane Otomasyon Sistemi

Yıldız Tech tarafından geliştirilen LaundroStar, fabrikaların ve işletmelerin çamaşırhane süreçlerini otomatikleştirip, personellerin (işçilerin) kıyafetlerinin temizlik durumunu takip etmeyi sağlayan Dockerize edilmiş modern bir web uygulamasıdır.

## Mimari ve Teknoloji Yığını
Platform aşağıdaki teknolojiler üzerine kurgulanmıştır:

* **Backend:** Python 3.11, FastAPI (Hızlı ve modern API geliştirimi)
* **Veritabanı:** SQLite (Kolay kurulum ve taşınabilirlik `data/camasirhane.db`), SQLAlchemy (ORM mimarisi)
* **Güvenlik:** JWT (JSON Web Tokens), Bcrypt (Şifre hashleme protokolü)
* **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript, Chart.js (Grafik kütüphanesi)
* **Konteynerizasyon:** Docker, Docker Compose

## Proje Yapısı

```
camasirhane/
├── app/
│   ├── main.py         # API Uç Noktaları (Endpoints) ve İş Mantığı
│   ├── models.py       # SQLAlchemy Veritabanı Tablo Tanımlamaları
│   ├── schemas.py      # Pydantic Veri Doğrulama ve Yanıt Modelleri
│   ├── security.py     # Auth, RBAC, Hasher ve Token yönetim servisleri
│   ├── database.py     # Veritabanı bağlantısı ve oturum yönetimi
│   └── static/         # Frontend dosyaları (app.js, style.css, index.html vb.)
├── data/               # SQLite veritabanı dosyasının tutulduğu docker volume'u
├── docs/               # Proje dökümantasyonları
├── Dockerfile          # Web servisi için imaj kuralları
├── docker-compose.yml  # Servislerin orkestrasyon dosyası
└── requirements.txt    # Python kütüphane bağımlılıkları listesi
```

## Temel Çalışma Algoritması

Sistem, işlenmesi gereken kıyafetlerin döngüsünü 3 farklı tabloda / durumda takip eder:

1. **Kirli Girişi (`kirli_kiyafetler`):** İşçinin RFID etiketi veya Sicil Numarası okutulduğunda kıyafet çamaşırhaneye "kirli" olarak girer.
2. **Kıyafetin Temizlenmesi (`temiz_kiyafetler` ve `teslim_edilenler`):** Kirli listesindeki ürünler yıkandıktan sonra arayüz üzerinden "Temizlendi" olarak işaretlenir. Bu eylem sonrası:
   - Kayıt `kirli_kiyafetler` tablosundan silinir.
   - İlgili kayıt log tutmak amacıyla `temiz_kiyafetler` tablosuna eklenir.
   - Eş zamanlı olarak çalışana verilmeye hazır olduğunu belirtmek adına `teslim_edilenler` tablosuna kaydedilir.

3. **Yetkilendirme (RBAC):** `admin` rolü tüm kullanıcıları görebilir, düzenleyebilir ve geçmiş istatistiklerle raporlamalara erişebilir. `user` rolü sadece günlük kıyafet operasyonlarını yapabilir ve kendi profilini güncelleyebilir.
