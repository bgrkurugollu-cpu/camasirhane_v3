# ADR 0007: Admin Hesapları için TOTP Tabanlı İki Faktörlü Kimlik Doğrulama (MFA)

**Tarih:** 2026-06-07
**Durum:** Kabul Edildi

## Bağlam
Mimari Gate Raporu (2026-06-05), kurumsal güvenlik standardının admin kullanıcılar için MFA zorunluluğu getirdiğini, ancak sistemin admin hesaplarına yalnızca şifre + hesap kilitleme kombinasyonu sunduğunu blocker olarak işaretledi. Bir admin hesabının ele geçirilmesi durumunda tüm kıyafet verileri, personel kayıtları ve audit logları risk altına girmektedir.

ADR 0003 gereği sistem Keycloak'a bağımlı değildir (kapalı devre fabrika ağı gereksinimi). Dolayısıyla "Keycloak MFA" seçeneği bu mimaride kullanılamaz; çözüm self-contained olmalıdır.

## Karar
Admin (ve isteğe bağlı olarak tüm) kullanıcılar için **TOTP (Time-based One-Time Password, RFC 6238)** tabanlı, `pyotp` ile uygulanan bir ikinci faktör mekanizması eklenmiştir. Google Authenticator / Microsoft Authenticator gibi standart uygulamalarla uyumludur.

**Akış:**
1. Login (`POST /auth/token`) birinci faktörü (şifre) doğrular.
2. Kullanıcının `mfa_enabled` alanı 1 ise access token üretilmez; bunun yerine kısa ömürlü (5 dk) `type="mfa"` ara token döner: `{ "mfa_required": true, "mfa_token": "..." }`.
3. İstemci, authenticator kodunu `POST /auth/mfa/verify` (`{mfa_token, code}`) ile gönderir. Kod doğruysa normal oturum (access + refresh) açılır.
4. Kayıt: oturum açmış kullanıcı `POST /auth/mfa/setup` ile secret + `otpauth://` URI alır (QR), `POST /auth/mfa/activate` ile kodu doğrulayıp etkinleştirir. `POST /auth/mfa/disable` ile geçerli kodla kapatır.

`ADMIN_MFA_REQUIRED=true` env değişkeni açıldığında, MFA tanımlamamış admin login yanıtında `mfa_enrollment_required: true` uyarısı alır (operasyonel zorunluluk politikası).

## Alternatifler
- **Keycloak MFA:** Kurumsal standart. ADR 0003'teki kapalı devre ağ gereksinimi nedeniyle reddedildi.
- **SMS/E-posta OTP:** Harici servis (SMS gateway / SMTP) bağımlılığı; kapalı devre ağda erişilemez ve SIM-swap riski taşır. Reddedildi.
- **WebAuthn / FIDO2 (donanım anahtarı):** En güçlü seçenek; ancak donanım dağıtımı ve tarayıcı/işletim sistemi desteği Faz 1 kapsamı için ağır. v5 için aday olarak not edildi.

## Sonuçlar
- **Olumlu:** Admin ele geçirme riski büyük ölçüde azaldı; çözüm tamamen self-contained, internet/SSO gerektirmiyor. Secret DB'de tutulur, doğrulama lokal yapılır.
- **Olumsuz:** TOTP secret'ı veritabanında saklanıyor (plaintext base32). DB ele geçirilirse secret'lar açığa çıkar; v5'te secret'ların uygulama anahtarıyla şifrelenerek (encryption-at-rest) saklanması planlanmaktadır. Kullanıcı authenticator cihazını kaybederse admin tarafından MFA reset prosedürü gerekir.

## AI Rolü
Bu güvenlik özelliği, AI ajanı tarafından Mimari Gate blocker'ını (Boyut 3 — Güvenlik) kapatmak amacıyla; `pyotp` ile `app/security.py` yardımcıları, `app/modules/auth` servis/router katmanı, `User.mfa_enabled/mfa_secret` modeli ve `tests/test_auth.py` MFA testleri olarak tasarlanıp uygulanmıştır.
