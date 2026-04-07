"""
1000 adet çalışan ve RFID eşleştirme kaydı oluşturur.
- 500 Kadın (cinsiyet='K') + 500 Erkek (cinsiyet='E')
- Sicil numarası: 700001 → 701000 (sıralı)
- RFID tag: 100001 → 101000 (sicil sırası ile eşleşik)
"""

import sys
import os
sys.path.insert(0, "/code")

from app.database import SessionLocal, engine
from app import models

models.Base.metadata.create_all(bind=engine)

# ------------------------------------------------------------
# İsim havuzları
# ------------------------------------------------------------
KADIN_ADLAR = [
    "Ayşe","Fatma","Zeynep","Emine","Hatice","Merve","Elif","Büşra","Selin","Esra",
    "Gül","Neslihan","Sibel","Deniz","Yasemin","Pınar","Ceren","Derya","Özlem","Tuğba",
    "Arzu","Gamze","Gizem","Hülya","İrem","Kübra","Leyla","Melek","Nilay","Özge",
    "Rabia","Sema","Sevda","Şule","Tuba","Ülkü","Vildan","Yeliz","Züleyha","Aslı",
    "Betül","Cansu","Dilek","Ebru","Figen","Gönül","Hayriye","İlknur","Jale","Kadriye",
    "Lale","Mihriban","Nadide","Pervin","Rukiye","Songül","Tülay","Ümran","Vesile","Yıldız"
]

ERKEK_ADLAR = [
    "Ahmet","Mehmet","Mustafa","Ali","Hüseyin","İbrahim","Hasan","Ömer","Yusuf","İsmail",
    "Recep","Murat","Kemal","Serkan","Burak","Emre","Onur","Tolga","Berk","Cem",
    "Umut","Volkan","Uğur","Selim","Ozan","Tarık","Kadir","Fırat","Ercan","Rıza",
    "Sinan","Tuncay","Yasin","Zafer","Arif","Bayram","Cüneyt","Doğan","Enver","Fikret",
    "Gökhan","Halil","İlhan","Kürşat","Levent","Nevzat","Orhan","Ramazan","Savaş","Tamer",
    "Ufuk","Veysel","Yıldıray","Zeki","Adnan","Bahadır","Celal","Dursun","Ertuğrul","Faruk"
]

SOYADLAR = [
    "Yılmaz","Kaya","Demir","Şahin","Çelik","Yıldız","Yıldırım","Öztürk","Arslan","Doğan",
    "Kılıç","Aslan","Çetin","Koç","Kurt","Aydın","Özdemir","Şimşek","Bulut","Erdoğan",
    "Güneş","Acar","Polat","Aksoy","Karahan","Ateş","Kara","Keskin","Korkmaz","Bozkurt",
    "Efe","Güler","Işık","Kaplan","Mutlu","Özcan","Sönmez","Tanrıverdi","Uysal","Yücel",
    "Altın","Başar","Candan","Demirtaş","Ekinci","Güngör","Hacıoğlu","İnce","Karakaya","Lale",
    "Mercan","Nas","Oral","Parlak","Sezgin","Tekin","Uçar","Varol","Zor","Akbulut",
    "Bıyık","Cin","Duman","Eren","Fidan","Göktaş","Havuç","Irgat","Kaptan","Kesen",
    "Macit","Nalbant","Oruç","Pala","Reyhan","Saka","Taş","Uluç","Vardar","Zorlu",
    "Aba","Baş","Çakır","Dinç","Erdem","Gürbüz","Hanım","İlhan","Kaygı","Kuzu",
    "Mollaoğlu","Nacar","Özer","Saraç","Tunç","Uzun","Vural","Yaman","Zeren","Altay"
]

import random
random.seed(42)  # Tekrarlanabilirlik

def rastgele_ad(cinsiyet: str) -> str:
    if cinsiyet == 'K':
        return random.choice(KADIN_ADLAR)
    return random.choice(ERKEK_ADLAR)

def rastgele_soyad() -> str:
    return random.choice(SOYADLAR)

# ------------------------------------------------------------
# Kayıt oluşturma
# ------------------------------------------------------------
db = SessionLocal()

try:
    # Mevcut seed kayıtlarını temizle (700001–701000 arası sicil)
    mevcut_k = db.query(models.Kiyafet).filter(
        models.Kiyafet.rfid_tag >= "100001",
        models.Kiyafet.rfid_tag <= "101000"
    ).count()

    mevcut_c = db.query(models.Calisan).filter(
        models.Calisan.sicil_numarasi >= "700001",
        models.Calisan.sicil_numarasi <= "701000"
    ).count()

    if mevcut_c > 0 or mevcut_k > 0:
        print(f"UYARI: Bu aralıkta zaten {mevcut_c} calisan ve {mevcut_k} kiyafet kaydı var.")
        print("Temizleniyor...")
        db.query(models.Kiyafet).filter(
            models.Kiyafet.rfid_tag >= "100001",
            models.Kiyafet.rfid_tag <= "101000"
        ).delete()
        db.query(models.Calisan).filter(
            models.Calisan.sicil_numarasi >= "700001",
            models.Calisan.sicil_numarasi <= "701000"
        ).delete()
        db.commit()

    # Sıralı sicil listesi: 700001..701000
    sicil_listesi = [str(700001 + i) for i in range(1000)]

    # 500 K + 500 E, sicil sırasına göre karıştırılmış
    cinsiyetler = ['K'] * 500 + ['E'] * 500
    random.shuffle(cinsiyetler)  # %50-%50 rastgele dağılım

    calisanlar = []
    kiyafetler = []

    for i, sicil in enumerate(sicil_listesi):
        cinsiyet = cinsiyetler[i]
        rfid = str(100001 + i)

        calisan = models.Calisan(
            sicil_numarasi=sicil,
            ad=rastgele_ad(cinsiyet),
            soyad=rastgele_soyad(),
            cinsiyet=cinsiyet
        )
        kiyafet = models.Kiyafet(
            rfid_tag=rfid,
            sicil_numarasi=sicil
        )
        calisanlar.append(calisan)
        kiyafetler.append(kiyafet)

    db.bulk_save_objects(calisanlar)
    db.flush()
    db.bulk_save_objects(kiyafetler)
    db.commit()

    k_count = sum(1 for c in cinsiyetler if c == 'K')
    e_count = sum(1 for c in cinsiyetler if c == 'E')

    print(f"\n✓ {len(calisanlar)} calisan eklendi")
    print(f"  - Kadın: {k_count}")
    print(f"  - Erkek: {e_count}")
    print(f"✓ {len(kiyafetler)} RFID eslesme kaydı eklendi")
    print(f"  - RFID aralığı: 100001 → 101000")
    print(f"  - Sicil aralığı: 700001 → 701000")

    # Özet
    print("\n--- Raf Kapasitesi Özeti ---")
    print("8 raf (A-H), 7 kat, 5 bölme")
    print("Kat 1-6: 3 kıyafet/bölme | Kat 7: 1 kıyafet/bölme")
    per_raf = (6 * 5 * 3) + (1 * 5 * 1)
    toplam = 8 * per_raf
    print(f"Raf başına kapasite: {per_raf}")
    print(f"Toplam kapasite: {toplam}")
    print(f"Kadın rafı (E): {per_raf} | Erkek rafları (A,B,C,D,F,G,H): {7 * per_raf}")

finally:
    db.close()
