from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=Path(__file__).resolve().parent / '.env')

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./finsight.db')

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema():
    """create_all() never alters existing tables, so add columns introduced after first deploy."""
    import models  # noqa: F401  (registers tables on Base)

    Base.metadata.create_all(bind=engine)
    columns = {c['name'] for c in inspect(engine).get_columns('accounts')}
    if 'refresh_token' not in columns:
        with engine.begin() as conn:
            conn.execute(text('ALTER TABLE accounts ADD COLUMN refresh_token VARCHAR'))
