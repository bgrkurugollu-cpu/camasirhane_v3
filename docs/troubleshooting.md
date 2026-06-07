# LaundroStar - Sorun Giderme ve Sistem Sağlık Kontrolü Rehberi

Bu rehber, LaundroStar sisteminin sağlık durumunu izlemek, olası sorunları teşhis etmek ve çözmek için kullanılacak araçları ve yöntemleri açıklar.

---

## 1. Health Check API

Sistem, kimlik doğrulama gerektirmeden erişilebilen bir sağlık kontrol uç noktası sunar.

### Endpoint

```
GET /api/health
```

**Kimlik doğrulama:** Gerekmez (public)

### Örnek Yanıt (Sağlıklı)

```json
{
  "status": "healthy",
  "timestamp": "2026-05-08T12:00:00+00:00",
  "uptime": "2sa 15dk 30sn",
  "uptime_seconds": 8130,
  "database": {
    "status": "healthy",
    "latency_ms": 1.23
  },
  "table_counts": {
    "calisanlar": 150,
    "kiyafetler": 200,
    "kirli_bekleyen": 12,
    "temiz_rafta": 45,
    "teslim_edilmis": 320,
    "kullanicilar": 3
  }
}
```

### Örnek Yanıt (Sorunlu)

```json
{
  "status": "unhealthy",
  "timestamp": "2026-05-08T12:00:00+00:00",
  "uptime": "0sa 5dk 12sn",
  "uptime_seconds": 312,
  "database": {
    "status": "unhealthy",
    "latency_ms": null,
    "error": "connection refused"
  },
  "table_counts": {}
}
```

### Yanıt Alanları

| Alan | Tip | Açıklama |
|---|---|---|
| `status` | string | Genel sistem durumu: `healthy` veya `unhealthy` |
| `timestamp` | string | Yanıtın üretildiği UTC zaman damgası |
| `uptime` | string | Uygulamanın çalışma süresi (okunabilir format) |
| `uptime_seconds` | int | Uygulamanın çalışma süresi (saniye) |
| `database.status` | string | Veritabanı bağlantı durumu: `healthy` veya `unhealthy` |
| `database.latency_ms` | float\|null | Veritabanı sorgu yanıt süresi (ms). Bağlantı yoksa `null` |
| `database.error` | string | Yalnızca sorun varsa döner; hata mesajı |
| `table_counts` | object | Tablolardaki kayıt sayıları |

### Kullanım Senaryoları

**Terminal ile hızlı kontrol:**
```bash
curl -sk https://localhost/api/health | python3 -m json.tool
```

**Sadece genel durum:**
```bash
curl -sk https://localhost/api/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])"
```

**Monitoring scriptinde kullanım:**
```bash
STATUS=$(curl -sk -o /dev/null -w "%{http_code}" https://localhost/api/health)
if [ "$STATUS" -ne 200 ]; then
  echo "ALARM: LaundroStar yanıt vermiyor! HTTP $STATUS"
fi
```

---

## 2. Docker Healthcheck

Docker Compose yapılandırmasında her servis için sağlık kontrolü tanımlıdır:

| Servis | Yöntem | Aralık | Timeout | Deneme |
|---|---|---|---|---|
| `db` (PostgreSQL) | `pg_isready` komutu | 10sn | 5sn | 5 |
| `web` (FastAPI) | `GET /api/health` | 30sn | 10sn | 3 |

### Servis Durumlarını Kontrol Etme

```bash
# Tüm servislerin durumunu görüntüle
docker compose -p camasirhane_v3 ps

# Beklenen çıktı:
# NAME                STATUS
# laundrostar_db      Up (healthy)
# laundrostar_web     Up (healthy)
# laundrostar_nginx   Up
```

### Docker Healthcheck Durumlarını Detaylı İnceleme

```bash
# Web servisinin healthcheck geçmişi
docker inspect --format='{{json .State.Health}}' laundrostar_web | python3 -m json.tool

# DB servisinin healthcheck geçmişi
docker inspect --format='{{json .State.Health}}' laundrostar_db | python3 -m json.tool
```

---

## 3. Log İnceleme

### Servis Logları

```bash
# Web servisinin loglarını izle (canlı)
docker compose -p camasirhane_v3 logs -f web

# Veritabanı logları
docker compose -p camasirhane_v3 logs -f db

# Nginx logları
docker compose -p camasirhane_v3 logs -f nginx

# Tüm servislerin logları (son 100 satır)
docker compose -p camasirhane_v3 logs --tail=100
```

### Uygulama İçi Audit Logları

Audit loglarına erişmek için admin yetkisi ve JWT token gerekir:

