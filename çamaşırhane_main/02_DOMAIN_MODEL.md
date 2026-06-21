# LaundroStar — Domain Modeli

> Bu doküman platformun iş-diline ait kavram haritasıdır: hangi nesneler var, birbirleriyle nasıl ilişkili, yaşam döngüleri nedir, hangi kurallar her zaman geçerli olmalıdır. Veritabanı şeması veya API'den önce okunur; kodu açmadan önce iş anlaşılmalıdır.

---

## 1. Domain'e Genel Bakış

LaundroStar'ın domain'i üç alt-domain'e gruplanır:

**Identity & Access.** Sisteme giriş yapan kullanıcıları (User), rollerini (admin/user) ve oturum bilgilerini tutar. Kimlik doğrulama ve yetkilendirme bu alt-domain'in sorumluluğundadır.

**Laundry Operations.** Tesisteki personeli (Calisan), her personele zimmetlenen kıyafetlerin RFID etiketlerini (Kiyafet) ve kıyafetin anlık durumunu (KirliKiyafet / TemizKiyafet / TeslimEdilen) tutar. Raf atama algoritması bu alt-domain'in iş kuralıdır.

**Observability.** Tüm kritik işlemlerin denetim kaydını (AuditLog) tutar. Diğer iki alt-domain'den gelen aksiyonları izler; bağımsız olarak bir şey üretmez.

Alt-domain'ler arası temel akış: **User** login olur → yetkisine göre **Calisan**'a ait **Kiyafet**'i işleme koyar → Kıyafet **KirliKiyafet** → **TemizKiyafet** → **TeslimEdilen** döngüsünden geçer → Her aksiyon **AuditLog**'a yazılır.

---

## 2. Ana Entity'ler

### 2.1 User (Platform Kullanıcısı)

Sisteme giriş yapan fiziksel kişi. İki rolden birine sahiptir: `admin` veya `user`.

**Sorumluluğu:**
- Platform operasyonlarını yürüten veya yöneten kişiyi temsil eder.
- Kimliğini `username` ile taşır; sistem genelinde unique.
- `admin` rolü tüm ekranlara ve aksiyonlara erişir. `user` rolü operasyonel işlemlere (onay, teslim) erişir; **kirli giriş** (tek RFID girişi ve sepet simülasyonu) yalnızca `admin` yetkisindedir.

**Ana attribute'lar:**

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| id | UUID | Evet | PK, sistem tarafından üretilir |
| username | VARCHAR(50) | Evet | Unique, değiştirilemez |
| hashed_password | VARCHAR(60) | Evet | bcrypt hash (cost 12) |
| role | ENUM | Evet | `admin` / `user` |
| email | VARCHAR(255) | Hayır | Kullanıcı profilinde gösterilir |
| phone | VARCHAR(20) | Hayır | — |
| title | VARCHAR(100) | Hayır | Unvan (örn. "Görevli") |
| company | VARCHAR(100) | Hayır | Şirket adı |
| is_active | BOOLEAN | Evet | Soft-disable bayrağı; default true |
| failed_login_count | INTEGER | Evet | Lockout tetikleyicisi; default 0 |
| locked_until | TIMESTAMPTZ | Hayır | Null ise kilit yok |
| created_at | TIMESTAMPTZ | Evet | — |
| updated_at | TIMESTAMPTZ | Evet | Trigger ile otomatik |

**İlişkiler:**
- ← AuditLog (1-N): yaptığı işlemlerin audit kaydı

