# ADR 0002: Vanilla JS ve Tailwind CSS Tercihi

**Tarih:** 2026-06-07  
**Durum:** Kabul Edildi  

## Bağlam
LaundroStar uygulaması temelde bir iç otomasyon (internal tool) aracıdır. Frontend framework'ü olarak kurumsal standart genellikle React + TypeScript olmasına rağmen, bu projenin kapsamı ve hızlı teslimat gereksinimi değerlendirildi.

## Karar
Frontend katmanında hiçbir derleme aşaması (build step) gerektirmeyen **Vanilla JS (ES6+)** ve CDN üzerinden alınan **Tailwind CSS** kullanılmasına karar verildi.

## Alternatifler
- **React + TypeScript (Next.js/Vite):** Kurumsal standarttır. Güçlü tip kontrolü ve modüler component mimarisi sunar. Ancak proje için ayrı bir build pipeline, CI/CD adımı ve Node.js environment gerektirir.
- **Vue.js:** Öğrenme eğrisi düşüktür ancak yine de bir derleme süreci gerektirir veya CDN ile kullanıldığında component mimarisi kısıtlı kalır.

## Sonuçlar
- **Olumlu:** Proje tek bir Docker container (FastAPI) üzerinden sunulabilir hale geldi (BFF gereksinimi ortadan kalktı). Geliştirme hızı arttı.
- **Olumsuz:** Kod tabanı büyüdükçe state yönetimi (AppState) zorlaşabilir. Tip güvenliği (Type Safety) eksikliği runtime hatalarına neden olabilir.

## AI Rolü ve İnsan Kararı
**AI önerisi:** AI ajanı, kurumsal standart olan React+TypeScript yerine derleme adımı gerektirmeyen Vanilla JS + CDN Tailwind yığınını önerdi; gerekçe over-engineering'den kaçınmak ve uygulamayı tek FastAPI container'ından sunulabilir tutmaktı.

**İnsan kararı:** Proje sahibi, kurumsal standarttan bu sapmayı bilinçli olarak kabul etti çünkü (1) LaundroStar bir iç otomasyon/kiosk aracıdır, dışa açık karmaşık bir SPA değildir; (2) ayrı bir Node.js build pipeline + CI adımı, kapalı devre tesis kurulumunda bakım yükü ve bağımlılık riski getirir; (3) tip güvenliği eksikliğinin yaratabileceği runtime hataları, `innerHTML` yasağı + DOM helper (XSS önlemi) ve test coverage (%80) ile telafi edilebilir bulundu. Sapma, ADR olarak kayıt altına alınması koşuluyla onaylandı.
