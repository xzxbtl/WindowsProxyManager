import os
import sys
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DB_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, "proxy.db")


DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)

Base = declarative_base()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def create_base():
    try:
        Base.metadata.create_all(bind=engine)
        print("Base tables created (sync)")
    except Exception as e:
        print(f"Error creating tables (sync) - {e}")


def clear_base():
    try:
        Base.metadata.drop_all(bind=engine)
        print("Base tables dropped (sync)")
    except Exception as e:
        print(f"Error dropping tables (sync) - {e}")


@contextmanager
def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        print("Session closed")
