# LaundroStar - Kurulum Rehberi

Bu rehber, LaundroStar uygulamasını sıfırdan bir sunucuya veya yerel makineye kurmak için izlenecek adımları içerir.

## Ön Koşullar

Sistemi çalıştıracağınız makinede aşağıdaki yazılımların kurulu olması gerekir:

1. **Docker Desktop** (Windows/Mac) veya **Docker Engine + Docker Compose** (Linux)
   - [Docker Desktop İndir](https://www.docker.com/products/docker-desktop/)
2. **Git** (proje dosyalarını klonlamak için)
   - [Git İndir](https://git-scm.com/downloads)
3. **OpenSSL** (TLS sertifikası oluşturmak için — genellikle Git ile birlikte gelir)

---

## Adım Adım Kurulum

### Adım 1: Proje Dosyalarını İndirin

```bash
git clone <repo-adresi> camasirhane
cd camasirhane
```

### Adım 2: Ortam Değişkenlerini Yapılandırın

Proje kök dizininde `.env.example` dosyasını kopyalayarak `.env` oluşturun:

```bash
cp .env.example .env
```

`.env` dosyasını bir metin düzenleyici ile açıp aşağıdaki alanları doldurun:

| Değişken | Açıklama |
|---|---|
| `SECRET_KEY` | JWT imzalama anahtarı — güçlü, rastgele bir değer girin |
| `POSTGRES_USER` | PostgreSQL kullanıcı adı |
| `POSTGRES_PASSWORD` | PostgreSQL şifresi — tahmin edilemez bir değer seçin |
| `POSTGRES_DB` | Veritabanı adı |
| `DATABASE_URL` | `postgresql://<user>:<password>@db:5432/<db>` formatında |
| `TZ` | Zaman dilimi (örn: `Europe/Istanbul`) |

> **Güvenlik:** `.env` dosyasını asla versiyon kontrolüne (Git'e) eklemeyin. Bu dosya `.gitignore` içinde listelenmektedir.

### Adım 3: TLS Sertifikası Oluşturun

Nginx'in HTTPS sunabilmesi için `nginx/certs/` dizinine self-signed sertifika gerekir:

```bash
mkdir -p nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certs/selfsigned.key \
  -out nginx/certs/selfsigned.crt \
  -subj "/CN=localhost"
```

> Üretim ortamında Let's Encrypt veya kurumsal CA sertifikası kullanmanız önerilir.

### Adım 4: Konteynerleri Başlatın

```bash
docker-compose up -d --build
```

İlk çalıştırmada Docker, Python ortamını ve bağımlılıkları indirir; PostgreSQL veritabanı ve tablolar otomatik oluşturulur. Bu işlem birkaç dakika sürebilir.

### Adım 5: Kurulumu Doğrulayın

```bash
docker-compose ps
```

Çıktıda `db`, `web` ve `nginx` servislerinin `running` (veya `Up`) durumunda olması beklenir.

---

## Sisteme Erişim

Kurulum tamamlandıktan sonra tarayıcınızda şu adresi açın:

- **HTTPS (önerilen):** `https://localhost` veya `https://<sunucu-ip>`
- Self-signed sertifika kullandığınız için tarayıcı güvenlik uyarısı gösterebilir; "Gelişmiş → Devam et" seçeneğiyle geçebilirsiniz.

> HTTP (port 80) istekleri otomatik olarak HTTPS (port 443)'e yönlendirilir.

### İlk Kullanıcı Oluşturma

Sistem ilk başlatıldığında veritabanı boştur. Admin kullanıcısı oluşturmak için `/api/register` endpoint'ine veya doğrudan veritabanına bağlanarak kayıt ekleyebilirsiniz.

Giriş yaptıktan sonra sağ üst köşedeki profil menüsünden şifrenizi hemen değiştirmeniz önerilir.

---

## Veritabanı Yönetimi

Veriler `postgres_data` adlı Docker volume'una kaydedilir. Bu volume, konteyner silinse bile yerinde kalır.

- **Volume yedeği almak için:**
  ```bash
  docker exec camasirhane_db pg_dump -U <kullanici> <veritabani> > yedek.sql
  ```
- **Yedeği geri yüklemek için:**
  ```bash
  cat yedek.sql | docker exec -i camasirhane_db psql -U <kullanici> <veritabani>
  ```

---

## Sistemi Durdurmak / Yeniden Başlatmak

```bash
# Durdur (veriler korunur)
docker-compose down

# Yeniden başlat
docker-compose up -d

# Logları izle
docker-compose logs -f web
```

---

## Sık Karşılaşılan Sorunlar

| Sorun | Çözüm |
|---|---|
| `web` servisi başlamıyor | `docker-compose logs web` ile hata mesajını inceleyin. `.env` dosyasının doğru yapılandırıldığından emin olun. |
| PostgreSQL bağlantı hatası | `db` servisi sağlıklı duruma geçmeden `web` başlamaya çalışmış olabilir. Birkaç saniye bekleyip `docker-compose restart web` deneyin. |
| Sertifika uyarısı | Normal; self-signed sertifika kullanan sistemlerde tarayıcı uyarısı beklenir. |
| Port çakışması | Başka bir uygulama 443 veya 80 portunu kullanıyorsa `nginx/nginx.conf` içindeki portları değiştirin. |
