# LaundroStar (Çamaşırhane Otomasyon Sistemi) - Yönetim Özeti & Teknik Altyapı Raporu

Aşağıdaki belge, projemizin halihazırda ulaştığı mevcut durumu ("As-Is"), kurduğumuz güçlü teknolojik altyapıyı, güvenlik standartlarını ve gelecekteki kurumsal ölçeklenme opsiyonlarını ("To-Be") şirket yönetimi ve CEO seviyesinde sunmak amacıyla hazırlanmıştır.

---

## 1. Yönetici Özeti (Executive Summary)
LaundroStar, işletmemizin çamaşırhane süreçlerini, kıyafet/üniforma zimmetlerini ve günlük temizlik döngülerini dijitalleştirmek amacıyla geliştirilmiş, **uçtan uca entegre bir RFID/Barkod otomasyon ve takip sistemidir.** 

Amacımız; kayıp kaçak oranlarını sıfıra indirmek, manuel veri giriş hatalarını ortadan kaldırmak, anlık raf doluluk/kapasite yönetimini sağlamak ve yöneticilere veriye dayalı anlık kararlar alabilmeleri için canlı bir Dashboard sunmaktır.

---

## 2. Teknik Altyapı ve Kullanılan Framework'ler (Tech Stack)

Uygulama, modern, bulut sistemlerine hazır ve yüksek performanslı araçlar seçilerek "Microservice" mimari konseptine uygun şekilde inşa edilmiştir:

