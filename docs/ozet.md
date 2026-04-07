# LaundroStar - Yönetim Özeti ve Teknik Altyapı Raporu

Bu belge, LaundroStar sisteminin mevcut durumunu, teknolojik altyapısını, güvenlik standartlarını ve kurumsal ölçeklenme potansiyelini yönetim seviyesinde özetlemek amacıyla hazırlanmıştır.

---

## 1. Yönetici Özeti (Executive Summary)

LaundroStar, işletmenin çamaşırhane süreçlerini, kıyafet/üniforma zimmetlerini ve günlük temizlik döngülerini dijitalleştirmek amacıyla geliştirilmiş **uçtan uca entegre bir RFID otomasyon ve takip sistemidir.**

Hedefler:
- Kayıp/kaçak oranlarını sıfıra indirmek
- Manuel veri giriş hatalarını ortadan kaldırmak
- Raf doluluk/kapasite yönetimini anlık olarak sağlamak
- Yöneticilere veriye dayalı karar destek paneli (Dashboard) sunmak

---

## 2. Teknoloji Yığını (Tech Stack)

Uygulama, kurumsal standartlara uygun ve bulut sistemlerine hazır araçlar seçilerek geliştirilmiştir:

### Konteyner Mimarisi — Docker & Docker Compose
Sistem üç izole servis olarak çalışır: **Veritabanı (PostgreSQL)**, **Web Uygulaması (FastAPI)** ve **Proxy Sunucusu (Nginx)**. Docker sayesinde uygulamanın herhangi bir sunucuya taşınma ve başlatılma süresi dakikalarla ifade edilebilir.

### Web Sunucusu ve Proxy — Nginx
Dış dünyadan gelen trafiği karşılar. TLS/SSL (HTTPS) protokolünü yönetir; HTTP isteklerini HTTPS'e otomatik yönlendirir. Web uygulaması doğrudan internete açık değildir.

### Backend — Python 3.11 & FastAPI
Asenkron (async/await) mimarisiyle yüksek performanslı, RESTful API sunar. Her işlem adımı denetim kaydıyla belgelenir.

### Veritabanı — PostgreSQL 16 & SQLAlchemy
Kurumsal düzeyde ilişkisel veritabanı. Yüzlerce eş zamanlı bağlantıyı destekler; veriler kalıcı Docker volume'una yazılır.

### Frontend — HTML5, Tailwind CSS, Vanilla JavaScript, Chart.js
Tarayıcı tabanlı, ek kurulum gerektirmez. Masaüstü ve tablet cihazlara tam uyumlu (responsive). Dashboard yöneticiler için Chart.js ile görselleştirilmiştir.

---

## 3. Sistem Özellikleri

### Kıyafet Takip Döngüsü
- **Kirli Giriş:** RFID etiketi veya sicil numarası ile kıyafet sisteme alınır.
- **Temizlendi:** Yıkama tamamlandığında işaretlenir; kıyafet otomatik raf konumuna atanır.
- **Teslim:** Kıyafet personele teslim edildiğinde döngü kapanır.

### Otomatik Raf Atama Sistemi
8 raf bölümü (**A–H**), her biri 7 kat × 5 kompartıman. Toplam 280 göz. Sistem, kıyafeti personelin cinsiyetine göre doğru rafa yönlendirir:
- Kadın personeller → yalnızca **E rafı**
- Erkek personeller → A, B, C, D, F, G, H rafları

Atama algoritması gözleri kapasite dolma sırasına göre doldurur; taşma olmaz.

### 2D İnteraktif Raf Simülasyonu
- Her raf için 7×5 ızgara haritası
- Gözler doluluk durumuna göre renk kodlu (boş / kısmi / dolu)
- Üzerine gelindiğinde personel listesi popup olarak görüntülenir
- Sicil veya ad soyad ile arama; sonuç bulunan göze otomatik yönlendirme


### Tablo Araması
Kirli bekleyenler, temizlenenler, teslim edilecekler, personel ve RFID listelerinde anlık metin araması.

---

## 4. Güvenlik Mimarisi

| Katman | Uygulama |
|---|---|
| **Ağ izolasyonu** | Nginx reverse proxy; uygulama doğrudan internete açık değil |
| **Şifreleme** | HTTPS (TLS 1.2/1.3); tüm trafik şifreli |
| **Kimlik doğrulama** | JWT tabanlı; token süresi dolduğunda oturum kapanır |
| **Yetkilendirme** | Rol bazlı erişim (RBAC): admin / user |
| **Brute-force koruması** | IP bazlı rate limiting (slowapi) |
| **Denetim izi** | Tüm kritik işlemler kullanıcı adı ve IP ile kayıt altında |

---

## 5. Kurumsal Ölçeklenme Potansiyeli

### Mevcut Durum
Kurulu Docker + PostgreSQL mimarisi kurumsal standartlarda çalışmaktadır:
- PostgreSQL eş zamanlı yüzlerce bağlantıyı destekler
- Konteyner mimarisi beklenmedik çöküşlerde servisleri otomatik yeniden başlatır (`restart: unless-stopped`)
- Yüzlerce aktif personel ve geçmişe dönük milyonlarca işlem kaydını sorunsuz yönetir

### Gelecek Ölçekleme Opsiyonları

1. **Kubernetes & Yüksek Erişilebilirlik:** Proje Docker tabanlı olduğundan Kubernetes'e taşınması mümkündür. Web sunucu sayısı talebe göre otomatik artırılabilir (Auto-Scaling). PostgreSQL tarafında replikasyon yapılabilir.

2. **Mesaj Kuyrukları (RabbitMQ / Kafka):** Üretim hacmi büyüdüğünde barkod/RFID tarama istekleri kuyruk sistemine alınarak asenkron işlenebilir.

3. **RFID Donanım Entegrasyonu:** Gerçek RFID tünel okuyucuları API'ye doğrudan bağlanarak insan faktörü sürece dahil olmadan %100 otonom çalışma sağlanabilir.

4. **ERP / İK Entegrasyonu:** Açık RESTful API mimarisi üzerinden SAP, Oracle gibi sistemlerle entegrasyon kurularak personel verisi iki yönlü senkronize edilebilir.

---

**Sonuç:** LaundroStar; kurumsal veritabanı (PostgreSQL), ağ güvenliği (Nginx/TLS), izole konteyner mimarisi (Docker) ve kapsamlı denetim altyapısıyla yalnızca bir operasyon paneli değil, ölçeklenebilir bir kurumsal IT ekosistemidir.
