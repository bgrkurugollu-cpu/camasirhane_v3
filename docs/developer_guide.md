# Geliştirici Dokümantasyonu (Developer Guide)

Bu doküman projenin Python arka ucunu destekleyen ekibi bilgilendirmek amacıyla oluşturulmuştur.

## Kurulum ve Çalıştırma

LaundroStar, Docker-compose altyapısı üzerine tam entegre çalışır.

Sistemi ayağa kaldırmak için:
```bash
docker-compose up -d --build
```

Bu kod bloğu, `Dockerfile` içindeki kuralları okuyarak bir python ortamı oluşturur, kütüphaneleri yükler (`requirements.txt`) ve ana uygulamayı (`uvicorn app.main:app`) `0.0.0.0:8085` portunda yayına açar. `data` klasörüne de SQLite veritabanı bağlar.

## Geliştirme Standartları

1. **Veri Modelleri (app/models.py)**: SQL veritabanındaki tabloları temsil eder. Tablo kolonlarının isim ve tip tanımlarından sorumludur. Yeni bir obje ekleneceğinde ilk burası düzenlenir. (Örn: `User`, `Kirli_Kiyafet`)
2. **Pydantic Şemaları (app/schemas.py)**: Gelen JSON verilerini parçalayıp doğrulamak, çıkan JSON verilerini de şekillendirmek için kullanılır. İstek atarken (Request) ve dönerken (Response) ne beklediğimizi katı (strict) olarak belirtir.
3. **Güvenlik & JWT (app/security.py)**: `bcrypt` ile şifre güvenlik altına alınır. Giriş yapanlara bir `Token` döner. Bu token, `Depends(security.get_current_user)` yapısıyla diğer endpointlerde "Sadece giriş yapanlar girebilir" koşulu sağlamak (<a href="https://fastapi.tiangolo.com/tutorial/security/">FastAPI Dependency Injection</a>) için kullanılır.
4. **Veritabanı (`app/database.py`)**: `SQLALCHEMY_DATABASE_URL` tanımlar. Bir SessionLocal nesnesi açarak `get_db` ile her endpoint çağrısında yeni ve izole bir db oturumu yaratır, çağrı bitince `finally:` bloğu ile kapatır.
5. **API Rotaları (`app/main.py`)**: Uygulamanın kalbidir. Gelen isteklerin eşleştirildiği, veritabanına sorguların atılıp manipüle edildiği, Python döngülerinin kurulduğu tüm operasyonların işlendiği yerdir.

Tüm servisler bu katmanlar arasında yatay bir iletişim sağlar ve bağımlılıkları minimumda tutar. Python dosyalarının içinde ekibe yardımcı olacak *Docstring* dökümantasyonları bırakılmıştır.
