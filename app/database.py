import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Ortam değişkeninden veritabanı bağlantı adresi okunur
DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
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
