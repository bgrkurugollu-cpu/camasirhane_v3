from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, text
from datetime import datetime, date, timezone, timedelta
from typing import List, Optional
import os
import uuid
import time

from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from . import models, schemas, database, security

app = FastAPI(title="Çamaşırhane Otomasyon Sistemi API")

# Rate limiter – IP bazlı istek sınırlama
limiter = Limiter(key_func=lambda request: get_client_ip(request))
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

models.Base.metadata.create_all(bind=database.engine)

_startup_time = time.time()

# ---------------------------------------------------------------------------
# Yardımcı: Audit Log kayıt fonksiyonu
# ---------------------------------------------------------------------------

def write_audit_log(
    db: Session,
    action: str,
    username: Optional[str] = None,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
    status: str = "success"
):
    """Verilen bilgileri audit_logs tablosuna yazar."""
    log = models.AuditLog(
        action=action,
        username=username,
        detail=detail,
        ip_address=ip_address,
        status=status,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log)
    db.commit()

def get_client_ip(request: Request) -> str:
    """İstemcinin IP adresini döndürür (proxy arkasında da çalışır)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    db = database.SessionLocal()
    try:
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
    finally:
        db.close()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("app/static/index.html")

# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    """
    Kimlik doğrulama gerektirmeden sistemin genel sağlık durumunu döndürür.
    Veritabanı bağlantısını test eder ve temel sistem metriklerini raporlar.
    """
    now = datetime.now(timezone.utc)
    uptime_seconds = int(time.time() - _startup_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}sa {minutes}dk {seconds}sn"

    # Veritabanı bağlantı kontrolü
    db_status = "healthy"
    db_latency_ms = None
    db_error = None
    try:
        db = database.SessionLocal()
        t0 = time.time()
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - t0) * 1000, 2)
        db.close()
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)

    # Tablo satır sayıları
    table_counts = {}
    try:
        db = database.SessionLocal()
        table_counts = {
            "calisanlar": db.query(models.Calisan).count(),
            "kiyafetler": db.query(models.Kiyafet).count(),
            "kirli_bekleyen": db.query(models.Kirli_Kiyafet).count(),
            "temiz_rafta": db.query(models.Temiz_Kiyafet).count(),
            "teslim_edilmis": db.query(models.Teslim_Edilen).count(),
            "kullanicilar": db.query(models.User).count(),
        }
        db.close()
    except Exception:
        pass

    overall = "healthy" if db_status == "healthy" else "unhealthy"

    result = {
        "status": overall,
        "timestamp": now.isoformat(),
        "uptime": uptime_str,
        "uptime_seconds": uptime_seconds,
        "database": {
            "status": db_status,
            "latency_ms": db_latency_ms,
        },
        "table_counts": table_counts,
    }
    if db_error:
        result["database"]["error"] = db_error

    return result

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/api/token", response_model=schemas.Token)
@limiter.limit("10/minute")
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    """
    Kullanıcının sisteme giriş (Login) yaptığı uç noktadır.
    Başarılı ve başarısız girişler audit log'a kaydedilir.
    """
    ip = get_client_ip(request)
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        write_audit_log(
            db=db,
            action="LOGIN_FAIL",
            username=form_data.username,
            detail="Hatalı kullanıcı adı veya şifre",
            ip_address=ip,
            status="fail"
        )
        raise HTTPException(
            status_code=401,
            detail="Kullanıcı adı veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = security.create_access_token(data={"sub": user.username})
    write_audit_log(
        db=db,
        action="LOGIN_SUCCESS",
        username=user.username,
        detail=f"Rol: {user.role}",
        ip_address=ip,
        status="success"
    )
    return {"access_token": access_token, "token_type": "bearer"}

# ---------------------------------------------------------------------------
# Kullanıcı Profili
# ---------------------------------------------------------------------------

@app.get("/api/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    """Sisteme giriş yapmış olan kullanıcının (kendisinin) profil bilgilerini döndürür."""
    return current_user

@app.put("/api/users/me", response_model=schemas.UserResponse)
def update_user_me(
    request: Request,
    data: schemas.UserProfileUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    ip = get_client_ip(request)
    if data.email is not None: current_user.email = data.email
    if data.phone is not None: current_user.phone = data.phone
    if data.title is not None: current_user.title = data.title
    if data.company is not None: current_user.company = data.company
    if data.password:
        current_user.hashed_password = security.get_password_hash(data.password)

    db.commit()
    db.refresh(current_user)

    write_audit_log(
        db=db,
        action="PROFILE_UPDATE",
        username=current_user.username,
        detail="Kendi profilini güncelledi",
        ip_address=ip,
        status="success"
    )
    return current_user

@app.post("/api/users/me/photo", response_model=schemas.UserResponse)
@limiter.limit("10/minute")
async def upload_profile_photo(
    request: Request,
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

# ---------------------------------------------------------------------------
# Admin: Kullanıcı Yönetimi
# ---------------------------------------------------------------------------

@app.get("/api/users", response_model=List[schemas.UserResponse])
def get_all_users(db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sadece adminler tüm kullanıcıları görebilir.")
    return db.query(models.User).all()

@app.post("/api/users", response_model=schemas.UserResponse)
def create_user_by_admin(
    request: Request,
    data: schemas.UserCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sadece adminler yeni kullanıcı oluşturabilir.")
    
    existing_user = db.query(models.User).filter(models.User.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten alınmış.")
        
    hashed_pwd = security.get_password_hash(data.password)
    new_user = models.User(
        username=data.username,
        hashed_password=hashed_pwd,
        role=data.role,
        title=data.title,
        company=data.company,
        email=data.email,
        phone=data.phone
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    write_audit_log(
        db=db,
        action="USER_CREATE",
        username=current_user.username,
        detail=f"Yeni kullanıcı: {new_user.username} (rol: {new_user.role})",
        ip_address=get_client_ip(request),
        status="success"
    )
    return new_user

@app.delete("/api/users/{user_id}")
def delete_user_by_admin(
    user_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sadece adminler kullanıcı silebilir.")
        
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")
        
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Kendi kendinizi silemezsiniz.")

    deleted_username = user.username
    db.delete(user)
    db.commit()

    write_audit_log(
        db=db,
        action="USER_DELETE",
        username=current_user.username,
        detail=f"Silinen kullanıcı: {deleted_username}",
        ip_address=get_client_ip(request),
        status="success"
    )
    return {"message": "Kullanıcı başarıyla silindi."}

@app.put("/api/users/{user_id}", response_model=schemas.UserResponse)
def update_user_by_admin(
    user_id: int,
    request: Request,
    data: schemas.UserProfileUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
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

    write_audit_log(
        db=db,
        action="USER_UPDATE",
        username=current_user.username,
        detail=f"Güncellenen kullanıcı: {user.username}",
        ip_address=get_client_ip(request),
        status="success"
    )
    return user

# ---------------------------------------------------------------------------
# İşlem Kayıtları
# ---------------------------------------------------------------------------

RACK_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
RACK_FLOORS = 7
RACK_COMPARTMENTS = 5

def get_compartment_capacity(floor: int) -> int:
    """Kat kapasitesini döndürür: 7. kat (en üst) 1, diğerleri 3."""
    return 1 if floor == 7 else 3

def assign_shelf(db: Session, cinsiyet: Optional[str] = None) -> Optional[str]:
    """Cinsiyete göre raf atar. Kadın → E rafı, Erkek → A-D,F-H rafları."""
    occupancy = db.query(
        models.Temiz_Kiyafet.raf_id,
        func.count(models.Temiz_Kiyafet.islem_id)
    ).filter(models.Temiz_Kiyafet.raf_id != None).group_by(models.Temiz_Kiyafet.raf_id).all()

    occupancy_dict = {raf_id: count for raf_id, count in occupancy}

    if cinsiyet == 'K':
        letters = ['E']
    else:
        letters = [l for l in RACK_LETTERS if l != 'E']

    for letter in letters:
        for floor in range(1, RACK_FLOORS + 1):
            cap = get_compartment_capacity(floor)
            for comp in range(1, RACK_COMPARTMENTS + 1):
                raf_id = f"{letter}{floor}{comp}"
                if occupancy_dict.get(raf_id, 0) < cap:
                    return raf_id
    return None

@app.get("/api/calisan/{sicil_numarasi}", response_model=dict)
def get_calisan(
    sicil_numarasi: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    calisan = db.query(models.Calisan).filter(models.Calisan.sicil_numarasi == sicil_numarasi).first()
    if not calisan:
        raise HTTPException(status_code=404, detail="Calisan bulunamadı")
    return {
        "sicil_numarasi": calisan.sicil_numarasi,
        "ad": calisan.ad,
        "soyad": calisan.soyad,
        "cinsiyet": calisan.cinsiyet
    }

@app.post("/api/kiyafet", response_model=dict)
def register_kiyafet(
    request: Request,
    req: schemas.KiyafetCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sadece adminler RFID eşleştirmesi yapabilir.")
        
    ip = get_client_ip(request)
    
    calisan = db.query(models.Calisan).filter(models.Calisan.sicil_numarasi == req.sicil_numarasi).first()
    if not calisan:
        if not req.ad or not req.soyad:
            raise HTTPException(status_code=400, detail="Yeni personel kaydı için Ad ve Soyad zorunludur.")
        yeni_calisan = models.Calisan(
            sicil_numarasi=req.sicil_numarasi,
            ad=req.ad,
            soyad=req.soyad,
            cinsiyet=req.cinsiyet
        )
        db.add(yeni_calisan)
        db.commit()
    
    existing = db.query(models.Kiyafet).filter(models.Kiyafet.rfid_tag == req.rfid_tag).first()
    if existing:
        existing.sicil_numarasi = req.sicil_numarasi
        action_log = "RFID_UPDATE"
    else:
        yeni_kiyafet = models.Kiyafet(rfid_tag=req.rfid_tag, sicil_numarasi=req.sicil_numarasi)
        db.add(yeni_kiyafet)
        action_log = "RFID_REGISTER"
        
    db.commit()

    write_audit_log(
        db=db,
        action=action_log,
        username=current_user.username,
        detail=f"RFID: {req.rfid_tag} -> Sicil: {req.sicil_numarasi}",
        ip_address=ip,
        status="success"
    )
    return {"message": "RFID eşleştirmesi başarılı."}

@app.put("/api/kiyafet/{old_rfid_tag}", response_model=dict)
def update_kiyafet(
    old_rfid_tag: str,
    req: schemas.KiyafetCreate,
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sadece adminler RFID eşleştirmesi güncelleyebilir.")
        
    kayit = db.query(models.Kiyafet).filter(models.Kiyafet.rfid_tag == old_rfid_tag).first()
    if not kayit:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
        
    if old_rfid_tag != req.rfid_tag:
        conflict = db.query(models.Kiyafet).filter(models.Kiyafet.rfid_tag == req.rfid_tag).first()
        if conflict:
             raise HTTPException(status_code=400, detail="Yeni girilen RFID Tag zaten başka bir sicille eşleşmiş.")
             
        db.query(models.Kiyafet).filter(models.Kiyafet.rfid_tag == old_rfid_tag).update(
            {models.Kiyafet.rfid_tag: req.rfid_tag, models.Kiyafet.sicil_numarasi: req.sicil_numarasi}
        )
    else:
        kayit.sicil_numarasi = req.sicil_numarasi
        
    db.commit()
    write_audit_log(db=db, action="RFID_MATCH_UPDATE", detail=f"Önceki: {old_rfid_tag} -> Yeni Tag: {req.rfid_tag}, Sicil: {req.sicil_numarasi}", ip_address=get_client_ip(request), username=current_user.username)
    return {"status": "success"}

@app.delete("/api/kiyafet/{rfid_tag}", response_model=dict)
def delete_kiyafet(
    rfid_tag: str,
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sadece adminler RFID eşleştirmesi silebilir.")
        
    kayit = db.query(models.Kiyafet).filter(models.Kiyafet.rfid_tag == rfid_tag).first()
    if not kayit:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
        
    db.delete(kayit)
    db.commit()
    write_audit_log(db=db, action="RFID_MATCH_DELETE", detail=f"Silinen: RFID Tag {rfid_tag}, Sicil: {kayit.sicil_numarasi}", ip_address=get_client_ip(request), username=current_user.username)
    return {"status": "success"}

@app.post("/api/islem/rfid-oku")
def rfid_oku(
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Kirli sepetini simüle eder: RFID listesindeki kişilerden henüz kirli bekleyenlerde
    olmayan rastgele 10 tanesini seçip kirli_kiyafetler tablosuna ekler.
    Tüm kişiler zaten eklenmişse 'sepet boş' uyarısı döner.
    """
    import random

    # Kirli bekleyenlerdeki mevcut sicil numaraları
    kirli_siciller = {
        r.sicil_numarasi
        for r in db.query(models.Kirli_Kiyafet.sicil_numarasi).all()
    }

    # RFID listesindeki tüm kişilerden kirli olmayanları bul
    aday_kayitlar = (
        db.query(models.Kiyafet, models.Calisan)
        .join(models.Calisan, models.Kiyafet.sicil_numarasi == models.Calisan.sicil_numarasi)
        .filter(models.Kiyafet.sicil_numarasi.notin_(kirli_siciller))
        .all()
    )

    if not aday_kayitlar:
        return {"durum": "bos", "mesaj": "Kirli sepetinde yeni kıyafet bulunamadı!", "eklenenler": []}

    secilen = random.sample(aday_kayitlar, min(10, len(aday_kayitlar)))

    now_utc = datetime.now(timezone.utc)
    ip = get_client_ip(request)
    eklenenler = []

    for kiyafet, calisan in secilen:
        yeni = models.Kirli_Kiyafet(
            rfid_tag=kiyafet.rfid_tag,
            sicil_numarasi=kiyafet.sicil_numarasi,
            zaman_damgasi=now_utc
        )
        db.add(yeni)
        db.flush()
        eklenenler.append({
            "islem_id": yeni.islem_id,
            "rfid_tag": kiyafet.rfid_tag,
            "sicil_numarasi": kiyafet.sicil_numarasi,
            "ad_soyad": f"{calisan.ad} {calisan.soyad}",
            "cinsiyet": calisan.cinsiyet,
            "zaman_damgasi": now_utc.isoformat()
        })

    db.commit()

    write_audit_log(
        db=db, action="KIRLI_GIRIS",
        username=current_user.username,
        detail=f"RFID Oku: {len(eklenenler)} kıyafet kirli sepetine eklendi",
        ip_address=ip, status="success"
    )

    kalan = len(aday_kayitlar) - len(secilen)
    return {"durum": "ok", "eklenenler": eklenenler, "kalan_aday": kalan}


