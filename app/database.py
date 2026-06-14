import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Ortam değişkeninden veritabanı bağlantı adresi okunur
DATABASE_URL = os.environ["DATABASE_URL"]

# Connection pool ayarları env'den okunur (bkz. topoloji.md §9).
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
    cursor = dbapi_connection.cursor()
    try:
        # PostgreSQL Rule: ignore UPDATE and DELETE on audit_logs
        cursor.execute('''
            CREATE OR REPLACE RULE audit_log_prevent_update AS 
            ON UPDATE TO audit_logs DO INSTEAD NOTHING;
        ''')
        cursor.execute('''
            CREATE OR REPLACE RULE audit_log_prevent_delete AS 
            ON DELETE TO audit_logs DO INSTEAD NOTHING;
        ''')
    except Exception as e:
        # Ignore errors if DB is not PostgreSQL or table doesn't exist yet
        pass
    finally:
        cursor.close()
