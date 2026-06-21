# LaundroStar — Ekran Kataloğu

> Tüm ekranların alan tanımları, buton davranışları ve kullanıcı akışları. Ekran sırası navigasyon menüsündeki sırayı yansıtır.

---

## Ekran Haritası

| Ekran ID | Ekran Adı | Erişim | Navigasyon Hedefi |
|----------|-----------|--------|-------------------|
| S-LOGIN | Giriş | Herkese açık | `/login` modal |
| S-DASHBOARD | Dashboard | user + admin | `dashboard` |
| S-KIRLI-GIRIS | Kirli Kıyafet Girişi | user + admin | `kirli-giris` |
| S-TABLO-KIRLI | Kirli Bekleyenler | user + admin | `tablo-kirli` |
| S-TABLO-TEMIZ | Temiz Kıyafetler | user + admin | `tablo-temiz` |
| S-TABLO-TESLIM | Teslim Edilenler | admin | `tablo-teslim` |
| S-RAF-SIM | Raf Simülasyonu | user + admin | `raf-simulasyon` |
| S-RFID | RFID Eşleştirme | admin | `rfid-eslestirme` |
| S-KIYAFET-LIST | Kıyafet Listesi | admin | `tablo-kiyafet` |
| S-AUDIT | Audit Loglar | admin | `audit-logs` |
| S-KULLANICI | Kullanıcı Yönetimi | admin | `kullanici-yonetimi` |
| S-PROFIL | Profil / Ayarlar | user + admin | `profil` |

---

## S-LOGIN — Giriş Ekranı

**Tip:** Modal overlay (sayfa yüklenir, token yoksa modal açılır).
**Erişim:** Herkese açık.

**Alanlar:**

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| Kullanıcı adı | Text input | Evet | `username` |
| Şifre | Password input | Evet | `password` |

**Butonlar:**
- **Giriş Yap** — `POST /api/v1/auth/login` çağrısı; başarıda `AppState.setSession()` ve dashboard'a yönlendirme.

**Hata durumları:**
- `AUTH_INVALID_CREDENTIALS` → "Kullanıcı adı veya şifre hatalı." toast
- `AUTH_ACCOUNT_LOCKED` → "Hesabınız kilitlendi. {unlocks_at} tarihinde açılacak." toast

**Davranış:**
- Enter tuşu form submit'i tetikler.
- Şifre alanı gözden geçirme ikonu ile toggle edilebilir.
- Modal kapama (ESC/dış tık) → kapatılmaz; oturum açmadan geçilemez.

---

## S-DASHBOARD — Ana Panel

**Tip:** Tam sayfa.
**Erişim:** user + admin.

**Bölümler:**

### Özet Kartlar (üst bant)

| Kart | Değer | Kaynak |
|------|-------|--------|
| Kirli Bekleyen | `kirli_bugun` | `GET /api/v1/stats` |
| Temiz / Rafta | `temiz_bugun` | — |
| Bugün Teslim | `teslim_bugun` | — |

Kartlar sayfa açılışında ve 5 dakikada bir otomatik yenilenir.

### Geçmiş Grafik

- Chart.js bar chart; X ekseni tarih etiketi, Y ekseni işlem sayısı.
- 3 dataset: Kirli (kırmızı), Temiz (yeşil), Teslim (mavi).
- Periyot seçici: **Haftalık** / **Aylık** buton grubu.
- Kaynak: `GET /api/v1/stats/gecmis?period=weekly|monthly`
- Periyot değiştiğinde grafik yenilenir; eski instance yok edilir (`chart.destroy()`).

**Butonlar:**
- Haftalık / Aylık — periyot toggle.

---

## S-KIRLI-GIRIS — Kirli Kıyafet Girişi

**Tip:** Aksiyon view (test/operasyon amaçlı).
**Erişim:** yalnızca admin. Ekran, sidebar'da değil; sağ üstteki kullanıcı menüsünde admin'e özel **"Test Ekranları"** sekmesinden açılır. Personel ne arayüzde ne de API'de bu işleme erişebilir (backend `require_admin` ile 403 döner).

**Bölüm 1: Sepet Simülasyonu**

- **"Sepeti Oku" butonu** → `POST /api/v1/islem/sepet-simulasyon`
  - Başarıda: eklenen kıyafetlerin listesi tabloda gösterilir (rfid_tag, sicil, ad_soyad, cinsiyet, zaman).
  - `durum: "bos"` ise: "Kirli sepetinde yeni kıyafet bulunamadı!" uyarısı.
  - Kalan aday sayısı mesajı: "{kalan_aday} kişi daha beklemede."