```bash
# Önce token al (MFA kapalı hesap için; aktifse /api/v1/auth/mfa/verify adımı gerekir)
TOKEN=$(curl -sk -X POST https://localhost/api/v1/auth/token \
  -d "username=admin&password=admin" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Audit loglarını getir
curl -sk -H "Authorization: Bearer $TOKEN" https://localhost/api/v1/audit-logs | python3 -m json.tool

# Belirli bir aksiyona göre filtrele
curl -sk -H "Authorization: Bearer $TOKEN" "https://localhost/api/audit-logs?action=LOGIN_FAIL" | python3 -m json.tool
```

---

## 4. Sık Karşılaşılan Sorunlar ve Çözümleri

### 4.1 Web Servisi Başlamıyor

**Belirtiler:** `laundrostar_web` container'ı sürekli restart ediyor veya `Exit` durumunda.

**Tanı:**
```bash
docker compose -p camasirhane_v3 logs web --tail=50
```

**Olası nedenler ve çözümler:**

| Neden | Log İpucu | Çözüm |
|---|---|---|
| `.env` dosyası eksik/hatalı | `KeyError: 'DATABASE_URL'` | `.env.example`'dan kopyalayıp değerleri doldurun |
| DB henüz hazır değil | `connection refused` | DB healthcheck'in geçmesini bekleyin: `docker compose -p camasirhane_v3 restart web` |
| Python bağımlılık hatası | `ModuleNotFoundError` | Image'ı yeniden build edin: `docker compose -p camasirhane_v3 up -d --build web` |

### 4.2 Veritabanı Bağlantı Hatası

**Belirtiler:** `/api/health` yanıtında `database.status: "unhealthy"`.

**Tanı:**
```bash
# DB container'ının durumunu kontrol et
docker compose -p camasirhane_v3 ps db

# DB'ye doğrudan bağlantı testi
docker exec laundrostar_db pg_isready -U camasirhane -d camasirhane_db
```

**Çözümler:**
```bash
# DB servisini yeniden başlat
docker compose -p camasirhane_v3 restart db

# Web servisini DB'den sonra yeniden başlat
docker compose -p camasirhane_v3 restart web
```

### 4.3 Nginx 502 Bad Gateway

**Belirtiler:** Tarayıcıda "502 Bad Gateway" hatası.

**Tanı:**
```bash
docker compose -p camasirhane_v3 logs nginx --tail=20
docker compose -p camasirhane_v3 ps web
```

**Neden:** Web servisi henüz başlamamış veya çökmüş.

**Çözüm:**
```bash
docker compose -p camasirhane_v3 restart web
# Birkaç saniye bekleyin, ardından:
curl -sk https://localhost/api/health
```

### 4.4 SSL Sertifika Hatası

**Belirtiler:** Nginx başlamıyor, logda `SSL: error` mesajı.

**Tanı:**
```bash
docker compose -p camasirhane_v3 logs nginx --tail=10
ls -la nginx/certs/
```

**Çözüm:**
```bash
# Sertifikaları yeniden oluştur
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certs/key.pem -out nginx/certs/cert.pem -subj "/CN=localhost"

# Nginx'i yeniden başlat
docker compose -p camasirhane_v3 restart nginx
```

### 4.5 Port Çakışması (80 veya 443)

**Belirtiler:** Nginx container'ı başlamıyor, `port is already allocated` hatası.

**Tanı:**
```bash
# Hangi uygulamanın portu kullandığını bul
lsof -i :80
lsof -i :443
```

**Çözüm:** Çakışan uygulamayı durdurun veya `docker-compose.yml` dosyasında portları değiştirin:
```yaml
ports:
  - "8080:80"
  - "8443:443"
```

### 4.6 Disk Alanı / Volume Sorunları

**Tanı:**
```bash
# Docker disk kullanımı
docker system df

# PostgreSQL volume boyutu
docker exec laundrostar_db du -sh /var/lib/postgresql/data
```

**Çözüm:**
```bash
# Kullanılmayan Docker kaynaklarını temizle (dikkatli kullanın)
docker system prune -f
```

---

## 5. Servisleri Yeniden Başlatma

```bash
# Tek bir servisi yeniden başlat
docker compose -p camasirhane_v3 restart web

# Tüm servisleri durdur ve başlat (veriler korunur)
docker compose -p camasirhane_v3 down
docker compose -p camasirhane_v3 up -d

# Yeniden build ile başlat (kod değişikliklerinden sonra)
docker compose -p camasirhane_v3 up -d --build
```

---

## 6. Veritabanı Yedekleme ve Geri Yükleme

```bash
# Yedek al
docker exec laundrostar_db pg_dump -U camasirhane camasirhane_db > yedek_$(date +%Y%m%d).sql

# Yedeği geri yükle
cat yedek_20260508.sql | docker exec -i laundrostar_db psql -U camasirhane camasirhane_db
```
