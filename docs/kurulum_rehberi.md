# LaundroStar - Kurulum Rehberi

Bu rehber, LaundroStar uygulamasını sıfırdan başka bir bilgisayara (sunucu veya yerel makine) kurmak ve çalıştırmak için izlenmesi gereken adımları içerir. Sistem **Docker** tabanlı olduğu için kurulum oldukça basittir.

## Ön Koşullar (Gereksinimler)

Sistemi çalıştıracağınız yeni bilgisayarda aşağıdaki yazılımların kurulu olması gerekmektedir:

1. **Docker:** Konteynerleri çalıştırmak için.
    * [Docker Desktop İndir (Windows/Mac)](https://www.docker.com/products/docker-desktop/)
    * Linux için: `sudo apt-get install docker-ce docker-ce-cli containerd.io`
2. **Git:** Proje dosyalarını bilgisayara çekmek için (isteğe bağlı ama önerilir).
    * [Git İndir](https://git-scm.com/downloads)

*(Not: Python kurmanıza gerek yoktur, Docker tüm Python bağımlılıklarını izole bir şekilde kendi içinde kuracaktır.)*

---

## Adım Adım Kurulum

### Adım 1: Proje Dosyalarının Alınması
Proje dosyalarını yeni bilgisayara kopyalayın. Kurum içi bir Git sunucunuz varsa repoyu klonlayabilirsiniz. Eğer klasör olarak kopyaladıysanız, klasörü uygun bir dizine (örneğin Masaüstüne) taşıyın.

Git ile çekiyorsanız:
```bash
git clone <repo-adresi> camasirhane
cd camasirhane
```

Sadece kopyaladıysanız terminal (veya Command Prompt) açıp proje klasörüne gidin:
```bash
cd yol/nereye/kopyaladiysaniz/camasirhane
```

### Adım 2: Konteynerleri Ayağa Kaldırma (Build)
Uygulamanın bulunduğu ana dizinde (içinde `docker-compose.yml` olan klasörde) terminal üzerinden aşağıdaki komutu çalıştırarak imajı derleyip, veritabanını oluşturup, ağı bağlayıp arka planda (`-d`) çalışmaya bırakın.

```bash
docker-compose up -d --build
```
*İlk çalıştırmada; Docker gerekli işletim sistemini, Python çevresini indirecek ve bağımlılıkları derleyecektir (Bu işlem internet hızınıza bağlı olarak birkaç dakika sürebilir).*

### Adım 3: Çalıştığını Doğrulama
Bu işlem tamamlandıktan sonra, terminalinizde hata yoksa uygulamanız başarılı bir şekilde portlanmış demektir. Konteynerin durumunu görmek için:
```bash
docker ps
```
Burada `camasirhane-web-1` (veya benzeri isimli) uygulamanızın **8085** portunda (0.0.0.0:8085) ayakta olduğunu görmelisiniz.

---

## Sisteme Erişim ve Kullanım

### Web Arayüzüne Girmek
Kurulum tamamlandıktan sonra, bilgisayarınızda bir internet tarayıcısı (Chrome, Safari, Edge) açın ve adres çubuğuna şunu yazın:

* **Lokal Kurulum İçin:** `http://localhost:8085` veya `http://127.0.0.1:8085`
* **Sunucu Kurulumu Varsa:** `http://<sunucu-ip-adresi>:8085`

### İlk Kullanıcılarla Giriş (Mock Data)
Sisteme ilk kez girildiğinde veritabanı tamamen boştur. Yönetici hesabı oluşturmak ve temel konfigürasyonu (Personeller ve Kıyafetlerin RFID takipleri) başlatmak için:

1. `app/main.py` dosyasında yazdığımız "Demo Verisi Yükle" (`/api/init_mock_data`) API'sini tetikleyebilirsiniz. (Eski arayüzdeki butonu kaldırdığımızdan curl veya postman ile çağırabilirsiniz veya doğrudan SQLite yönetim paneli ile kendi tablolarınızı manuel girebilirsiniz.)
2. Bir kez admin ve personeller veritabanına işlendikten sonra `http://localhost:8085` adresinden:
   - **Kullanıcı Adı:** `admin` | **Şifre:** `admin`   *(Yetkili hesap)*
   - **Kullanıcı Adı:** `user` | **Şifre:** `user`     *(Sadece işlem görebilen hesap)*
   bilgileriyle sisteme giriş yapabilirsiniz.

*(Güvenlik notu: Sisteme ilk girişinizden sonra sağ üst köşeden profilinize girerek bu varsayılan şifreleri hemen değiştirmeniz önerilir.)*

---

## Veritabanı ve Kritik Dosyalar

* Mimaride veritabanı Docker'ın içindeki sanal diske gömülü **değildir**. Docker'a dışarıdan bağlı (`bind-mount`) lokal bir volume oluşturulmuştur.
* `camasirhane/data/camasirhane.db` dosyasını yeni bir yere taşırsanız, **tüm sistem geçmişi, kayıtlar ve şifreler o dosyanın içindedir.**
* Bilgisayarı kapatıp açtığınızda Docker Desktop otomatik başlıyorsa uygulamanız da arka planda kendi kendine otomatik olarak yayın yapmaya devam edecektir.

## Sistemin Kapatılması
Servisi geçici olarak durdurmak isterseniz ana proje dizininde şu komutu verebilirsiniz:
```bash
docker-compose down
```
*(Bunu yaptığınızda verileriniz silinmez, koruma altındadır. Uygulamayı yeniden ulaşıma açmak için tekrar `docker-compose up -d` demeniz yeterlidir).*
