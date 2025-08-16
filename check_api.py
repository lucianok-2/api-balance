#!/usr/bin/env python3
"""
Script para verificar si la API Python Flask está ejecutándose
"""

import requests
import sys
import time

def check_api_health(url="http://localhost:5000"):
    """Verifica si la API está respondiendo"""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Python está ejecutándose correctamente")
            print(f"📊 Status: {data.get('status')}")
            print(f"💬 Message: {data.get('message')}")
            print(f"🕐 Timestamp: {data.get('timestamp')}")
            return True
        else:
            print(f"❌ API responde pero con error: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ No se puede conectar a la API en {url}")
        print("💡 La API Python no está ejecutándose")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Timeout conectando a la API en {url}")
        return False
    except Exception as e:
        print(f"❌ Error verificando API: {e}")
        return False

def main():
    """Función principal"""
    print("🔍 Verificando estado de la API Python Flask...")
    print("=" * 50)
    
    if check_api_health():
        print("\n✅ La API está funcionando correctamente")
        print("🚀 Puedes procesar archivos desde el frontend")
    else:
        print("\n❌ La API no está disponible")
        print("\n🔧 Para iniciar la API:")
        print("   1. cd python-api")
        print("   2. python install_dependencies.py  # Si es la primera vez")
        print("   3. python app.py")
        print("   o")
        print("   3. python start.py")
        
        print("\n📋 Verificar que:")
        print("   - Puerto 5000 esté disponible")
        print("   - Todas las dependencias estén instaladas")
        print("   - No hay errores en la consola de Python")
        
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)