@app.post("/api/islem", response_model=dict)
@limiter.limit("60/minute")
def process_islem(
    request: Request,
    req: schemas.IslemRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Çamaşırhaneye getirilen kirli kıyafetin sisteme RFID okutularak veya manüel kayıt edilmesini veya
    doğrudan Temiz / Teslim durumuna geçirilmesini sağlar.
    """
    rfid_tag = req.rfid_tag
    ip = get_client_ip(request)

    now_utc = datetime.now(timezone.utc)
    if req.islem_tipi == 'kirli':
        kiyafet = db.query(models.Kiyafet).filter(models.Kiyafet.rfid_tag == rfid_tag).first()
        if not kiyafet:
            raise HTTPException(status_code=404, detail="Bu RFID tag sisteme kayıtlı değil. Lütfen önce eşleştirin.")
        sicil_numarasi = kiyafet.sicil_numarasi
        yeni_islem = models.Kirli_Kiyafet(rfid_tag=rfid_tag, sicil_numarasi=sicil_numarasi, zaman_damgasi=now_utc)
        action_log = "KIRLI_GIRIS"
    elif req.islem_tipi == 'temiz':
        calisan = db.query(models.Calisan).filter(models.Calisan.sicil_numarasi == req.sicil_numarasi).first()
        cinsiyet = calisan.cinsiyet if calisan else None
        raf_id = assign_shelf(db, cinsiyet=cinsiyet)
        if raf_id is None:
            raise HTTPException(status_code=400, detail="Tüm raflar dolu! Sistem yeni temiz kıyafet kabul edemiyor.")
        yeni_islem = models.Temiz_Kiyafet(rfid_tag=rfid_tag, sicil_numarasi=req.sicil_numarasi, zaman_damgasi=now_utc, raf_id=raf_id)
        action_log = "TEMIZ_GIRIS"
    elif req.islem_tipi == 'teslim':
        yeni_islem = models.Teslim_Edilen(rfid_tag=rfid_tag, sicil_numarasi=req.sicil_numarasi, zaman_damgasi=now_utc)
        action_log = "TESLIM_GIRIS"
    else:
        raise HTTPException(status_code=400, detail="Geçersiz işlem tipi")

    db.add(yeni_islem)
    db.commit()
    db.refresh(yeni_islem)

    write_audit_log(
        db=db,
        action=action_log,
        username=current_user.username,
        detail=f"RFID: {rfid_tag} | Sicil: {sicil_numarasi}",
        ip_address=ip,
        status="success"
    )
    return {"message": "İşlem başarılı", "islem_id": yeni_islem.islem_id}

@app.post("/api/islem/onayla")
def onayla_islem(
    request: Request,
    req: schemas.IslemOnayRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    'Kirli Bekleyenler' tablosundaki bir kıyafetin yıkanması tamamlandığında çağrılır.
    Kirli tablosundan siler, Temiz_Kiyafet tablosuna aktarır.
    """
    kirli_kayit = db.query(models.Kirli_Kiyafet).filter(models.Kirli_Kiyafet.islem_id == req.islem_id).first()

    if not kirli_kayit:
        raise HTTPException(status_code=404, detail="Kirli kayıt bulunamadı")

    calisan = db.query(models.Calisan).filter(models.Calisan.sicil_numarasi == kirli_kayit.sicil_numarasi).first()
    cinsiyet = calisan.cinsiyet if calisan else None
    raf_id = assign_shelf(db, cinsiyet=cinsiyet)
    if raf_id is None:
        raise HTTPException(status_code=400, detail="Uygun raf bulunamadı! Kapasite dolu.")
        
    now_utc = datetime.now(timezone.utc)
    
    yeni_temiz = models.Temiz_Kiyafet(
        rfid_tag=kirli_kayit.rfid_tag, 
        sicil_numarasi=kirli_kayit.sicil_numarasi, 
        zaman_damgasi=now_utc,
        raf_id=raf_id
    )
    
    db.add(yeni_temiz)
    db.delete(kirli_kayit)
    db.commit()

    write_audit_log(
        db=db,
        action="ISLEM_ONAYLA",
        username=current_user.username,
        detail=f"İşlem ID: {req.islem_id} | RFID: {kirli_kayit.rfid_tag} onaylandı (Temiz)",
        ip_address=get_client_ip(request),
        status="success"
    )
    return {"message": "Kıyafet temizlendi ve teslime hazır.", "yeni_islem_id": yeni_temiz.islem_id}

@app.post("/api/islem/teslim")
def teslim_et(
    request: Request,
    req: schemas.TeslimRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    temiz_kayit = db.query(models.Temiz_Kiyafet).filter(models.Temiz_Kiyafet.islem_id == req.islem_id).first()
    
    if not temiz_kayit:
        raise HTTPException(status_code=404, detail="Temiz kayıt bulunamadı veya daha önce teslim edilmiş.")
        
    if temiz_kayit.sicil_numarasi != req.sicil_numarasi:
        raise HTTPException(status_code=400, detail=f"Hata: Sicil numarası eşleşmiyor. Kayıtlı Sicil: {temiz_kayit.sicil_numarasi}, Girilen: {req.sicil_numarasi}")
        
    now_utc = datetime.now(timezone.utc)
    
    yeni_teslim = models.Teslim_Edilen(
        rfid_tag=temiz_kayit.rfid_tag, 
        sicil_numarasi=temiz_kayit.sicil_numarasi, 
        zaman_damgasi=now_utc,
        raf_id=temiz_kayit.raf_id
    )
    
    db.add(yeni_teslim)
    db.delete(temiz_kayit)
    db.commit()

    write_audit_log(
        db=db,
        action="TESLIM_GIRIS",
        username=current_user.username,
        detail=f"İşlem ID: {req.islem_id} | RFID: {temiz_kayit.rfid_tag} Teslim edildi",
        ip_address=get_client_ip(request),
        status="success"
    )
    return {"message": "Kıyafet başarıyla teslim edildi.", "yeni_islem_id": yeni_teslim.islem_id}

# ---------------------------------------------------------------------------
# İstatistikler
# ---------------------------------------------------------------------------

@app.get("/api/stats", response_model=schemas.StatsResponse)
def get_stats(db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    bugun = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    kirli = db.query(models.Kirli_Kiyafet).filter(models.Kirli_Kiyafet.zaman_damgasi >= bugun).count()
    temiz = db.query(models.Temiz_Kiyafet).filter(models.Temiz_Kiyafet.zaman_damgasi >= bugun).count()
    teslim = db.query(models.Teslim_Edilen).filter(models.Teslim_Edilen.zaman_damgasi >= bugun).count()
    
    return schemas.StatsResponse(kirli_bugun=kirli, temiz_bugun=temiz, teslim_bugun=teslim)

@app.get("/api/stats/raflar", response_model=dict)
def get_raf_stats(db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    """Tüm rafların bölme bazında doluluk durumunu döndürür."""
    occupancy = db.query(
        models.Temiz_Kiyafet.raf_id,
        func.count(models.Temiz_Kiyafet.islem_id)
    ).filter(models.Temiz_Kiyafet.raf_id != None).group_by(models.Temiz_Kiyafet.raf_id).all()

    occupancy_dict = {raf_id: count for raf_id, count in occupancy}

    result = {}
    for letter in RACK_LETTERS:
        rack_data = {}
        for floor in range(1, RACK_FLOORS + 1):
            cap = get_compartment_capacity(floor)
            for comp in range(1, RACK_COMPARTMENTS + 1):
                raf_id = f"{letter}{floor}{comp}"
                rack_data[raf_id] = {
                    "count": occupancy_dict.get(raf_id, 0),
                    "capacity": cap
                }
        result[letter] = rack_data
    return result

@app.get("/api/stats/raf-detay/{rack_letter}")
def get_raf_detail(
    rack_letter: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Belirli bir raftaki (A-H) tüm bölmelerdeki kıyafet detaylarını döndürür."""
    rack_letter = rack_letter.upper()
    if rack_letter not in RACK_LETTERS:
        raise HTTPException(status_code=400, detail="Geçersiz raf harfi. A-H arası olmalıdır.")

    items = (
        db.query(models.Temiz_Kiyafet, models.Calisan)
        .outerjoin(models.Calisan, models.Temiz_Kiyafet.sicil_numarasi == models.Calisan.sicil_numarasi)
        .filter(models.Temiz_Kiyafet.raf_id.like(f"{rack_letter}%"))
        .all()
    )

    compartments = {}
    for temiz, calisan in items:
        raf_id = temiz.raf_id
        if raf_id not in compartments:
            compartments[raf_id] = []
        compartments[raf_id].append({
            "rfid_tag": temiz.rfid_tag,
            "sicil_numarasi": temiz.sicil_numarasi,
            "ad_soyad": f"{calisan.ad} {calisan.soyad}" if calisan else "-",
            "zaman_damgasi": temiz.zaman_damgasi.isoformat() if temiz.zaman_damgasi else None
        })

    return compartments

@app.get("/api/stats/history", response_model=schemas.HistoryStatsResponse)
def get_stats_history(period: str = "weekly", db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
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
    
    daily_stats = {}
    for i in range(days):
        dt = (start_date + timedelta(days=i))
        date_str = f"{dt.day:02d}.{dt.month:02d}"
        daily_stats[date_str] = {"kirli": 0, "temiz": 0, "teslim": 0}
        
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

# ---------------------------------------------------------------------------
# Tablolar
# ---------------------------------------------------------------------------

@app.get("/api/tablo/{islem_tipi}")
def get_tablo(
    islem_tipi: str,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    if islem_tipi in ['teslim', 'kiyafet'] and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Sadece admin geçmiş kayıtları görebilir.")

    if islem_tipi in ('kirli', 'temiz', 'teslim'):
        model_map = {
            'kirli': models.Kirli_Kiyafet,
            'temiz': models.Temiz_Kiyafet,
            'teslim': models.Teslim_Edilen,
        }
        model = model_map[islem_tipi]
        rows = (
            db.query(model, models.Calisan)
            .outerjoin(models.Calisan, model.sicil_numarasi == models.Calisan.sicil_numarasi)
            .order_by(model.zaman_damgasi.desc())
            .limit(50)
            .all()
        )
        result = []
        for rec, calisan in rows:
            item = {
                "islem_id": rec.islem_id,
                "rfid_tag": rec.rfid_tag,
                "sicil_numarasi": rec.sicil_numarasi,
                "ad_soyad": f"{calisan.ad} {calisan.soyad}" if calisan else "-",
                "zaman_damgasi": rec.zaman_damgasi.isoformat() if rec.zaman_damgasi else None,
            }
            if hasattr(rec, 'raf_id'):
                item["raf_id"] = rec.raf_id
            result.append(item)
        return result
    elif islem_tipi == 'kiyafet':
        query = (
            db.query(models.Kiyafet, models.Calisan)
            .outerjoin(models.Calisan, models.Kiyafet.sicil_numarasi == models.Calisan.sicil_numarasi)
        )
        if q and q.strip():
            term = f"%{q.strip()}%"
            query = query.filter(
                or_(
                    models.Kiyafet.rfid_tag.ilike(term),
                    models.Kiyafet.sicil_numarasi.ilike(term),
                    models.Calisan.ad.ilike(term),
                    models.Calisan.soyad.ilike(term),
                )
            )
        total = query.count()
        rows = query.order_by(models.Kiyafet.rfid_tag).offset(offset).limit(limit).all()
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "data": [
                {
                    "rfid_tag": k.rfid_tag,
                    "sicil_numarasi": k.sicil_numarasi,
                    "ad_soyad": f"{c.ad} {c.soyad}" if c else "-"
                }
                for k, c in rows
            ]
        }
    else:
        raise HTTPException(status_code=400, detail="Geçersiz işlem tipi")

# ---------------------------------------------------------------------------
# Audit Logs (Sadece Admin)
# ---------------------------------------------------------------------------

@app.get("/api/audit-logs", response_model=List[schemas.AuditLogResponse])
def get_audit_logs(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user),
    limit: int = 100,
    username: Optional[str] = None,
    action: Optional[str] = None
):
    """
    Audit log kayıtlarını döndürür. Sadece admin kullanıcılar erişebilir.
    Opsiyonel filtreler: username ve action query parametreleri.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sadece adminler audit loglarını görebilir.")
    
    query = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc())
    
    if username:
        query = query.filter(models.AuditLog.username == username)
    if action:
        query = query.filter(models.AuditLog.action == action)
    
    return query.limit(limit).all()

# ---------------------------------------------------------------------------
# Mock Data Init
# ---------------------------------------------------------------------------

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
