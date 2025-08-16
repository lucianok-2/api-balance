#!/usr/bin/env python3
"""
Script para probar la API Python Flask
"""

import requests
import json
from pathlib import Path

API_BASE_URL = "http://localhost:5000"

def test_health():
    """Probar el endpoint de health check"""
    print("🔍 Probando health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check exitoso: {data['message']}")
            return True
        else:
            print(f"❌ Health check falló: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar a la API. ¿Está ejecutándose?")
        return False
    except Exception as e:
        print(f"❌ Error en health check: {e}")
        return False

def test_functions_list():
    """Probar el endpoint de listado de funciones"""
    print("🔍 Probando listado de funciones...")
    try:
        # Usar UUID temporal para pruebas
        test_user_id = "11111111-1111-1111-1111-111111111111"
        response = requests.get(f"{API_BASE_URL}/functions", params={"userId": test_user_id})
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                functions = data['functions']
                print(f"✅ Funciones obtenidas: {len(functions)} funciones disponibles")
                for func in functions:
                    print(f"   - ID {func['id']}: {func['function_name']}")
                return True
            else:
                print(f"❌ Error obteniendo funciones: {data.get('error')}")
                return False
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error probando funciones: {e}")
        return False

def test_execute_function():
    """Probar el endpoint de ejecución (sin archivo real)"""
    print("🔍 Probando ejecución de función...")
    try:
        # Crear un archivo de prueba temporal
        test_data = {
            'functionId': '1',
            'userId': '11111111-1111-1111-1111-111111111111'
        }
        
        # Sin archivo para esta prueba
        response = requests.post(f"{API_BASE_URL}/execute-function", data=test_data)
        
        if response.status_code == 400:
            # Esperamos un error 400 porque no enviamos archivo
            print("✅ Endpoint de ejecución responde correctamente (sin archivo)")
            return True
        else:
            print(f"⚠️ Respuesta inesperada: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error probando ejecución: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("🧪 Iniciando pruebas de la API Python Flask")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("Listado de Funciones", test_functions_list),
        ("Ejecución de Función", test_execute_function)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        if test_func():
            passed += 1
        print("-" * 30)
    
    print(f"\n📊 Resultados: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! La API está funcionando correctamente.")
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa la configuración de la API.")
    
    print("\n💡 Para probar con archivos reales, usa el frontend web o herramientas como Postman.")

if __name__ == '__main__':
    main()