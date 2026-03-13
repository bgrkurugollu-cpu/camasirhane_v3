from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, date, timezone, timedelta
from typing import List
import os
import uuid

from fastapi.security import OAuth2PasswordRequestForm
from . import models, schemas, database, security

app = FastAPI(title="Çamaşırhane Otomasyon Sistemi API")

models.Base.metadata.create_all(bind=database.engine)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("app/static/index.html")

@app.post("/api/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    """
    Kullanıcının sisteme giriş (Login) yaptığı uç noktadır.
    Girilen kullanıcı adı ve şifresinin DB'deki hash ile eşleşip eşleşmediğini kontrol eder
    ve başarılıysa Access_Token (JWT) döner.
    """
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Kullanıcı adı veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    """Sisteme giriş yapmış olan kullanıcının (kendisinin) profil bilgilerini döndürür."""
    return current_user

@app.put("/api/users/me", response_model=schemas.UserResponse)
def update_user_me(data: schemas.UserProfileUpdate, db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    if data.email is not None: current_user.email = data.email
    if data.phone is not None: current_user.phone = data.phone
    if data.title is not None: current_user.title = data.title
    if data.company is not None: current_user.company = data.company
    if data.password:
        current_user.hashed_password = security.get_password_hash(data.password)
        
    db.commit()
    db.refresh(current_user)
    return current_user

@app.post("/api/users/me/photo", response_model=schemas.UserResponse)
async def upload_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Kullanıcının profil fotoğrafını günceller. Sadece PNG formatı kabul edilir."""
    if file.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Sadece .png formatında resim yükleyebilirsiniz.")
    
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Dosya boyutu çok büyük! Maksimum 2MB yükleyebilirsiniz.")
    
    os.makedirs("app/static/avatars", exist_ok=True)
    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.png"
    filepath = f"app/static/avatars/{filename}"
    
    with open(filepath, "wb") as f:
        f.write(contents)
        
    current_user.profile_photo = f"/static/avatars/{filename}"
    db.commit()
    db.refresh(current_user)
    
    return current_user

@app.get("/api/users", response_model=List[schemas.UserResponse])
def get_all_users(db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sadece adminler tüm kullanıcıları görebilir.")
    return db.query(models.User).all()

@app.put("/api/users/{user_id}", response_model=schemas.UserResponse)
def update_user_by_admin(user_id: int, data: schemas.UserProfileUpdate, db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sadece adminler diğer kullanıcıları düzenleyebilir.")
        
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")
        
    if data.email is not None: user.email = data.email
    if data.phone is not None: user.phone = data.phone
    if data.title is not None: user.title = data.title
    if data.company is not None: user.company = data.company
    if data.password:
        user.hashed_password = security.get_password_hash(data.password)
        
    db.commit()
    db.refresh(user)
    return user

@app.post("/api/islem", response_model=dict)
def process_islem(req: schemas.IslemRequest, db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    """
    Çamaşırhaneye getirilen kirli kıyafetin sisteme RFID okutularak veya manüel kayıt edilmesini veya
    doğrudan Temiz / Teslim durumuna geçirilmesini sağlar. Modeline göre Kirli/Teslim/Temiz db lerinden birine Insert atar.
    """
    rfid_tag = req.rfid_tag
    sicil_numarasi = req.sicil_numarasi
    
    # Mevcut çalışan veya kıyafet kontrolü MVP için esnek bırakıldı.
    # Girilen iki bilgiyi doğrudan veritabanına alıyoruz.
    
    now_utc = datetime.now(timezone.utc)
    if req.islem_tipi == 'kirli':
        yeni_islem = models.Kirli_Kiyafet(rfid_tag=rfid_tag, sicil_numarasi=sicil_numarasi, zaman_damgasi=now_utc)
    elif req.islem_tipi == 'temiz':
        # Legacy support just in case, though UI won't send this anymore
        yeni_islem = models.Temiz_Kiyafet(rfid_tag=rfid_tag, sicil_numarasi=sicil_numarasi, zaman_damgasi=now_utc)
    elif req.islem_tipi == 'teslim':
        yeni_islem = models.Teslim_Edilen(rfid_tag=rfid_tag, sicil_numarasi=sicil_numarasi, zaman_damgasi=now_utc)
    else:
        raise HTTPException(status_code=400, detail="Geçersiz işlem tipi")

    db.add(yeni_islem)
    db.commit()
    db.refresh(yeni_islem)

    return {"message": "İşlem başarılı", "islem_id": yeni_islem.islem_id}

@app.post("/api/islem/onayla")
def onayla_islem(req: schemas.IslemOnayRequest, db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    """
    "Kirli Bekleyenler" tablosundaki bir kıyafetin yıkanma süreci bittiğinde çağrılır.
    Veritabanında önceden var olan islem_id yi bulur, bunu kirli tablosundan silip, 
    Temizlendi ve Teslime Hazır anlamında teslim tablosuna aktarır.
    """
    kirli_kayit = db.query(models.Kirli_Kiyafet).filter(models.Kirli_Kiyafet.islem_id == req.islem_id).first()
    
    if not kirli_kayit:
        raise HTTPException(status_code=404, detail="Kirli kayıt bulunamadı")
        
    now_utc = datetime.now(timezone.utc)
    
    # Create the teslim record
    yeni_teslim = models.Teslim_Edilen(
        rfid_tag=kirli_kayit.rfid_tag, 
        sicil_numarasi=kirli_kayit.sicil_numarasi, 
        zaman_damgasi=now_utc
    )
    
    db.add(yeni_teslim)
    db.delete(kirli_kayit)
    db.commit()
    
    return {"message": "Kıyafet temizlendi ve teslime hazır.", "yeni_islem_id": yeni_teslim.islem_id}

@app.get("/api/stats", response_model=schemas.StatsResponse)
def get_stats(db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    # Very basic date filter conceptually starting exactly at midnight 
    bugun = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    kirli = db.query(models.Kirli_Kiyafet).filter(models.Kirli_Kiyafet.zaman_damgasi >= bugun).count()
    temiz = db.query(models.Temiz_Kiyafet).filter(models.Temiz_Kiyafet.zaman_damgasi >= bugun).count()
    teslim = db.query(models.Teslim_Edilen).filter(models.Teslim_Edilen.zaman_damgasi >= bugun).count()
    
    return schemas.StatsResponse(kirli_bugun=kirli, temiz_bugun=temiz, teslim_bugun=teslim)

@app.get("/api/stats/history", response_model=schemas.HistoryStatsResponse)
def get_stats_history(period: str = "weekly", db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    """
    Ana ekrandaki Grafik Bar Chartlar için geriye dönük (gün gün) işlem tarihlerini döngü ile hesaplar.
    Son 7 ("weekly") veya 30 ("monthly") günü filtreleyip ilgili günlerde kaç kirli/temiz kayıt atıldığını sayar.
    Chart.js formatına (labels ve veriler) hazırlayarak dictionary şeklinde Frontende gönderir.
    """
    now = datetime.now(timezone.utc)
    
    if period == "weekly":
        days = 7
    elif period == "monthly":
        days = 30
    else:
        raise HTTPException(status_code=400, detail="Geçersiz periyot")

    start_date = (now - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    kirli_records = db.query(models.Kirli_Kiyafet).filter(models.Kirli_Kiyafet.zaman_damgasi >= start_date).all()
    temiz_records = db.query(models.Temiz_Kiyafet).filter(models.Temiz_Kiyafet.zaman_damgasi >= start_date).all()
    teslim_records = db.query(models.Teslim_Edilen).filter(models.Teslim_Edilen.zaman_damgasi >= start_date).all()
    
    # Initialize dictionary with all days set to 0
    daily_stats = {}
    for i in range(days):
        dt = (start_date + timedelta(days=i))
        # Use dd.mm format for labels
        date_str = f"{dt.day:02d}.{dt.month:02d}"
        daily_stats[date_str] = {"kirli": 0, "temiz": 0, "teslim": 0}
        
    # Python Döngüsü: db'den dönen kirli raw veriler (kirli_records) içerisinde her bir kayıt için geziyoruz
    # İlgili kaydın tarihi (dt_str), daily_stats sözlüğümüzde boş oluşturulmuş kovalara denk geliyorsa onu +1 artırıyoruz (+1 Sayım)
    for rec in kirli_records:
        if rec.zaman_damgasi:
            dt_str = f"{rec.zaman_damgasi.day:02d}.{rec.zaman_damgasi.month:02d}"
            if dt_str in daily_stats:
                daily_stats[dt_str]["kirli"] += 1

    for rec in temiz_records:
        if rec.zaman_damgasi:
            dt_str = f"{rec.zaman_damgasi.day:02d}.{rec.zaman_damgasi.month:02d}"
            if dt_str in daily_stats:
                daily_stats[dt_str]["temiz"] += 1
                
    for rec in teslim_records:
        if rec.zaman_damgasi:
            dt_str = f"{rec.zaman_damgasi.day:02d}.{rec.zaman_damgasi.month:02d}"
            if dt_str in daily_stats:
                daily_stats[dt_str]["teslim"] += 1

    labels = list(daily_stats.keys())
    kirli_data = [d["kirli"] for d in daily_stats.values()]
    temiz_data = [d["temiz"] for d in daily_stats.values()]
    teslim_data = [d["teslim"] for d in daily_stats.values()]

    return schemas.HistoryStatsResponse(
        labels=labels,
        kirli_data=kirli_data,
        temiz_data=temiz_data,
        teslim_data=teslim_data
    )

@app.get("/api/tablo/{islem_tipi}")
def get_tablo(islem_tipi: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    if islem_tipi == 'teslim' and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Sadece admin geçmiş kayıtları görebilir.")

    if islem_tipi == 'kirli':
        kayitlar = db.query(models.Kirli_Kiyafet).order_by(models.Kirli_Kiyafet.zaman_damgasi.desc()).limit(50).all()
    elif islem_tipi == 'temiz':
        kayitlar = db.query(models.Temiz_Kiyafet).order_by(models.Temiz_Kiyafet.zaman_damgasi.desc()).limit(50).all()
    elif islem_tipi == 'teslim':
        kayitlar = db.query(models.Teslim_Edilen).order_by(models.Teslim_Edilen.zaman_damgasi.desc()).limit(50).all()
    else:
        raise HTTPException(status_code=400, detail="Geçersiz işlem tipi")
    
    return kayitlar

@app.post("/api/init_mock_data")
def init_mock(db: Session = Depends(database.get_db)):
    if db.query(models.User).count() == 0:
        admin_user = models.User(
            username="admin", 
            hashed_password=security.get_password_hash("admin"), 
            role="admin",
            title="Sistem Yöneticisi",
            company="Yıldız Tech",
            email="admin@yildiz.tech"
        )
        standart_user = models.User(
            username="user", 
            hashed_password=security.get_password_hash("user"), 
            role="user",
            title="Görevli",
            company="Yıldız Tech"
        )
        db.add_all([admin_user, standart_user])
        db.commit()

    if db.query(models.Calisan).count() == 0:
        c1 = models.Calisan(sicil_numarasi="1001", ad="Ahmet", soyad="Yılmaz")
        c2 = models.Calisan(sicil_numarasi="1002", ad="Ayşe", soyad="Demir")
        db.add_all([c1, c2])
        db.commit()

        k1 = models.Kiyafet(rfid_tag="RFID-001", sicil_numarasi="1001")
        k2 = models.Kiyafet(rfid_tag="RFID-002", sicil_numarasi="1002")
        db.add_all([k1, k2])
        db.commit()
        return {"message": "Mock veriler ve kullanıcılar(admin, user) eklendi."}
    return {"message": "Mock veriler zaten mevcut."}
    return {"message": "Veriler zaten mevcut."}
