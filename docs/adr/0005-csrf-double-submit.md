# ADR 0005: CSRF Koruması için Double Submit Cookie Yöntemi Seçimi

**Tarih:** 2026-06-07  
**Durum:** Kabul Edildi  

## Bağlam
API'nin web tarayıcısı üzerinden kullanılmasından dolayı CSRF (Cross-Site Request Forgery) saldırılarına karşı korunması gerekmektedir. Frontend'in Vanilla JS olması ve SPA mantığıyla çalışması nedeniyle stateful bir session mekanizması yoktur.

## Karar
CSRF koruması için **Double Submit Cookie** (Çift Gönderim Cookie) yönteminin kullanılmasına ve bunun `CSRFMiddleware` olarak FastAPI uygulamasına entegre edilmesine karar verilmiştir.

## Alternatifler
- **Synchronizer Token Pattern:** Sunucunun session'da token tutmasını gerektirir. API'nin stateless JWT mimarisine (RESTful yapısına) ters düşer.
- **Sadece SameSite Cookie:** Sadece `SameSite=Strict` veya `Lax` kullanmak modern tarayıcılarda büyük ölçüde korur, ancak eski tarayıcılar veya spesifik origin yönlendirmeleri için yetersiz kalabilir.

## Sonuçlar
- **Olumlu:** Sunucuda herhangi bir state (durum) tutulmasına gerek kalmadı. Uygulama yatayda (horizontal) kolayca ölçeklenebilir. JWT token mimarisiyle tam uyumludur.
- **Olumsuz:** Frontend'in her `POST/PUT/DELETE` isteğinde, header içerisine `X-CSRF-Token` değerini cookie'den okuyup manuel olarak eklemesi gerekir (`fetchWithAuth` wrapper'ı yazılmasını zorunlu kıldı).

## AI Rolü ve İnsan Kararı
**AI önerisi:** AI ajanı, CSRF koruması için üç seçeneği (Synchronizer Token, yalnızca SameSite, Double Submit Cookie) değerlendirip Double Submit Cookie'yi önerdi; gerekçe, mevcut stateless JWT mimarisiyle uyum ve sunucuda session tutma ihtiyacının olmamasıydı.

**İnsan kararı:** Proje sahibi öneriyi kabul etti çünkü (1) Synchronizer Token Pattern, stateless JWT mimarisini bozar ve yatay ölçeklemeyi zorlaştırırdı; (2) yalnızca SameSite cookie'ye güvenmek eski tarayıcı/origin senaryolarında yetersizdi; (3) Double Submit'in getirdiği ek yük (frontend'in her mutasyon isteğinde `X-CSRF-Token` eklemesi) zaten yazılan `fetchWithAuth` wrapper'ı ile merkezileştirildiğinden kabul edilebilir bulundu. `auth/token`, `refresh`, `logout`, `mfa/verify` uçlarının muafiyeti de bilinçle onaylandı.
