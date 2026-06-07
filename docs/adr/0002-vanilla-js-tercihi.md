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

## AI Rolü
AI ajanı, projenin modüler monolith mimarisine uygun olarak, gereksiz altyapı karmaşasını (over-engineering) önlemek adına bu hafif teknoloji yığınını önermiş ve uygulamıştır. XSS korumaları için özel DOM helper fonksiyonları AI tarafından sisteme dahil edilmiştir.