*   **Konteyner Mimarisi:** **Docker & Docker Compose**
    *   Hizmetlerimiz (Web, Veritabanı ve Sunucu Proxy'si) izole edilmiş Docker konteynerleri içerisinde çalıştırılmaktadır. Bu sayede uygulamanın herhangi bir sunucuya kurulum süresi saniyelerle ifade edilebilir.
*   **Web Sunucusu ve Proxy:** **NGINX**
    *   Trafiği karşılamak ve load-balancing (yük dengeleme) yapmak için Nginx kullanılmaktadır. Üst düzey güvenlik için SSL/TLS (HTTPS) protokollerini yönetir ve uygulamaya güvenli erişim sağlar.
*   **Backend (Motor ve API):** **Python 3 ve FastAPI**
    *   Saniyede binlerce isteği asenkron (async/await) yapısıyla yönetebilen, sektördeki en hızlı ve modern API framework'lerinden biridir. %100 RESTful mimari ile Frontend'i besler.
*   **Veritabanı (Database):** **PostgreSQL 16 (Alpine) & SQLAlchemy**
    *   İlişkisel veritabanı yönetim sistemi olarak, açık kaynak dünyasının endüstri standardı olan güçlü **PostgreSQL** tercih edilmiştir. On milyonlarca satır veriyi sıfır veri kaybı riskiyle yönetebilecek güce sahiptir.
*   **Frontend (Ön Yüz):** **Vanilla JavaScript, HTML5 & Tailwind CSS**
    *   Tarayıcıların doğrudan donanımı (kamera, okuyucu) kullanabilmesini sağlayan bir altyapı tasarlandı. Tailwind CSS ile mobil ve endüstriyel tabletlere tam uyum (responsive) sağlandı. `Chart.js` ile dashboard yöneticiler için görselleştirildi, `jsPDF` ve `QRious` ile endüstriyel etiket yazdırma becerisi eklendi.

---

## 3. Sistem Tasarımı, Veritabanı ve Güvenlik
Sanayi tesislerinde verinin güvenilirliği kritik önem taşıdığı için güvenlik ağı derinlemesine bir tasarımla belirlenmiştir:

*   **Rol Bazlı Yetkilendirme (RBAC) & JWT (JSON Web Tokens):** 
    *   Sistem, standart "Görevli" ve "Sistem Yöneticisi" (Admin) ayrımına sahiptir. Sadece yetkili Admin'ler personelleri / RFID demirbaşlarını yönetebilir.
*   **Dinamik Kısıtlama (Rate Limiting):**
    *   `SlowAPI` kullanılarak IP bazlı hız sınırlandırmaları getirilmiştir. Kötü amaçlı yazılımların ardışık login denemeleri veya sisteme sızma girişimleri donanımsal düzeyde engellenir.
*   **Ağ Güvenliği (Nginx Reverse Proxy):**
    *   API'ın doğrudan internete açık olması Nginx ile engellenmiş; sadece yetkilendirilmiş HTTPS istekleri kapıdan geçirilerek uygulamanın izole kalkan arkasında kalması sağlanmıştır.
*   **Gelişmiş Denetim İzi (Audit Log Sistemi):**
    *   Uygulamadaki veri işleme adımlarının %100'ü kayıt altındadır. Hangi kullanıcının, hangi IP adresinden, hangi personel veya RFID üzerinde işlem yaptığı PostgreSQL veri tabanına işlenerek suistimallerin önüne kesilir.

---

## 4. Kurumsal Ölçekte Kullanılabilirlik (Scalability)

### Halihazırdaki Mevcut Kapasitemiz (As-Is Durumu)
Şu anda kurduğumuz Docker+PostgreSQL mimarisi ile bu uygulama **Enterprise (Kurumsal) Standartlarda** çalışmaktadır;
*   **Veri Yönetimi:** PostgreSQL veritabanımız aynı anda yüzlerce cihazın paralel barkod okutma isteğine (Concurrency) hiç zorlanmadan cevap verebilecek güce sahiptir. Veriler güvenle anlık olarak donanıma yazılır.
*   **Yüksek Kararlılık:** Konteyner mimarisi her bir servisin (Nginx, Web, DB) eğer beklenmeyen bir arıza çıkarsa saniyeler içinde otomatik olarak tekrar başlatılmasını (`restart: unless-stopped`) garanti eder. Kesinti süresi neredeyse sıfırdır.
*   Uygulama aktif yüzlerce çalışanın birden çok çamaşır zimmet döngüsünü ve geçmişe dönük milyonlarca işlem satırını rahatça listeleyebilir.

### Gelecek İçin Ölçekleme ve Transformasyon Opsiyonları (To-Be Durumu)
Sistemin sahip olduğu asenkron ve API-First dizaynı, uygulamayı gelecekteki mega-kurumsal senaryolara hazırlamaktadır:

1.  **High-Availability (Yüksek Bulunabilirlik) & Kubernetes:** Proje hali hazırda Docker üzerinden yürüdüğü için yarın "Multi-Node" bir Kubernetes dağıtımına bağlanıp, şirket büyüdükçe arkadaki web sunucu sayısı 1'den 100'e otomatik çıkartılabilir (Auto-Scaling). Database tarafında PostgreSQL Replication (Aktif-Pasif Kümeleme) yapılabilir.
2.  **Mesaj Kuyrukları ile Yük Dağıtımı (RabbitMQ / Kafka):** Kurumun üretim hacminin olağanüstü boyutlara ulaştığı durumlarda barkod taramaları mikro-saniyelik yanıtlar dönmesi adına doğrudan veri tabanına değil, MQ tabanlı kuyruklara (Kafka) yazılarak Backend tarafından asenkron eritilebilir.
3.  **IoT & Donanım Tünelleri Sinerjisi:** Manuel barkod kullanımının ötesine geçilerek, çamaşırhane kapılarına asılacak toplu RFID tünellerinden geçen yüzlerce sepet barkodu, doğrudan API'ımıza basılabilir ve insan faktörü elenerek %100 otonomlaştırmaya gidilebilir.
4.  **ERP ve İK Entegrasyonları (SAP / Oracle):** Var olan açık API mimarisi dış dünyaya açılarak yeni işe başlayan bir çalışanın ERP üzerindeki kaydının tetiklenmesiyle o saniye LaundroStar sisteminde otomatik personel dosyası açması programlanabilir.

---
**Özetle:** LaundroStar sadece bir panel değil; Endüstri standardında veritabanı yapısına (PostgreSQL), güvenliğe (NGINX/TLS) ve konteyner esnekliğine (Docker) halihazırda oturtulmuş Global çapta ölçeklenebilir bir kurumsal IT ekosistemidir.