**Yaşam döngüsü:** `ACTIVE` ↔ `PASSIVE` (is_active bayrağı). Silme: admin başka bir admin tarafından silinebilir; kendi hesabını silemez. Detay: [[#52-user-lifecycle]].

**Değişmezler:**
- `username` bir kez atandıktan sonra değiştirilemez.
- Kullanıcı kendi rolünü değiştiremez.
- Sistemde en az bir aktif admin bulunmalıdır; son admin silinemez.
- 5 başarısız login → `locked_until = NOW() + 15 dakika`; kilit süresi dolmadan giriş yapılamaz.

---

### 2.2 Calisan (Personel)

Çamaşırhanede kıyafet zimmetlenen fabrika personeli. Platform kullanıcısı değildir — kıyafet takibinin konusudur.

**Sorumluluğu:**
- Her çalışanı sicil numarasıyla benzersiz olarak tanımlar.
- Cinsiyeti raf atama algoritmasını belirler.
- Birden fazla RFID tag'e sahip olabilir (birden fazla kıyafet).

**Ana attribute'lar:**

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| sicil_numarasi | VARCHAR(20) | Evet | PK; fabrika sicil no'su |
| ad | VARCHAR(100) | Evet | — |
| soyad | VARCHAR(100) | Evet | — |
| cinsiyet | CHAR(1) | Hayır | `K` (Kadın) veya `E` (Erkek); null ise erkek rafına atanır |

**İlişkiler:**
- ← Kiyafet (1-N): zimmetlenen kıyafetler
- ← KirliKiyafet (1-N via sicil_numarasi)
- ← TemizKiyafet (1-N via sicil_numarasi)
- ← TeslimEdilen (1-N via sicil_numarasi)

**Değişmezler:**
- `sicil_numarasi` bir kez atandıktan sonra değiştirilemez.
- Silme yoktur; Calisan hard-delete ile kaldırılamaz (zimmet geçmişi bütünlüğü için).
- Cinsiyeti null olan Calisan'lar raf atamasında erkek rafı kuralına tabi tutulur.

---

### 2.3 Kiyafet (RFID-Kıyafet Kaydı)

Bir RFID etiketinin tek bir personele zimmetlendiğini temsil eden kayıt. "Kıyafet" kelimesi burada RFID-personel bağını ifade eder; fiziksel kıyafetin markası veya bedeni bu domaine ait değildir.

**Sorumluluğu:**
- RFID tag → Calisan eşleştirmesini tutar.
- Kirli giriş sırasında `rfid_tag` üzerinden hangi personelin kıyafetinin sisteme alındığı belirlenir.

**Ana attribute'lar:**

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| rfid_tag | VARCHAR(50) | Evet | PK; RFID okuyucudan gelen etiket değeri |
| sicil_numarasi | VARCHAR(20) | Evet | FK → calisanlar.sicil_numarasi |
| created_at | TIMESTAMPTZ | Evet | Eşleştirme tarihi |

**İlişkiler:**
- → Calisan (N-1)

**Değişmezler:**
- Bir `rfid_tag` yalnızca bir `sicil_numarasi`'na bağlı olabilir.
- Kiyafet kaydı silinebilir (admin yetkisi gerektirir); silme öncesi o tag'e ait açık KirliKiyafet veya TemizKiyafet kaydı varsa işlem reddedilir. (Bu kontrol service katmanında uygulanır.)

---

### 2.4 KirliKiyafet (Kirli Bekleyen)

Kirli olarak sisteme alınmış ve yıkama bekleme kuyruğunda olan kıyafet kaydı.

**Sorumluluğu:**
- Kirli girişi anında oluşturulur.
- Yıkama onaylandığında bu tablodan silinir ve TemizKiyafet'e aktarılır.
- Aktif kuyruk görevi görür: bu tabloda ne kadar kayıt varsa, o kadar kıyafet beklemede demektir.

**Ana attribute'lar:**

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| id | INTEGER | Evet | PK, auto-increment |
| rfid_tag | VARCHAR(50) | Hayır | Okutulabilen kıyafetlerde dolu; manuel kayıtta null olabilir |
| sicil_numarasi | VARCHAR(20) | Hayır | — |
| zaman_damgasi | TIMESTAMPTZ | Evet | Kirli girişinin zamanı |
| created_by_user_id | UUID | Hayır | İşlemi yapan User FK |

**Değişmezler:**
- Tamamlanan (onaylanan) kayıt bu tablodan silinir; güncellenmez.
- Aynı `rfid_tag` için birden fazla açık KirliKiyafet kaydı olmamalıdır (service katmanı kontrol eder).

---

### 2.5 TemizKiyafet (Temiz / Rafta)

Yıkanmış ve rafa yerleştirilmiş kıyafet kaydı.

**Sorumluluğu:**
- Onaylanan kirli kayıttan oluşturulur.
- Otomatik raf ataması bu noktada gerçekleşir.
- Teslim edildiğinde bu tablodan silinir ve TeslimEdilen'e aktarılır.

**Ana attribute'lar:**

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| id | INTEGER | Evet | PK, auto-increment |
| rfid_tag | VARCHAR(50) | Hayır | — |
| sicil_numarasi | VARCHAR(20) | Hayır | — |
| zaman_damgasi | TIMESTAMPTZ | Evet | Temiz onayının zamanı |
| raf_id | VARCHAR(5) | Hayır | Örn. "A11", "E35"; atama başarısız olursa null |
| created_by_user_id | UUID | Hayır | İşlemi yapan User FK |

**Değişmezler:**
- `raf_id` bir kez atandıktan sonra değiştirilemez (manuel raf düzeltme v5+).
- Teslim edilen kayıt bu tablodan silinir; güncellenmez.
- Teslim sırasında `sicil_numarasi` eşleşmesi zorunludur (başka personele teslim engeli).

---

### 2.6 TeslimEdilen (Teslim Geçmişi)

Personele teslim edilmiş kıyafetlerin kalıcı geçmiş kaydı.

**Sorumluluğu:**
- Teslim anında oluşturulur; silinmez.
- Döngünün kapanma kanıtıdır.
- Dashboard ve istatistik sorgularında kullanılır.

**Ana attribute'lar:**

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| id | INTEGER | Evet | PK, auto-increment |
| rfid_tag | VARCHAR(50) | Hayır | — |
| sicil_numarasi | VARCHAR(20) | Hayır | — |
| zaman_damgasi | TIMESTAMPTZ | Evet | Teslim zamanı |
| raf_id | VARCHAR(5) | Hayır | Hangi raftan teslim edildiği |
| created_by_user_id | UUID | Hayır | İşlemi yapan User FK |

**Değişmezler:**
- Hard delete **yoktur**; yalnızca retention job (6 ay) ile temizlenir (v5).
- Güncelleme yoktur; append-only kayıt.

---

### 2.7 AuditLog (Denetim Kaydı)

Sistemdeki tüm kritik işlemlerin kim tarafından, ne zaman, hangi IP'den yapıldığını ve sonucunu tutan kayıt.

**Sorumluluğu:**
- Operasyonel traceability sağlar (kıyafetin başına ne geldi?).
- Güvenlik olaylarını kayıt altına alır (başarısız login, yetkisiz erişim).
- Append-only; güncelleme ve silme yoktur.

**Ana attribute'lar:**

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| id | INTEGER | Evet | PK, auto-increment |
| timestamp | TIMESTAMPTZ | Evet | UTC zaman damgası |
| username | VARCHAR(50) | Hayır | İşlemi yapan kullanıcı adı (null: sistem olayı) |
| action | VARCHAR(50) | Evet | Standart aksiyon kodu (bkz. [[#4-audit-action-kodlari]]) |
| detail | TEXT | Hayır | Ek bilgi (RFID, sicil no, hedef kullanıcı) |
| ip_hash | VARCHAR(64) | Hayır | SHA-256(IP); plaintext IP saklanmaz |
| status | VARCHAR(10) | Evet | `success` veya `fail` |

**Değişmezler:**
- UPDATE ve DELETE çalışmaz (append-only trigger ile korunur).
- `ip_hash` alanında plaintext IP asla tutulmaz — KVKK uyumu.

---

## 3. Kıyafet Yaşam Döngüsü (State Machine)

```
[Kayıt Dışı]
     │
     │ RFID Eşleştirme (admin)
     ▼
[Zimmetli / Stokta]
     │
     │ Kirli Giriş (admin)
     ▼
[KirliKiyafet — BEKLEMEDE]
     │
     │ Yıkama Onayı (user/admin)
     ▼
[TemizKiyafet — RAFTA]
     │
     │ Personele Teslim (user/admin)
     ▼
[TeslimEdilen — DÖNGÜ TAMAMLANDI]
     │
     │ Bir sonraki kirli giriş
     └──────────────────────────▶ [KirliKiyafet — BEKLEMEDE]
```

**Geçiş kuralları:**

| Geçiş | Tetikleyen aksiyon | Kaynak tablo | Hedef tablo | Yan etki |
|-------|-------------------|--------------|-------------|----------|
| Zimmetli → Beklemede | `POST /api/v1/islem/kirli-giris` | — | kirli_kiyafetler | AuditLog: KIRLI_GIRIS |
| Beklemede → Rafta | `POST /api/v1/islem/onayla` | kirli_kiyafetler | temiz_kiyafetler | Raf ataması; AuditLog: TEMIZ_ONAY |
| Rafta → Teslim | `POST /api/v1/islem/teslim` | temiz_kiyafetler | teslim_edilenler | AuditLog: TESLIM |

**Terminal durum yoktur** — TeslimEdilen kaydı oluştuktan sonra aynı RFID tag yeni bir Kirli girişine konu olabilir. Döngü açık uçludur.

---

## 4. Audit Action Kodları

Tüm `AuditLog.action` değerleri bu listeden alınır. Kod dışında yeni aksiyon eklenemez.

| Kod | Tetikleyen | Açıklama |
|-----|-----------|----------|
| `LOGIN_SUCCESS` | Auth | Başarılı giriş |
| `LOGIN_FAIL` | Auth | Başarısız giriş (hatalı şifre veya kullanıcı) |
| `LOGIN_LOCKED` | Auth | Kilit devreye girdi |
| `LOGOUT` | Auth | Çıkış |
| `TOKEN_REFRESH` | Auth | Access token yenilendi |
| `PASSWORD_CHANGED` | Auth | Şifre değiştirildi |
| `USER_CREATE` | Admin | Yeni kullanıcı oluşturuldu |
| `USER_UPDATE` | Admin | Kullanıcı güncellendi |
| `USER_DELETE` | Admin | Kullanıcı silindi |
| `PROFILE_UPDATE` | User | Kendi profil bilgisi güncellendi |
| `RFID_REGISTER` | Admin | Yeni RFID eşleştirmesi |
| `RFID_UPDATE` | Admin | RFID eşleştirmesi güncellendi |
| `RFID_DELETE` | Admin | RFID eşleştirmesi silindi |
| `CALISAN_CREATE` | Admin | Yeni personel kaydı |
| `KIRLI_GIRIS` | Admin | Kıyafet kirli sepetine alındı |
| `SEPET_SIMULASYON` | Admin | Sepet simülasyonu (toplu kirli giriş) |
| `TEMIZ_ONAY` | User/Admin | Kıyafet temiz onaylandı ve rafa atandı |
| `TESLIM` | User/Admin | Kıyafet personele teslim edildi |
| `UNAUTHORIZED_ACCESS` | System | Yetkisiz erişim girişimi |

---

## 5. Raf Atama İş Kuralı

### 5.1 Raf Yapısı

```
Raflar:  A  B  C  D  E  F  G  H    (8 raf)
Katlar:  1  2  3  4  5  6  7       (7 kat)
Bölmeler: 1  2  3  4  5            (5 bölme per kat)
```

**Toplam:** 8 × 7 × 5 = 280 göz

**Raf ID formatı:** `<Harf><Kat><Bölme>` → Örnek: `A11`, `E35`, `H72`

### 5.2 Kapasite Kuralı

| Kat | Kapasite (göz başına max kıyafet) |
|-----|-----------------------------------|
| 1–6 | 3 |
| 7 (en üst) | 1 |

### 5.3 Cinsiyet Bazlı Atama

| Personel cinsiyeti | Atanabilir raflar |
|---------------------|------------------|
| `K` (Kadın) | Yalnızca **E** rafı |
| `E` (Erkek) veya `null` | A, B, C, D, F, G, H (E hariç tümü) |

### 5.4 Atama Algoritması

1. Personelin cinsiyetine göre uygun raf harfleri belirlenir.
2. Uygun harfler alfabetik sırayla, her harfte 1→7 kat sıralamasıyla, her katta 1→5 bölme sıralamasıyla taranır.
3. `temiz_kiyafetler` tablosundaki mevcut doluluk sayımına göre ilk uygun boşluk seçilir.
4. Hiçbir uygun göz bulunamazsa `HTTP 409 SHELF_FULL` hatası döner.

**Değişmezler:**
- Kadın personelin kıyafeti E dışındaki rafa atanamaz.
- Erkek personelin kıyafeti E rafına atanamaz.
- Kapasite aşımı yapılamaz (service katmanı kontrol eder).

---

## 6. User Lifecycle

```
ACTIVE ──────────► PASSIVE
  ▲                   │
  └───────────────────┘
  (admin reactivate)

ACTIVE: is_active = true
PASSIVE: is_active = false (login yapamaz)
```

**Kural:** Sistemde her zaman en az 1 `ACTIVE` admin bulunmalıdır. Son admin pasifleştirilemez.

---

## 7. Veri Sahipliği ve Gizlilik

- `AuditLog.ip_hash`: Kişisel veri sayılan IP adresi hash'lenerek (SHA-256) saklanır. Orijinal IP tutulmaz.
- `Calisan` tablosu: Ad, soyad, sicil bilgileri kişisel veri kapsamındadır. v4'te plaintext saklanır (şifreleme v5 planında). Erişim yalnızca kimlik doğrulama sonrası yapılır.
- `User.hashed_password`: bcrypt ile tek yönlü hash; plaintext asla saklanmaz.

Detaylı güvenlik uygulaması: [[08_SECURITY_IMPLEMENTATION]].
