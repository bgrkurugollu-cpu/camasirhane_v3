# ADR 0008: Deployment Modeli — On-Premise (Tesis Başına Ayrı Kurulum)

**Tarih:** 2026-06-14  
**Durum:** Kabul Edildi  

## Bağlam
Mimari Gate raporu (2026-06-14), doküman paketi boyunca deployment modelinin tanımlanmamış olmasını **blocker** olarak işaretledi. Çelişki somuttu: o tarihteki doküman paketi (`ozet.md`, `topoloji.md` — sonradan numaralı 00–11 paketiyle değiştirildi) sistemi bir yerde "işletmenin/tesislerin çamaşırhane süreçlerini dijitalleştirme" olarak çoğul tanımlarken, başka bir yerde "Faz 1 hedef tesis" varsayımıyla yazılmıştı. Bu belirsizlik mevcut mimari kararların büyük bölümünün (Vanilla JS — ADR 0002, standalone auth — ADR 0003, hardcoded raf algoritması — ADR 0004) gerekçesini havada bırakıyordu; çünkü hepsi örtük olarak "tek tesis, kapalı devre, dahili araç" varsayımına dayanıyordu.

Temel soru: **Uygulama tek tesise mi kurulacak, birden fazla tesise mi?**

## Karar
LaundroStar **on-premise, tesis başına ayrı (self-contained) kurulum** modeliyle dağıtılır. Her tesis kendi izole `docker-compose` yığınında (db + web + nginx), kendi PostgreSQL örneğiyle çalışır. Multi-tenant (tek uygulama, paylaşımlı şema) modeline **geçilmez**.

Operasyonel ölçeklenmeyi sağlamak için kurulum, çıplak "her tesise elle kurulum" değil, **fleet-managed on-premise** olarak konumlandırılır: tesisler izole kalır ama deployment/patch/monitoring merkezi bir IaC + log-aggregation hattından yönetilir (bkz. Sonuçlar ve Faz 2 notu).

## Alternatifler

### Alternatif A — On-premise, her tesiste bağımsız kurulum (SEÇİLDİ, fleet-managed varyantıyla)
Her tesis kendi yığınında çalışır; veri izolasyonu ve ağ bağımsızlığı (ADR 0003) korunur. Kapalı devre fabrika ağı gereksinimini doğal olarak karşılar. Operasyonel riski (versiyon drift, patch gecikmesi, config drift, monitoring körlüğü) fleet management katmanı ile kapatılır.

### Alternatif B — Merkezi, çok-tesis (multi-tenant) kurulum (REDDEDİLDİ)
Tek uygulama tüm tesislere hizmet eder; tek SSL, tek patch. Operasyonel yük tesis sayısından bağımsızlaşır. **Reddedilme gerekçeleri:**
- **Kapalı devre ağ gereksinimini karşılamaz:** ADR 0003'ün dayandığı temel kısıt, tesislerin internet/intranet erişiminin kısıtlı olabileceğidir. Merkezi model, her tesisin sürekli merkeze bağlı olmasını şart koşar; merkez erişilemezse o tesis çalışamaz — kabul edilemez tek hata noktası.
- **Veri izolasyonu zayıflar:** Tek PostgreSQL şeması + tek `users` tablosu, tesisler arası veri sızıntısı yüzeyi açar. KVKK/veri yerelliği açısından her tesisin verisinin fiziksel olarak ayrı kalması tercih edilir.
- **Büyük ve kırıcı kod yatırımı:** Mevcut kod tabanında hiçbir tenant izolasyonu yok. B alternatifi tüm tablolara `tenant_id`, API katmanında tenant doğrulaması, Keycloak entegrasyonu (ADR 0003 geçersiz kalır) ve raf konfigürasyonunun config-driven hale getirilmesini (ADR 0004 kırılır) gerektirir. Faz 1 kapsamı ve teslim takvimiyle orantısız.

## Sonuçlar
- **Olumlu:** Veri izolasyonu, ağ bağımsızlığı ve kapalı devre çalışabilirlik korunur. ADR 0002/0003/0004 varsayımları artık açıkça dokümante edilmiş bir zemine oturur. Faz 1'de **kod değişikliği gerekmez.**
- **Olumsuz / azaltım gerektiren:** "Her tesise elle kurulum" 5+ tesiste operasyonel olarak ölçeklenmez (versiyon drift, gecikmeli güvenlik patch'i, config drift, merkezi monitoring eksikliği). Bu risk, 3–5 tesis eşiğine gelmeden **fleet management altyapısı** kurularak azaltılır:
  - Tüm tesislere deployment tek komutla (Ansible/benzeri IaC); versiyon tutarlılığı pipeline tarafından zorlanır.
  - Security patch'ler tüm fleet'e eş zamanlı; doğrulama tek pipeline'dan.
  - Tüm tesis logları merkezi OpenSearch'e Fluent Bit ile akar (tek monitoring panosu; bkz. [[08_SECURITY_IMPLEMENTATION#11.1 Loglama Kategorileri ve Alerting]]).
  - SSL sertifika yönetimi otomatize (internal CA veya Let's Encrypt + certbot).
- Bu yatırım IaC + CI/CD'dir, uygulama kodu değil. Ekip bu altyapıyı kurmadan tesis sayısını artırırsa operasyonel yük altında kalır.

## Faz 2 Notu — Merkezi Raporlama (Taslak)
Çok-tesisli kurumsal görünürlük ihtiyacı doğarsa, multi-tenant'a geçmeden **salt-okunur merkezi raporlama** katmanı eklenir: her tesis, audit/işlem özetlerini periyodik olarak (veya log aggregation hattı üzerinden) merkezi bir read-only veri ambarına push eder. Operasyonel veri tesiste kalır, yalnızca raporlama agregasyonu merkezde toplanır. Bu, B alternatifinin izolasyon ve kapalı-devre dezavantajlarına girmeden yönetim seviyesinde fleet görünürlüğü sağlar. Detaylı tasarım Faz 2 kapsamına bırakılmıştır.

## AI Rolü
AI ajanı, Mimari Gate raporundaki iki deployment alternatifini (A: on-premise ayrı kurulum, B: multi-tenant) operasyonel SDLC, güvenlik patch yönetimi, config drift ve monitoring boyutlarıyla analiz edip karşılaştırdı ve fleet-managed on-premise (Alternatif C) sentezini önerdi. **İnsan kararı:** Proje sahibi, fabrika tesislerinin kapalı devre ağ gerçekliği ve veri yerelliği önceliği nedeniyle Alternatif A'yı (fleet-managed varyantıyla) kabul etti; B, kapalı-devre gereksinimini karşılamadığı ve mevcut kod tabanına orantısız bir yeniden yazım yükü getirdiği için bilinçle reddedildi. Merkezi raporlama ihtiyacı Faz 2'ye taslak olarak ertelendi.
