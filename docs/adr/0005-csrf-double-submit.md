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

## AI Rolü
"Faz 2 Vibecoding Standartları" uyarınca stateless güvenlik altyapısı kurma sorumluluğu AI tarafından üstlenilmiş ve middleware seviyesinde enforce edilmiştir.
