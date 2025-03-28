import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()  # Esto busca y carga las variables del archivo .env

DATABASE_URL = os.getenv("DATABASE_URL")  # Aquí obtienes el string real de la URL
# Ejemplo: "postgresql://user:pass@host/dbname"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)