**Bölüm 2: Manuel RFID Girişi**

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| RFID Tag | Text input | Evet | El ile veya RFID okuyucudan |

**Butonlar:**
- **Kaydet** → `POST /api/v1/islem/kirli-giris` ile `rfid_tag` gönderilir.
  - Başarıda: yeşil toast + form temizleme.
  - `ISLEM_RFID_NOT_REGISTERED` → "Bu RFID tag kayıtlı değil. Önce eşleştirin." toast.

---

## S-TABLO-KIRLI — Kirli Bekleyenler

**Tip:** Tablo view.
**Erişim:** user + admin.

**Tablo kolonları:**

| Kolon | Kaynak alan |
|-------|------------|
| # (İşlem ID) | `id` |
| RFID Tag | `rfid_tag` |
| Sicil No | `sicil_numarasi` |
| Ad Soyad | `ad_soyad` |
| Giriş Zamanı | `zaman_damgasi` (format: GG.AA.YYYY SS:DD) |
| İşlem | Aksiyon butonu |

**Arama:** Metin arama (rfid, sicil, ad_soyad); debounce 300ms.

**Butonlar (her satırda):**
- **Temizlendi / Onayla** → Onay dialog'u ("Bu kıyafeti temiz olarak işaretlemek istiyor musunuz?") → `POST /api/v1/islem/onayla` ile `id`.
  - Başarıda: satır listeden kalkar; "Kıyafet rafa yerleştirildi: {raf_id}" toast.
  - `ISLEM_SHELF_FULL` → "Raflar dolu! Uygun bölme bulunamadı." toast.

**Sayfalama:** offset-based; 50 kayıt/sayfa.

---

## S-TABLO-TEMIZ — Temiz Kıyafetler

**Tip:** Tablo view.
**Erişim:** user + admin.

**Tablo kolonları:**

| Kolon | Kaynak alan |
|-------|------------|
| # | `id` |
| RFID Tag | `rfid_tag` |
| Sicil No | `sicil_numarasi` |
| Ad Soyad | `ad_soyad` |
| Raf Konumu | `raf_id` |
| Onay Zamanı | `zaman_damgasi` |
| İşlem | Aksiyon butonu |

**Teslim akışı (her satırda):**
- **Teslim Et** butonu → Sicil doğrulama dialog'u açılır.
  - Dialog alanı: Sicil No (text input, zorunlu).
  - Onay → `POST /api/v1/islem/teslim` ile `{ id, sicil_numarasi }`.
  - Başarıda: satır kalkar; "Teslim edildi." toast.
  - `ISLEM_SICIL_MISMATCH` → "Sicil numarası eşleşmiyor!" hata toast.

---

## S-TABLO-TESLIM — Teslim Edilenler

**Tip:** Tablo view (salt okunur).
**Erişim:** admin.

**Tablo kolonları:**

| Kolon | Kaynak alan |
|-------|------------|
| # | `id` |
| RFID Tag | `rfid_tag` |
| Sicil No | `sicil_numarasi` |
| Ad Soyad | `ad_soyad` |
| Raf | `raf_id` |
| Teslim Zamanı | `zaman_damgasi` |

Arama ve sayfalama aktif. Aksiyon butonu yoktur (salt okunur geçmiş).

---

## S-RAF-SIM — Raf Simülasyonu

**Tip:** Özel interaktif görünüm.
**Erişim:** user + admin.

**Raf seçici:** A-H buton grubu; tıklandığında `GET /api/v1/stats/raf-detay/{rack_letter}` çağrılır.

**7×5 Izgarası:**

Her hücre bir raf bölmesini temsil eder. Renk kodu:
- Boş (yeşil arka plan)
- Kısmi dolu (sarı)
- Tam dolu (kırmızı)

Her hücre üzerine gelindiğinde (`hover`) o bölmedeki kıyafet listesi tooltip/popup olarak gösterilir:
```
E35 → Ahmet Yılmaz (1001), Ayşe Kaya (1002)
```

**Raf doluluk özeti:** Seçili raf için: Toplam göz / Dolu göz / Boş göz.

**Arama:** Sicil veya ad soyad ile arama; sonuç bulunan hücreye highlight + scroll.

---

## S-RFID — RFID Eşleştirme

**Tip:** Aksiyon view + tablo.
**Erişim:** admin.

**Form alanları (yeni eşleştirme):**

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| RFID Tag | Text | Evet | Yeni veya mevcut tag |
| Sicil No | Text | Evet | — |
| Ad | Text | Koşullu | Yeni personel oluşturulacaksa zorunlu |
| Soyad | Text | Koşullu | — |
| Cinsiyet | Select (K/E/Belirtilmemiş) | Hayır | — |

