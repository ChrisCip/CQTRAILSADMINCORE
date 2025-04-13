import os
import sys
import argparse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener la URL de la base de datos desde .env
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL no encontrado en el archivo .env")
    sys.exit(1)

def run_migration(script_path):
    """Ejecuta un script SQL de migración en la base de datos PostgreSQL"""
    try:
        # Leer el contenido del script
        with open(script_path, 'r') as file:
            sql_script = file.read()
            
        # Crear conexión a la base de datos
        engine = create_engine(DATABASE_URL)
        
        # Ejecutar la migración dentro de una transacción
        with engine.begin() as connection:
            print(f"Ejecutando migración desde: {script_path}")
            connection.execute(text(sql_script))
            print("Migración completada con éxito")
            
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {script_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error al ejecutar la migración: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejecutar script de migración SQL")
    parser.add_argument(
        "--script", 
        default="migrations/add_permisos_columns.sql",
        help="Ruta al archivo de script SQL (por defecto: migrations/add_permisos_columns.sql)"
    )
    
    args = parser.parse_args()
    run_migration(args.script) 