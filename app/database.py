import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Ortam değişkeninden veritabanı bağlantı adresi okunur
DATABASE_URL = os.environ["DATABASE_URL"]

# Connection pool ayarları env'den okunur (bkz. 03_DATABASE_SCHEMA.md §1 "DB Engine ve Versiyon").
# SQLite (testler) QueuePool argümanlarını desteklemediğinden yalnızca
# PostgreSQL gibi gerçek havuzlu sürücülerde uygulanır.
_engine_kwargs = {"pool_pre_ping": True}
if not DATABASE_URL.startswith("sqlite"):
    _engine_kwargs.update(
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
    )

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@event.listens_for(engine, "connect")
def set_audit_log_rule(dbapi_connection, connection_record):
    # audit_logs append-only güvencesi: UPDATE/DELETE'i RULE ile INSTEAD NOTHING yap.
    # Yalnızca PostgreSQL içindir; RULE sözdizimi SQLite'ta yok, o yüzden atlanır.
    if DATABASE_URL.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(
            "CREATE OR REPLACE RULE audit_log_prevent_update AS "
            "ON UPDATE TO audit_logs DO INSTEAD NOTHING;"
        )
        cursor.execute(
            "CREATE OR REPLACE RULE audit_log_prevent_delete AS "
            "ON DELETE TO audit_logs DO INSTEAD NOTHING;"
        )
        # DDL transaction'ını kalıcılaştır; aksi halde RULE asla persist olmaz.
        dbapi_connection.commit()
    except Exception:
        # İlk bağlantıda audit_logs henüz oluşmamış olabilir (create_all öncesi).
        # Aborted transaction'ı geri al ki bağlantı havuzda bozuk (InFailedSqlTransaction)
        # kalmasın. Tablo oluştuktan sonraki bağlantılarda RULE başarıyla kurulur.
        dbapi_connection.rollback()
    finally:
        cursor.close()
