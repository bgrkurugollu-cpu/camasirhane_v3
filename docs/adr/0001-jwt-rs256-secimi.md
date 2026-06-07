# ADR 0001: JWT RS256 Algoritma Seçimi

**Tarih:** 2026-06-07  
**Durum:** Kabul Edildi  

## Bağlam
Kimlik doğrulama sürecinde kullanılacak JWT (JSON Web Token) imzalama algoritmasının belirlenmesi gerekiyordu. Standart olarak çoğu projede simetrik bir şifreleme olan HS256 kullanılırken, bu projenin ileride farklı mikroservislerle veya entegrasyonlarla büyüme ihtimali göz önünde bulunduruldu.

## Karar
JWT imzalama algoritması olarak asimetrik **RS256** (RSA Signature with SHA-256) kullanılmasına karar verildi.

## Alternatifler
- **HS256:** Simetrik şifreleme kullanır. Tek bir secret key ile hem imzalama hem doğrulama yapılır. Kurulumu kolaydır ancak secret key sızdığında tüm sistem tehlikeye girer.
- **ES256:** ECDSA kullanarak imzalama yapar. RSA'e göre daha küçük anahtar boyutlarıyla aynı güvenliği sağlar ancak mevcut kütüphane desteği (python-jose) RS256 kadar yaygın ve stabil kullanılmayabilir.

## Sonuçlar
- **Olumlu:** Public key'in dış sistemlerle veya gelecekte eklenecek mikroservislerle güvenli bir şekilde paylaşılabilmesi sağlandı. Merkezi bir doğrulama servisi ihtiyacı ortadan kalktı.
- **Olumsuz:** Sertifika/anahtar yönetimi karmaşıklığı eklendi. `.pem` dosyalarının Docker container'a güvenli bir şekilde mount edilmesi gereksinimi oluştu.

## AI Rolü
Bu karar, projenin "Faz 2 Vibecoding Standartları" kapsamında AI ajanı tarafından, güvenlik boyutunu (Boyut 3) maksimize etmek ve kurumsal standartlara uyum sağlamak amacıyla önerilmiş ve uygulanmıştır.
