import os
import time
import logging
from datetime import datetime, timedelta

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("jwt_utils")

# Variable global para rastrear el módulo JWT que estamos usando
JWT_MODULE_NAME = None

# Intentar importar PyJWT/jwt con múltiples estrategias
try:
    # Estrategia 1: Importar como PyJWT (nombre del paquete)
    import PyJWT
    JWT_MODULE_NAME = "PyJWT"
    logger.info("Usando módulo PyJWT directamente")
except ImportError:
    try:
        # Estrategia 2: Importar como jwt (alias común)
        import jwt as PyJWT
        JWT_MODULE_NAME = "jwt"
        logger.info("Usando módulo jwt como PyJWT")
    except ImportError:
        try:
            # Estrategia 3: Usar importlib para una importación más flexible
            import importlib
            jwt_spec = importlib.util.find_spec("jwt")
            pyjwt_spec = importlib.util.find_spec("PyJWT")
            
            if pyjwt_spec:
                PyJWT = importlib.import_module("PyJWT")
                JWT_MODULE_NAME = "PyJWT (importlib)"
                logger.info("Usando PyJWT importado con importlib")
            elif jwt_spec:
                PyJWT = importlib.import_module("jwt")
                JWT_MODULE_NAME = "jwt (importlib)"
                logger.info("Usando jwt importado con importlib")
            else:
                raise ImportError("No se encontró ningún módulo JWT usando importlib")
        except Exception as e:
            logger.error(f"Error al importar JWT usando importlib: {str(e)}")
            
            # Implementación de respaldo (dummy) para desarrollo
            logger.warning("ADVERTENCIA: Usando implementación de JWT provisional")
            
            class DummyJWT:
                @staticmethod
                def encode(payload, key, algorithm=None):
                    import base64
                    import json
                    logger.warning("ADVERTENCIA: Usando encode() de implementación provisional")
                    # Implementación básica que simplemente codifica en base64
                    payload_json = json.dumps(payload)
                    token = base64.b64encode(payload_json.encode()).decode()
                    return token
                
                @staticmethod
                def decode(token, key, algorithms=None, options=None, audience=None, issuer=None):
                    import base64
                    import json
                    logger.warning("ADVERTENCIA: Usando decode() de implementación provisional")
                    try:
                        # Implementación básica que simplemente decodifica el base64
                        payload_json = base64.b64decode(token).decode()
                        return json.loads(payload_json)
                    except Exception as e:
                        logger.error(f"Error decodificando token: {str(e)}")
                        raise Exception(f"Invalid token: {str(e)}")
            
            PyJWT = DummyJWT()
            JWT_MODULE_NAME = "DummyJWT"

# Configuración desde variables de entorno
JWT_KEY = os.getenv("JWT_KEY", "tu-clave-secreta-para-desarrollo")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ISSUER = os.getenv("JWT_ISSUER", "cqtrails-api")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "cqtrails-app")
JWT_SUBJECT = os.getenv("JWT_SUBJECT", "auth")
JWT_EXPIRATION_SECONDS = int(os.getenv("JWT_EXPIRATION_SECONDS", "28800"))  # 8 horas

# Registrar información sobre la configuración
logger.info(f"Módulo JWT: {JWT_MODULE_NAME}")
logger.info(f"Algoritmo: {JWT_ALGORITHM}")
logger.info(f"Expiración: {JWT_EXPIRATION_SECONDS} segundos")

def create_access_token(user_id: int, email: str, role: str, permissions: list = None):
    """
    Crea un token JWT de acceso con información del usuario
    
    Args:
        user_id: ID del usuario
        email: Email del usuario
        role: Nombre del rol del usuario
        permissions: Lista de nombres de permisos
        
    Returns:
        str: Token JWT codificado
    """
    permissions = permissions or []
    
    # Obtener timestamp actual y tiempo de expiración
    now = int(time.time())
    expires = now + JWT_EXPIRATION_SECONDS
    
    # Crear payload del token
    payload = {
        "iss": JWT_ISSUER,        # Emisor
        "aud": JWT_AUDIENCE,      # Audiencia
        "sub": JWT_SUBJECT,       # Asunto
        "iat": now,               # Emitido en
        "exp": expires,           # Tiempo de expiración
        "user_id": user_id,       # Claims personalizados
        "email": email,
        "role": role,
        "permissions": permissions
    }
    
    try:
        # Codificar token con PyJWT
        token = PyJWT.encode(payload, JWT_KEY, algorithm=JWT_ALGORITHM)
        
        # PyJWT devuelve bytes en Python 3.6 y anteriores; str en versiones posteriores
        if isinstance(token, bytes):
            token = token.decode('utf-8')
            
        logger.debug(f"Token creado correctamente para usuario {email}")
        return token
    except Exception as e:
        logger.error(f"Error creando token para {email}: {str(e)}")
        raise Exception(f"Error creating token: {str(e)}")

def decode_token(token: str) -> dict:
    """Decodifica y valida un token JWT"""
    if not token:
        logger.error("Se intentó decodificar un token vacío")
        raise ValueError("Token vacío")
        
    try:
        # Realizar opciones básicas de validación
        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True, 
            "verify_aud": True,
            "verify_iss": True,
            "require": ["exp", "iat", "iss", "aud", "user_id", "role"]
        }
        
        # Decodificar y verificar el token
        payload = PyJWT.decode(
            token, 
            JWT_KEY, 
            algorithms=[JWT_ALGORITHM],
            options=options,
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER
        )
        
        logger.debug(f"Token decodificado correctamente para usuario {payload.get('email')}")
        return payload
    except Exception as e:
        logger.error(f"Error decodificando token: {str(e)}")
        # Usar excepción genérica para capturar cualquier error de jwt
        raise Exception(f"Invalid token: {str(e)}")

# Añadir una función de prueba que se puede ejecutar directamente
def test_jwt_functionality():
    """Prueba la funcionalidad JWT básica"""
    print("\n=== PRUEBA DE FUNCIONALIDAD JWT ===")
    try:
        # Crear un token de prueba
        test_token = create_access_token(
            user_id=999, 
            email="test@example.com", 
            role="Tester",
            permissions=["test"]
        )
        print(f"✓ Token creado: {test_token}")
        
        # Decodificar el token
        decoded = decode_token(test_token)
        print(f"✓ Token decodificado: {decoded}")
        
        print("✓ ¡La funcionalidad JWT está trabajando correctamente!")
        return True
    except Exception as e:
        print(f"✗ Error en la prueba JWT: {str(e)}")
        return False

# Si este archivo se ejecuta directamente, realizar prueba
if __name__ == "__main__":
    test_jwt_functionality()
