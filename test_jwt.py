"""
This is a simple test script to verify PyJWT installation.
Run it with: python test_jwt.py
"""
import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path}")
print("\nChecking for PyJWT installation...")

try:
    import PyJWT
    print(f"PyJWT is installed! Version: {PyJWT.__version__}")
    
    # Test basic functionality
    test_payload = {"test": "data"}
    test_key = "secret"
    
    encoded = PyJWT.encode(test_payload, test_key, algorithm="HS256")
    print(f"Successfully encoded token: {encoded}")
    
    decoded = PyJWT.decode(encoded, test_key, algorithms=["HS256"])
    print(f"Successfully decoded token: {decoded}")
    
    print("PyJWT is working correctly!")
except ImportError:
    print("❌ PyJWT is NOT installed in this Python environment!")
    print("\nPlease install it with one of these commands:")
    print("pip install PyJWT")
    print("python -m pip install PyJWT")
except Exception as e:
    print(f"❌ Error when testing PyJWT: {str(e)}")
