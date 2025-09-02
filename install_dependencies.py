#!/usr/bin/env python3
"""
Script para instalar las dependencias necesarias para procesar archivos Excel
"""

import subprocess
import sys
import os

def install_package(package):
    """Instala un paquete usando pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} instalado correctamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando {package}: {e}")
        return False

def check_package(package_name):
    """Verifica si un paquete está instalado"""
    try:
        __import__(package_name)
        print(f"✅ {package_name} ya está instalado")
        return True
    except ImportError:
        print(f"⚠️ {package_name} no está instalado")
        return False

def main():
    """Función principal"""
    print("🔧 Verificando e instalando dependencias para procesamiento de Excel...")
    print("=" * 60)
    
    # Lista de paquetes requeridos
    packages = {
        'flask': 'Flask==3.0.0',
        'flask_cors': 'Flask-CORS==4.0.0', 
        'pandas': 'pandas>=2.2.0',
        'openpyxl': 'openpyxl>=3.1.0',
        'xlrd': 'xlrd>=2.0.1',
        'dotenv': 'python-dotenv>=1.0.0'
    }
    
    packages_to_install = []
    
    # Verificar qué paquetes faltan
    for package_name, package_spec in packages.items():
        if not check_package(package_name):
            packages_to_install.append(package_spec)
    
    # Instalar paquetes faltantes
    if packages_to_install:
        print(f"\n📦 Instalando {len(packages_to_install)} paquetes faltantes...")
        for package in packages_to_install:
            install_package(package)
    else:
        print("\n✅ Todas las dependencias ya están instaladas")
    
    print("\n🧪 Probando importaciones...")
    
    # Probar importaciones
    try:
        import flask
        import flask_cors
        import pandas as pd
        import openpyxl
        import xlrd
        from dotenv import load_dotenv
        
        print("✅ Todas las importaciones funcionan correctamente")
        
        # Probar lectura de Excel
        print("\n🔍 Verificando capacidades de lectura de Excel...")
        print(f"📊 Pandas version: {pd.__version__}")
        print(f"📊 Openpyxl version: {openpyxl.__version__}")
        print(f"📊 Xlrd version: {xlrd.__version__}")
        
        print("\n✅ Sistema listo para procesar archivos Excel (.xlsx y .xls)")
        
    except ImportError as e:
        print(f"❌ Error en importaciones: {e}")
        return False
    
    print("=" * 60)
    print("🚀 Configuración completada. Puedes ejecutar la API con:")
    print("   python app.py")
    print("   o")
    print("   python start.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)