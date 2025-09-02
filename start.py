#!/usr/bin/env python3
"""
Script de inicio para la API Python Flask
Verifica dependencias y configuración antes de iniciar
"""

import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Verifica que las dependencias estén instaladas"""
    try:
        import flask
        import pandas
        import openpyxl
        from dotenv import load_dotenv
        print("✅ Todas las dependencias están instaladas")
        return True
    except ImportError as e:
        print(f"❌ Dependencia faltante: {e}")
        print("💡 Ejecuta: pip install -r requirements.txt")
        return False

def check_env_file():
    """Verifica que el archivo .env exista y tenga las variables necesarias"""
    env_path = Path('.env')
    
    if not env_path.exists():
        print("❌ Archivo .env no encontrado")
        print("💡 Copia .env.example a .env y configura tus variables")
        return False
    
    from dotenv import load_dotenv
    load_dotenv()
    
    # Ya no necesitamos variables de entorno de Supabase
    # El procesamiento Python solo genera INSERT statements
    
    print("✅ Configuración de entorno correcta")
    return True

def check_functions_directory():
    """Verifica que el directorio de funciones exista"""
    functions_dir = Path('functions')
    
    if not functions_dir.exists():
        print("❌ Directorio 'functions' no encontrado")
        return False
    
    required_functions = [
        'process_ingresos.py',
        'process_ventas.py',
        'process_inventario.py'
    ]
    
    missing_functions = []
    for func in required_functions:
        if not (functions_dir / func).exists():
            missing_functions.append(func)
    
    if missing_functions:
        print(f"❌ Archivos de función faltantes: {missing_functions}")
        return False
    
    print("✅ Todas las funciones están disponibles")
    return True

def main():
    """Función principal"""
    print("🚀 Iniciando verificaciones para la API Python Flask...")
    print("=" * 60)
    
    # Verificar dependencias
    if not check_dependencies():
        sys.exit(1)
    
    # Verificar archivo .env
    if not check_env_file():
        sys.exit(1)
    
    # Verificar directorio de funciones
    if not check_functions_directory():
        sys.exit(1)
    
    print("=" * 60)
    print("✅ Todas las verificaciones pasaron correctamente")
    print("🚀 Iniciando API Flask...")
    print("🌐 La API estará disponible en: http://localhost:5000")
    print("📋 Endpoints disponibles:")
    print("   - GET  /health")
    print("   - POST /execute-function")
    print("   - GET  /functions")
    print("=" * 60)
    
    # Iniciar la aplicación Flask
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 API Flask detenida por el usuario")
    except Exception as e:
        print(f"❌ Error iniciando la API: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()