from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import importlib.util
import sys
from datetime import datetime
import traceback
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
CORS(app)  # Permitir CORS para todas las rutas


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que la API está funcionando"""
    return jsonify({
        "status": "healthy",
        "message": "Python API Flask está funcionando correctamente",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/execute-function', methods=['POST'])
def execute_function():
    """Endpoint principal para ejecutar funciones Python"""
    try:
        # Obtener datos del request
        function_id = request.form.get('functionId')
        file = request.files.get('file')
        user_id = request.form.get('userId')  # RECIBIR EL USER_ID

        if not function_id:
            return jsonify({
                "success": False,
                "error": "functionId es requerido"
            }), 400

        if not file:
            return jsonify({
                "success": False,
                "error": "Archivo es requerido"
            }), 400

        if not user_id:
            return jsonify({
                "success": False,
                "error": "userId es requerido"
            }), 400

        # Ejecutar la función específica CON EL USER_ID
        result = execute_user_function(function_id, file, user_id)

        return jsonify(result)

    except Exception as e:
        error_message = f"Error interno del servidor: {str(e)}"
        print(f"❌ {error_message}")
        print(traceback.format_exc())

        return jsonify({
            "success": False,
            "error": error_message
        }), 500


def execute_user_function(function_id, file, user_id):
    """Ejecuta la función Python específica basada en el ID CON EL USER_ID"""
    try:
        print(f"🔍 Ejecutando función {function_id} para usuario {user_id}")

        # Mapeo específico para usuarios con funciones personalizadas
        user_function_mappings = {
            '496f6470-2f4d-40c6-9426-bb5421116a3d': {
                # Mapeo específico por función ID para este usuario
                '1': f"functions/{user_id}/process_recepciones.py",
                '3': f"functions/{user_id}/process_venta_astilla_masisa.py",
                '4': f"functions/{user_id}/process_ventas_masisa.py",
                '5': f"functions/{user_id}/process_ventas_arauco.py",
                # Función por defecto para IDs no especificados
                'default': f"functions/{user_id}/process_recepciones.py"
            },
            'ae6a5783-4da9-49d2-b415-af7384362b7c': {
                '6': f"functions/{user_id}/process_recepciones.py",
                'default': f"functions/{user_id}/process_recepciones.py"
            }
        }

        # Verificar si el usuario tiene funciones personalizadas
        if user_id in user_function_mappings:
            user_mappings = user_function_mappings[user_id]

            # Buscar función específica por ID, sino usar default
            user_function_file = user_mappings.get(
                str(function_id), user_mappings.get('default'))

            print(
                f"🔍 Usuario con funciones personalizadas detectado: {user_id}")
            print(f"📁 Función ID: {function_id}")
            print(f"📁 Buscando función personalizada en: {user_function_file}")
            print(
                f"📁 ¿Existe el archivo? {os.path.exists(user_function_file)}")

            if os.path.exists(user_function_file):
                print(
                    f"✅ Usando función personalizada del usuario: {user_function_file}")
                function_file = user_function_file
            else:
                return {
                    "success": False,
                    "error": f"Archivo de función personalizada no encontrado: {user_function_file}"
                }
        else:
            # Mapeo de function_id a archivo Python genérico para otros usuarios
            function_files = {
                '1': 'functions/process_ingresos.py',
                '2': 'functions/process_ventas.py',
                '3': 'functions/process_inventario.py',
                # Agregar más funciones aquí según sea necesario
            }

            function_file = function_files.get(str(function_id))
            print(
                f"📋 Usando función genérica para ID {function_id}: {function_file}")

            if not function_file:
                return {
                    "success": False,
                    "error": f"No hay implementación para la función ID {function_id}"
                }

        # Verificar que el archivo existe
        if not os.path.exists(function_file):
            return {
                "success": False,
                "error": f"Archivo de función no encontrado: {function_file}"
            }

        # Cargar y ejecutar el módulo dinámicamente
        spec = importlib.util.spec_from_file_location(
            "user_function", function_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Ejecutar la función principal del módulo CON EL USER_ID
        if hasattr(module, 'process_file'):
            # PASAR EL USER_ID A LA FUNCIÓN
            return module.process_file(file, user_id)
        else:
            return {
                "success": False,
                "error": "La función no tiene un método 'process_file' implementado"
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error ejecutando la función: {str(e)}"
        }


@app.route('/functions', methods=['GET'])
def list_functions():
    """Endpoint para listar todas las funciones disponibles"""
    try:
        # Lista estática de funciones disponibles
        functions = [
            {
                "id": 1,
                "function_name": "Procesador de Reportes de Ingreso",
                "function_description": "Procesa archivos Excel de reportes de ingreso de planta y genera INSERT statements para la tabla recepciones",
                "is_active": True
            },
            {
                "id": 2,
                "function_name": "Procesador de Ventas",
                "function_description": "Procesa archivos Excel de reportes de ventas y genera INSERT statements para la tabla ventas",
                "is_active": True
            },
            {
                "id": 3,
                "function_name": "Procesador de Inventario",
                "function_description": "Procesa archivos Excel de inventario y genera INSERT statements para la tabla inventario",
                "is_active": True
            },
            {
                "id": 5,
                "function_name": "Procesador de Proforma ARAUCO",
                "function_description": "Procesa archivos Excel de proforma ARAUCO y genera INSERT statements para la tabla ventas",
                "is_active": True
            }
        ]

        return jsonify({
            "success": True,
            "functions": functions
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error obteniendo funciones: {str(e)}"
        }), 500


if __name__ == '__main__':
    print("🚀 Iniciando Python API Flask...")
    print("🔧 Funciones disponibles:")
    print("   - ID 1: Procesador de Reportes de Ingreso")
    print("   - ID 2: Procesador de Ventas")
    print("   - ID 3: Procesador de Inventario")
    print("   - ID 5: Procesador de Proforma ARAUCO")
    print("🌐 API corriendo en http://localhost:5000")

    app.run(debug=True, host='0.0.0.0', port=5000)
