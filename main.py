from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from dbcontext.mydb import SessionLocal
from dbcontext.models import Usuarios  # Este viene del scaffold

app = FastAPI()

# Dependencia para la sesión de DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/usuarios")
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(Usuarios).all()