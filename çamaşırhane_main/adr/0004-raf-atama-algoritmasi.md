# ADR 0004: Raf Atama Algoritması Tasarımı

**Tarih:** 2026-06-07  
**Durum:** Kabul Edildi  

## Bağlam
Temizlenen kıyafetlerin raflara atanması sürecinde kapasitenin verimli kullanılması ve çalışanların kıyafetlerini kolay bulabilmesi için bir mantık kurulması gerekiyordu. Tesisin raf kapasitesi: 8 raf (A-H), 7 kat, her katta 5 bölme (7. kat 1 kapasiteli, diğerleri 3 kapasiteli) şeklindedir.

## Karar
Cinsiyet bazlı izolasyon içeren, doluluk oranını (first-available-fit) dikkate alan dinamik bir raf atama algoritması benimsenmiştir.
- **Kadın Çalışanlar:** Yalnızca E rafı (Kapasite: 95)
- **Erkek Çalışanlar:** A, B, C, D, F, G, H rafları (Kapasite: 665)

## Alternatifler
- **Sicil Numarasına Göre Sabit Raf:** Her çalışana sabit bir raf atanabilirdi. Ancak vardiyalı sistemde boş raflar verimsiz kalır ve işten çıkanların rafları atıl dururdu.
- **Rastgele Atama:** Kapasite tam kullanılır ancak teslim sırasında operatörün kıyafeti bulmasını zorlaştırır, mantıksal bir gruplama olmaz.

## Sonuçlar
- **Olumlu:** Kadın ve erkek soyunma odalarına/teslim noktalarına göre fiziksel organizasyon yapılabilmesine olanak tanındı. Kapasite (760 kıyafet) tamamen dinamik kullanılıyor.
- **Olumsuz:** Kadın çalışan sayısının raf E kapasitesini (95) aşması durumunda sistem darboğaza girecektir. Bu durumda config üzerinden kadın raf havuzuna yeni bir raf (örn. F) eklenmesi gerekebilir.

## AI Rolü
Bu algoritma, gereksinimlerdeki örtük kısıtları (kapasite limitleri ve fiziksel ayrım ihtimalleri) değerlendirerek AI ajanı tarafından `app/main.py` içerisindeki `assign_shelf` fonksiyonu ile kodlanmış ve belgelenmiştir.
