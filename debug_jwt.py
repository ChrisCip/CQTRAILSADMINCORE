"""
Script de diagnóstico para resolver problemas con PyJWT
Ejecuta este script para obtener información detallada sobre tu entorno
y resolver problemas de importación de PyJWT.
"""
import sys
import os
import subprocess
import importlib
import importlib.util
from pathlib import Path

# Encabezado
print("="*80)
print("DIAGNÓSTICO DE PyJWT".center(80))
print("="*80)

# Verificar entorno Python
print(f"\n1. INFORMACIÓN DEL ENTORNO PYTHON:")
print(f"   Python versión: {sys.version}")
print(f"   Ejecutable Python: {sys.executable}")
print(f"   Directorio de trabajo: {os.getcwd()}")

# Verificar instalación de PyJWT
print("\n2. BUSCANDO PAQUETE PyJWT:")

# Método 1: Comprobar con importlib
print("\n   Método 1: Verificando con importlib")
jwt_spec = importlib.util.find_spec("jwt")
pyjwt_spec = importlib.util.find_spec("PyJWT")

if jwt_spec:
    print(f"   ✓ El módulo 'jwt' está disponible en: {jwt_spec.origin}")
else:
    print(f"   ✗ No se encontró el módulo 'jwt'")

if pyjwt_spec:
    print(f"   ✓ El módulo 'PyJWT' está disponible en: {pyjwt_spec.origin}")
else:
    print(f"   ✗ No se encontró el módulo 'PyJWT'")

# Método 2: Intentar importar
print("\n   Método 2: Intentando importar directamente")
try:
    import jwt
    print(f"   ✓ Importación de 'jwt' exitosa, versión: {jwt.__version__}")
    print(f"     Ubicación: {jwt.__file__}")
except ImportError as e:
    print(f"   ✗ Error importando 'jwt': {str(e)}")
except AttributeError:
    print(f"   ⚠ El módulo 'jwt' se importó pero no tiene atributo '__version__'")
except Exception as e:
    print(f"   ✗ Error inesperado con 'jwt': {str(e)}")

try:
    import PyJWT
    print(f"   ✓ Importación de 'PyJWT' exitosa, versión: {PyJWT.__version__}")
    print(f"     Ubicación: {PyJWT.__file__}")
except ImportError as e:
    print(f"   ✗ Error importando 'PyJWT': {str(e)}")
except AttributeError:
    print(f"   ⚠ El módulo 'PyJWT' se importó pero no tiene atributo '__version__'")
except Exception as e:
    print(f"   ✗ Error inesperado con 'PyJWT': {str(e)}")

# Método 3: Verificar con pip
print("\n   Método 3: Comprobando con pip")
try:
    result = subprocess.run([sys.executable, "-m", "pip", "list"], 
                            capture_output=True, text=True, check=True)
    output = result.stdout.lower()
    
    if "pyjwt" in output:
        print("   ✓ PyJWT aparece en la lista de paquetes instalados")
        
        # Obtener versión exacta
        result = subprocess.run([sys.executable, "-m", "pip", "show", "PyJWT"], 
                                capture_output=True, text=True, check=True)
        for line in result.stdout.split('\n'):
            if line.lower().startswith('version:'):
                print(f"   ✓ Versión instalada: {line.split(':')[1].strip()}")
            if line.lower().startswith('location:'):
                print(f"   ✓ Ubicación: {line.split(':')[1].strip()}")
    else:
        print("   ✗ PyJWT NO aparece en la lista de paquetes instalados")
        print("   Intentando instalar PyJWT...")
        try:
            install_result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "PyJWT==2.6.0"], 
                capture_output=True, text=True, check=True
            )
            print("   ✓ PyJWT instalado correctamente")
        except subprocess.CalledProcessError as e:
            print(f"   ✗ Error al instalar PyJWT: {e.stderr}")
except subprocess.CalledProcessError as e:
    print(f"   ✗ Error ejecutando pip: {e.stderr}")

# Probar funcionalidad básica de JWT
print("\n3. PRUEBA DE FUNCIONALIDAD DE JWT:")
print("\n   Intentando crear y verificar un token JWT")

def test_jwt():
    try:
        # Primero intentamos con PyJWT
        import PyJWT
        print("   Usando módulo PyJWT...")
        token = PyJWT.encode({"data": "test"}, "secret", algorithm="HS256")
        print(f"   ✓ Token creado: {token}")
        decoded = PyJWT.decode(token, "secret", algorithms=["HS256"])
        print(f"   ✓ Token verificado: {decoded}")
        return True
    except ImportError:
        try:
            # Luego con jwt
            import jwt
            print("   Usando módulo jwt...")
            token = jwt.encode({"data": "test"}, "secret", algorithm="HS256")
            print(f"   ✓ Token creado: {token}")
            decoded = jwt.decode(token, "secret", algorithms=["HS256"])
            print(f"   ✓ Token verificado: {decoded}")
            return True
        except ImportError:
            print("   ✗ No se pudo importar ningún módulo JWT")
            return False
        except Exception as e:
            print(f"   ✗ Error con módulo jwt: {str(e)}")
            return False
    except Exception as e:
        print(f"   ✗ Error con módulo PyJWT: {str(e)}")
        return False

test_jwt()

# Verificar sys.path
print("\n4. RUTAS DE IMPORTACIÓN PYTHON (sys.path):")
for i, path in enumerate(sys.path, 1):
    print(f"   {i}. {path}")

# Mostrar soluciones
print("\n" + "="*80)
print("SOLUCIONES RECOMENDADAS".center(80))
print("="*80)

print("""
Si PyJWT no está instalado o hay errores:

1. Instala con pip desde la línea de comandos:
   pip install PyJWT==2.6.0
   
2. Usa pip con el ejecutable Python específico:
   {} -m pip install PyJWT==2.6.0
   
3. Reinicia tu entorno de desarrollo después de instalar.

4. Si usas un entorno virtual, asegúrate de activarlo antes de ejecutar.

5. Verifica que no haya conflictos de nombres:
   pip uninstall PyJWT jwt pyjwt
   pip install PyJWT==2.6.0
""".format(sys.executable))

print("="*80)