**Sicil arama davranışı:**
- Sicil alanına yazıldığında `GET /api/v1/calisanlar/{sicil}` çağrılır.
- Personel bulunursa ad/soyad/cinsiyet alanları otomatik doldurulur ve readonly yapılır.
- Personel bulunamazsa alanlar boş ve editable kalır (yeni personel oluşturulacak).

**Butonlar:**
- **Kaydet** → `POST /api/v1/kiyafetler`
  - Başarıda: "RFID eşleştirmesi başarılı." toast + form temizleme.
  - `KIYAFET_RFID_TAKEN` → "Bu RFID tag zaten başka bir sicille eşleşmiş." toast.

**Tablo (altta):**
- Kıyafet listesi; arama (rfid/sicil/ad soyad); 50 kayıt/sayfa.
- Her satırda: **Düzenle** (PATCH modal) + **Sil** (onay dialog + DELETE).

---

## S-AUDIT — Audit Loglar

**Tip:** Tablo view (salt okunur).
**Erişim:** admin.

**Filtreler:**
- Kullanıcı adı (text input)
- Aksiyon kodu (select; tüm standart kodlar listede)

**Tablo kolonları:**

| Kolon | Kaynak alan |
|-------|------------|
| Zaman | `timestamp` |
| Kullanıcı | `username` |
| Aksiyon | `action` |
| Detay | `detail` |
| Durum | `status` (Başarılı / Başarısız badge) |

Not: `ip_hash` alanı tabloda gösterilmez (KVKK).

**Sayfalama:** 100 kayıt/sayfa; max 500.

---

## S-KULLANICI — Kullanıcı Yönetimi

**Tip:** Tablo view + form modal.
**Erişim:** admin.

**Tablo kolonları:**

| Kolon | Kaynak alan |
|-------|------------|
| # | `id` (kısaltılmış UUID) |
| Kullanıcı Adı | `username` |
| Rol | `role` (Admin / Görevli badge) |
| Unvan | `title` |
| Şirket | `company` |
| Durum | `is_active` (Aktif / Pasif badge) |
| İşlem | Düzenle + Sil |

**Yeni Kullanıcı (modal):**

| Alan | Tip | Zorunlu |
|------|-----|---------|
| Kullanıcı Adı | Text | Evet |
| Şifre | Password | Evet (min 12 karakter) |
| Rol | Select (admin/user) | Evet |
| Unvan | Text | Hayır |
| Şirket | Text | Hayır |
| Email | Email | Hayır |
| Telefon | Text | Hayır |

**Düzenleme modal:** Şifre hariç aynı alanlar + Rol değişikliği.

**Silme:** Onay dialog. Kendi hesabı veya son admin ise hata gösterilir.

---

## S-PROFIL — Profil / Ayarlar

**Tip:** Tam sayfa.
**Erişim:** user + admin.

**Bölüm 1: Profil Bilgileri**

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| Kullanıcı Adı | Text (readonly) | — | Değiştirilemez |
| Rol | Text (readonly) | — | — |
| Email | Email | Hayır | Güncellenebilir |
| Telefon | Text | Hayır | — |
| Unvan | Text | Hayır | — |
| Şirket | Text | Hayır | — |

**Kaydet** → `PATCH /api/v1/users/me`

**Bölüm 2: Şifre Değiştirme**

| Alan | Tip | Açıklama |
|------|-----|----------|
| Yeni Şifre | Password | Min 12 karakter |
| Şifre Tekrar | Password | Client-side eşleşme kontrolü |

**Şifreyi Güncelle** → `PATCH /api/v1/users/me` (password alanı ile).

**Bölüm 3: Profil Avatarı**

- Avatar, kullanıcının ad/soyad baş harfleriyle gösterilir (örn. "AY"). Fotoğraf yükleme özelliği kaldırılmıştır; ekranda dosya seçme/yükleme alanı yoktur.

---

## Ortak Bileşenler

### Toast Bildirimleri

- Sağ üst köşede 3 saniye görünür.
- Tip: `success` (yeşil), `error` (kırmızı), `warning` (sarı), `info` (mavi).

### Onay Dialog'u

- Modal overlay.
- İşlem adı + uyarı mesajı.
- **İptal** + **Onayla** butonları.
- Enter → Onayla; ESC → İptal.

### Loading State

- Tablo yüklenirken skeleton veya spinner gösterilir.
- Buton tıklandığında disabled + spinner olur; yanıt gelene kadar tekrar tıklanamaz.

### Sayfalama (Pagination)

- Önceki / Sonraki butonlar.
- Mevcut sayfa / toplam sayfa bilgisi.
- Kayıt sayısı bilgisi: "X – Y / Z kayıt".
