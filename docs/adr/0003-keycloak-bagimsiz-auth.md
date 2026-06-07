# ADR 0003: Keycloak Yerine Bağımsız (Standalone) Auth Kullanımı

**Tarih:** 2026-06-07  
**Durum:** Kabul Edildi (İstisnai Durum)

## Bağlam
Kurumsal standartlar (Boyut 3) tüm yeni uygulamaların Keycloak SSO sistemine entegre olmasını zorunlu kılmaktadır. Ancak LaundroStar sistemi, doğrudan fabrikada fiziksel olarak kurulan, fabrika ağından bağımsız veya kapalı devre bir ağda çalışabilmesi öngörülen spesifik bir donanım/kiosk entegrasyon aracıdır.

## Karar
Projenin Faz 1 kapsamında **bağımsız (standalone) JWT tabanlı kimlik doğrulama sistemi** kullanmasına karar verilmiştir.

## Alternatifler
- **Keycloak SSO Entegrasyonu:** Standartlara tam uyar. Ancak kapalı devre fabrika ağlarında (internet/intranet erişiminin kısıtlı olduğu üretim bantlarında) SSO sunucusuna ulaşılamaması durumunda sistemin çökmesine neden olur.

## Sonuçlar
- **Olumlu:** Uygulama tamamen kendi başına (self-contained) çalışabilir durumda. Ağ kopmalarından etkilenmeden lokal veritabanı ile auth işlemlerini yürütebilir.
- **Olumsuz:** Kurumsal standarttan sapılmıştır. Kullanıcılar için ayrı bir şifre yönetimi gerektirir (şifre yorgunluğu).

## Gelecek Planı
Uygulamanın internet erişimi olan genel ağlara taşınması durumunda, `/api/v1/auth/token` endpoint'i Keycloak'a proxy yapacak şekilde modifiye edilmek üzere tasarlanmıştır (Dependency Injection yapısı buna uygundur).

## AI Rolü
Uygulamanın bağımsız çalışabilirlik ("standalone") gereksiniminden dolayı AI, bu mimari sapmayı tercih etmiş, ancak güvenliği maksimize etmek için RS256 ve hesap kilitleme mekanizmalarını kurmuştur.
