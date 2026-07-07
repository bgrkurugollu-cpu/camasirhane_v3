# LaundroStar — Veritabanı Şeması

> Bu doküman domain modelinin implementation-level çevirisidir. Agent bu dokümanla Alembic migration ve SQLAlchemy model üretebilir; başka referansa ihtiyaç duymaz.

---

## 1. DB Engine ve Versiyon

**Engine:** PostgreSQL 16 (Docker Compose'da `postgres:16-alpine`).

**ORM:** SQLAlchemy 2.0 (async değil; sync — Uvicorn worker thread model ile uyumlu).

**Migration:** Alembic. `Base.metadata.create_all()` kullanımı **yasaktır**; tüm şema değişiklikleri migration dosyası ile yapılır.

**Production hazırlığı:**
- Docker volume ile kalıcı depolama (`postgres_data` named volume).
- `pool_pre_ping=True` ile connection drop tespiti.
- TLS zorunluluğu v5'te (AWS RDS geçişi ile).

**Connection pool ayarları** (`app/database.py`, env'den okunur; yalnızca PostgreSQL
gibi havuzlu sürücülerde uygulanır — SQLite'ta atlanır):

| Env değişkeni | Default | Açıklama |
|---|---|---|
| `DB_POOL_SIZE` | 10 | Kalıcı havuz boyutu |
| `DB_MAX_OVERFLOW` | 20 | Havuz üstü geçici bağlantı limiti |
| `DB_POOL_TIMEOUT` | 30 | Bağlantı bekleme zaman aşımı (sn) |
| `DB_POOL_RECYCLE` | 1800 | Bağlantı geri dönüşüm süresi (sn) |

> Bu tablo, eski `topoloji.md §9` connection-pool içeriğinin güncel karşılığıdır.

---

## 2. Şemaya Genel Bakış

Toplam **7 tablo**, 3 mantıksal grup:

| Grup | Tablolar |
|------|---------|
| **Identity & Access** | `users` |
| **Laundry Operations** | `calisanlar`, `kiyafetler`, `kirli_kiyafetler`, `temiz_kiyafetler`, `teslim_edilenler` |
| **Observability** | `audit_logs` |

Tek PostgreSQL database, tek schema (`public`). Multi-tenant yoktur.

---

## 3. Standart Alanlar

Aşağıdaki alanlar `users` hariç tüm operasyonel tablolarda bulunur:

```sql
created_at         TIMESTAMPTZ    NOT NULL   DEFAULT NOW()
created_by_user_id UUID           NULL       FK users(id) ON DELETE SET NULL
```

`users` tablosunda ek olarak:
```sql
updated_at         TIMESTAMPTZ    NOT NULL   DEFAULT NOW()
-- BEFORE UPDATE trigger ile otomatik güncellenir
```

**`updated_at` trigger:**
```sql
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

**İstisnalar:**
- `audit_logs` — `updated_at` **yoktur** (append-only; update yasak).
- `teslim_edilenler` — `updated_at` yoktur (immutable geçmiş kaydı).

---

## 4. Soft Delete Stratejisi

| Pattern | Uygulandığı tablolar | Açıklama |
|---------|---------------------|----------|
| `is_active` bayrağı | `users` | Pasifleştirme; silme yok |
| Hard delete | `kiyafetler` | RFID kaydı kaldırılabilir (referans kontrolü sonrası) |
| Implicit (akış ile) | `kirli_kiyafetler`, `temiz_kiyafetler` | Onay/teslim sırasında silinir → hedefe aktarılır |
| Append-only | `teslim_edilenler`, `audit_logs` | Silinmez; retention job ile temizlenir (v5) |

---

## 5. Tablo Tanımları

### 5.1 `users`

Platform kullanıcılarını tutar. Admin ve görevli (user) rolleri bu tabloda ayrışır.

**Kolonlar:**

| Kolon | Tip | Null | Default | Kısıt | Açıklama |
|-------|-----|------|---------|-------|----------|
| id | UUID | No | gen_random_uuid() | PK | — |
| username | VARCHAR(50) | No | — | UNIQUE | Değiştirilemez |
| hashed_password | VARCHAR(60) | No | — | — | bcrypt cost 12 |
| role | VARCHAR(10) | No | 'user' | CHECK IN ('admin','user') | — |
| email | VARCHAR(255) | Yes | — | — | — |
| phone | VARCHAR(20) | Yes | — | — | — |
| title | VARCHAR(100) | Yes | — | — | Unvan |
| company | VARCHAR(100) | Yes | — | — | — |
| is_active | BOOLEAN | No | true | — | Soft-disable |
| failed_login_count | INTEGER | No | 0 | CHECK >= 0 | Lockout tetikleyicisi |
| locked_until | TIMESTAMPTZ | Yes | — | — | Null → kilit yok |
| created_at | TIMESTAMPTZ | No | NOW() | — | — |
| updated_at | TIMESTAMPTZ | No | NOW() | — | Trigger ile güncellenir |
| created_by_user_id | UUID | Yes | — | FK users(id) SET NULL | Seed için null |

**Index'ler:**
- `users_username_key` UNIQUE btree (username)
- `users_is_active_idx` btree (is_active) WHERE is_active = true

**Business rule enforcement:**
- `role` değeri yalnızca `admin` veya `user`: CHECK constraint.
- `failed_login_count >= 0`: CHECK constraint.
- Manager lock: son admin pasifleştirilemez → service-layer kontrol.

**Seed ihtiyacı: VAR.** `admin` kullanıcısı boot-time'da env'den (`ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`) seed edilir.

> **Uygulama notu:** Uygulanan sürümde env tabanlı boot-time seed yerine **UI tabanlı ilk kurulum (bootstrap)** akışı vardır: sistemde hiç kullanıcı yokken arayüz "İlk Kurulum" ekranını gösterir ve ilk kullanıcı buradan oluşturulur (bkz. 03_API_CONTRACTS.md §3.1.2 ve 07_SCREEN_CATALOG.md S-SETUP).

---

### 5.2 `calisanlar`

Fabrika/tesis personelini tutar. Platform kullanıcısı değil, kıyafet sahibidir.

**Kolonlar:**

| Kolon | Tip | Null | Default | Kısıt | Açıklama |
|-------|-----|------|---------|-------|----------|
| sicil_numarasi | VARCHAR(20) | No | — | PK | Değiştirilemez |
| ad | VARCHAR(100) | No | — | — | — |
| soyad | VARCHAR(100) | No | — | — | — |
| cinsiyet | CHAR(1) | Yes | — | CHECK IN ('K','E') OR NULL | K=Kadın, E=Erkek |
| created_at | TIMESTAMPTZ | No | NOW() | — | — |
| created_by_user_id | UUID | Yes | — | FK users(id) SET NULL | — |

**Index'ler:**
- `calisanlar_ad_soyad_idx` btree (ad, soyad) — arama için

**Business rule enforcement:**
- `cinsiyet` yalnızca `K` veya `E` veya NULL: CHECK constraint.
- Hard delete yoktur (service-layer engeller).

**Seed ihtiyacı:** Opsiyonel dev seed (örnek personel).

---

### 5.3 `kiyafetler`

RFID tag → sicil numarası eşleştirmesini tutar.

**Kolonlar:**

| Kolon | Tip | Null | Default | Kısıt | Açıklama |
|-------|-----|------|---------|-------|----------|
| rfid_tag | VARCHAR(50) | No | — | PK | RFID okuyucudan gelen değer |
| sicil_numarasi | VARCHAR(20) | No | — | FK calisanlar(sicil_numarasi) RESTRICT | — |
| created_at | TIMESTAMPTZ | No | NOW() | — | — |
| created_by_user_id | UUID | Yes | — | FK users(id) SET NULL | — |

**Index'ler:**
- `kiyafetler_sicil_idx` btree (sicil_numarasi) — personelin tüm kıyafetleri

**Business rule enforcement:**
- Aynı `rfid_tag` tek `sicil_numarasi`'na bağlanabilir: PK ile sağlanır.
- Silme öncesi açık KirliKiyafet veya TemizKiyafet kontrolü: service-layer.

---

### 5.4 `kirli_kiyafetler`

Kirli bekleyen kıyafetlerin aktif kuyruğu. Onaylandığında silinir.

**Kolonlar:**

| Kolon | Tip | Null | Default | Kısıt | Açıklama |
|-------|-----|------|---------|-------|----------|
| id | SERIAL | No | — | PK | — |
| rfid_tag | VARCHAR(50) | Yes | — | — | RFID okutulduysa dolu |
| sicil_numarasi | VARCHAR(20) | Yes | — | — | — |
| zaman_damgasi | TIMESTAMPTZ | No | NOW() | — | Giriş zamanı |
| created_by_user_id | UUID | Yes | — | FK users(id) SET NULL | — |

**Index'ler:**
- `kirli_sicil_idx` btree (sicil_numarasi) — kişi bazlı filtre
- `kirli_zaman_idx` btree (zaman_damgasi DESC) — sıralama

---

### 5.5 `temiz_kiyafetler`

Yıkanmış ve rafa yerleştirilmiş kıyafetlerin aktif listesi. Teslim edildiğinde silinir.

**Kolonlar:**

| Kolon | Tip | Null | Default | Kısıt | Açıklama |
|-------|-----|------|---------|-------|----------|
| id | SERIAL | No | — | PK | — |
| rfid_tag | VARCHAR(50) | Yes | — | — | — |
| sicil_numarasi | VARCHAR(20) | Yes | — | — | — |
| zaman_damgasi | TIMESTAMPTZ | No | NOW() | — | Temizleme zamanı |
| raf_id | VARCHAR(5) | Yes | — | — | Örn. "A11" |
| created_by_user_id | UUID | Yes | — | FK users(id) SET NULL | — |

**Index'ler:**
- `temiz_raf_idx` btree (raf_id) WHERE raf_id IS NOT NULL — doluluk sorgusu için kritik
- `temiz_sicil_idx` btree (sicil_numarasi)

---

### 5.6 `teslim_edilenler`

Teslim edilmiş kıyafetlerin kalıcı geçmiş kaydı. Silinmez.

**Kolonlar:**

| Kolon | Tip | Null | Default | Kısıt | Açıklama |
|-------|-----|------|---------|-------|----------|
| id | SERIAL | No | — | PK | — |
| rfid_tag | VARCHAR(50) | Yes | — | — | — |
| sicil_numarasi | VARCHAR(20) | Yes | — | — | — |
| zaman_damgasi | TIMESTAMPTZ | No | NOW() | — | Teslim zamanı |
| raf_id | VARCHAR(5) | Yes | — | — | Hangi raftan teslim |
| created_by_user_id | UUID | Yes | — | FK users(id) SET NULL | — |

**Index'ler:**
- `teslim_zaman_idx` btree (zaman_damgasi DESC) — istatistik sorguları
- `teslim_sicil_idx` btree (sicil_numarasi)

---

### 5.7 `audit_logs`

Tüm kritik işlemlerin denetim kaydı. Append-only; güncelleme ve silme yoktur.

**Kolonlar:**

| Kolon | Tip | Null | Default | Kısıt | Açıklama |
|-------|-----|------|---------|-------|----------|
| id | SERIAL | No | — | PK | — |
| timestamp | TIMESTAMPTZ | No | NOW() | — | UTC zaman damgası |
| username | VARCHAR(50) | Yes | — | — | İşlemi yapan (null=sistem) |
| action | VARCHAR(50) | No | — | — | Aksiyon kodu (bkz. [[02_DOMAIN_MODEL#4-audit-action-kodlari]]) |
| detail | TEXT | Yes | — | — | Ek bilgi |
| ip_hash | VARCHAR(64) | Yes | — | — | SHA-256(IP); plaintext yok |
| status | VARCHAR(10) | No | 'success' | CHECK IN ('success','fail') | — |

**Index'ler:**
- `audit_timestamp_idx` btree (timestamp DESC) — listeleme
- `audit_username_idx` btree (username) — kullanıcı filtresi
- `audit_action_idx` btree (action) — aksiyon filtresi

**Append-only koruması:**
```sql
CREATE RULE no_update_audit AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;
CREATE RULE no_delete_audit AS ON DELETE TO audit_logs DO INSTEAD NOTHING;
```

---

## 6. Migration Stratejisi (Alembic)

### 6.1 Yapı

```
apps/api/
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_initial_schema.py
│       ├── 0002_add_ip_hash_to_audit_logs.py
│       └── ...
├── alembic.ini
```

### 6.2 Kurallar

- `Base.metadata.create_all()` yalnızca test ortamında (`TEST_MODE=true`) izinlidir; production ve staging'de yasaktır.
- Her migration dosyası tek bir mantıksal değişiklik içerir.
- `upgrade()` ve `downgrade()` her ikisi de dolu olmalıdır.
- Migration dosyası adı: `<4_digit_sequence>_<short_description>.py`
- Yeni kolon eklemek: önce nullable, sonra backfill, sonra NOT NULL (üç ayrı migration).

### 6.3 Uygulama Başlangıcında Migration

```python
# main.py bootstrap bölümü
from alembic.config import Config
from alembic import command

def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
```

Uygulama başlamadan önce `alembic upgrade head` çalışır; schema güncel değilse deployment fail olur.

---

## 7. Bağlantı Konfigürasyonu

```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`pool_size` ve `max_overflow` env'den okunabilir; default değerler bu ölçekte yeterlidir.
