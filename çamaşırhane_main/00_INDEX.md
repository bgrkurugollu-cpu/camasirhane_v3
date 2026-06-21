# 📚 LaundroStar Dokümantasyon Merkezi (Index)

LaundroStar (Çamaşırhane) projesinin teknik, mimari ve analiz dokümanlarına hoş geldiniz. Bu **INDEX**, tüm spesifikasyon dosyalarını birbirine bağlayan merkezi bir ana sayfa işlevi görür (Obsidian Graph View için merkez noktadır).

Aşağıdaki listeden incelemek istediğiniz konu başlığına tıklayarak ilgili dokümana gidebilirsiniz.

---

## 🧭 1. Temel Proje Dokümanları
Projenin ne olduğunu, iş kurallarını ve genel hedeflerini anlamak için ilk okunması gerekenler:

- **[[01_PROJECT_OVERVIEW]]**: Projenin genel amacı, hedefleri, temel özellikleri ve mimari özeti.
- **[[02_DOMAIN_MODEL]]**: Çamaşırhane domain'indeki varlıkların (Entity) ilişkileri, yaşam döngüleri (Kirli, Temiz, Teslim) ve audit kuralları.

## 🗄 2. Veri ve Altyapı
Veritabanı yapısı, şemalar ve sunucu spesifikasyonları:

- **[[03_DATABASE_SCHEMA]]**: PostgreSQL tablo yapıları, kolon detayları, hesap kilitleme mekanizmaları ve Alembic migration stratejisi.
- **[[05_BACKEND_SPEC]]**: Python FastAPI backend modüler mimarisi (Service/Repository), exception yapısı ve loglama standartları.

## 🔌 3. İletişim ve Arayüz
Sistemlerin birbiriyle veya kullanıcı ile nasıl iletişim kurduğunu belirleyen arayüzler:

- **[[03_API_CONTRACTS]]**: Tüm REST API endpointleri, request/response şemaları ve hata kodu standartları (Error Envelope).
- **[[06_FRONTEND_SPEC]]**: Vanilla JS mimarisi, SPA state yönetimi (AppState), `fetch` interceptor ve XSS korumaları (DOM Helper kullanımı).
- **[[07_SCREEN_CATALOG]]**: Kullanıcının göreceği tüm kullanıcı arayüzü (UI) ekranlarının listesi, bileşenleri ve akışları.

## 🛡 4. Güvenlik ve Kalite
Sistemin üretim ortamındaki güvencesini sağlayan dokümanlar:

- **[[08_SECURITY_IMPLEMENTATION]]**: JWT (RS256) oturum yönetimi, CSRF koruması, Brute Force (hesap kilit) mekanizmaları ve Multi-stage Docker altyapısı.
- **[[09_TESTING_STRATEGY]]**: Pytest entegrasyonu, unit ve integration test senaryoları ile %80 Coverage hedefi (CI gate; mevcut %85).

## ⚙️ 5. Geliştirme Süreci ve Analiz
Yeni versiyona geçiş yol haritası ve kodlama standartları:

- **[[10_DEV_WORKFLOW]]**: Docker geliştirme ortamı kurulumu, CI/CD pipeline süreçleri ve PR standartları.
- **[[11_IMPLEMENTATION_ROADMAP]]**: v3'ten v4'e geçiş için belirlenen 9 fazlık uygulama yol haritası ve tamamlanma durumları.
- **[[Backlog/FAZ_2_ANALIZ]]**: Projenin Vibecoding standartlarına göre yapılmış detaylı analiz raporu ve kapatılmış güvenlik açıkları listesi.
- **[[Vibe Coding Standartları]]**: Proje boyunca yapay zeka ajanının ve geliştiricinin uyması zorunlu olan genel vibecoding prensipleri.

---
*💡 İpucu: Obsidian üzerinden bu dokümanı "Graph View" modunda açtığınızda, tüm teknik dokümantasyon ekosisteminin bu dosya etrafında birbirine bağlandığını ve merkezi bir harita oluşturduğunu görebilirsiniz.*
