# ADR 0006: Modüler Monolith ve Multi-Container Docker Mimarisi

**Tarih:** 2026-06-07  
**Durum:** Kabul Edildi  

## Bağlam
LaundroStar uygulaması çamaşırhane gibi yoğun bir operasyon sahasında çalışacak olup, bakımının kolay, yayın (deployment) sürecinin hatasız olması gerekmektedir. Faz 1 kapsamında uygulamanın çok yüksek trafikli bir e-ticaret sitesi gibi bağımsız mikroservislere bölünmesine gerek yoktur, ancak spagetti kod oluşumunun engellenmesi gereklidir.

## Karar
Sistemin kod tabanında **Modüler Monolith** (Router/Service/Repository katmanlarına sahip modüller), deployment tarafında ise **Multi-Container Docker** (Nginx, FastAPI, PostgreSQL) olarak tasarlanmasına karar verilmiştir.

## Alternatifler
- **Mikroservis Mimarisi:** Her modülün (kullanıcı, işlem, audit) ayrı bir servis olarak çalışması. Network gecikmesi, transaction yönetimi (Saga vb.) ve DevOps yükü getirdiği için reddedildi.
- **Tek Parça Monolith (Frontend dahil):** Nginx ve DB kullanılmadan SQLite ve Jinja2 template ile tek sunucu olarak ayağa kaldırılması. Güvenlik zafiyetleri ve ölçeklenme sorunu yarattığı için reddedildi.

## Sonuçlar
- **Olumlu:** Geliştiriciler kodu tek bir repo üzerinden (kolay debug ile) yönetebilir. Docker Compose sayesinde tek komutla tüm ortam izole ve standart bir şekilde (bağımlılık zinciri gözetilerek) ayağa kalkar.
- **Olumsuz:** Uygulamanın bir modülünde meydana gelen kritik bir hata (Memory leak vb.) tüm sistemi etkileyebilir.

## AI Rolü ve İnsan Kararı
**AI önerisi:** AI ajanı, Vibe Coding "Boyut 1: Katmanlı Mimari" ve "Boyut 9: Deployment & Docker" standartları doğrultusunda kod tarafında Modüler Monolith (Router/Service/Repository), deployment tarafında Multi-Container Docker yapısını önerdi; mikroservis ve tek-parça monolith alternatiflerini gerekçeleriyle eledi.

**İnsan kararı:** Proje sahibi öneriyi kabul etti çünkü (1) Faz 1 yük profili (tek tesis, ~1000 personel — bkz. `topoloji.md §12`) mikroservislerin getireceği network gecikmesi, dağıtık transaction ve DevOps yükünü gereksiz kılıyordu; (2) tek-parça (SQLite + Jinja2) alternatifi güvenlik ve ölçeklenme açısından yetersizdi; (3) Modüler Monolith, AI destekli geliştirmede tek modülün izole değiştirilebilmesini sağlayarak bakım ve devralınabilirliği artırıyordu. Tek modüldeki kritik hatanın tüm sistemi etkileyebileceği riski, deployment basitliği karşısında kabul edilebilir görüldü. (Deployment'ın tesis-başına ayrı kurulum olduğu ADR 0008 ile netleştirilmiştir.)
