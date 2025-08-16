# test_simple.py - Función de prueba simple
import pandas as pd
from datetime import datetime

def process_file(file, user_id):
    """
    Función de prueba simple para verificar que todo funciona
    """
    
    try:
        print(f"🧪 Función de prueba ejecutándose para usuario: {user_id}")
        print(f"📁 Archivo recibido: {file.filename if hasattr(file, 'filename') else 'Sin nombre'}")
        
        # Leer el archivo Excel
        df = pd.read_excel(file)
        print(f"📊 Archivo leído exitosamente: {len(df)} filas, {len(df.columns)} columnas")
        print(f"📋 Columnas: {list(df.columns)}")
        
        # Generar un INSERT de prueba
        insert_statements = [
            f"INSERT INTO recepciones (fecha_recepcion, producto_codigo, proveedor, num_guia, volumen_m3, certificacion, user_id) VALUES ('{datetime.now().isoformat()}', 'W1.1', 'PROVEEDOR_PRUEBA', 'GUIA_123', 10.5, 'Material Controlado', '{user_id}');"
        ]
        
        return {
            "success": True,
            "records_processed": 1,
            "sheets_processed": 1,
            "total_sheets": 1,
            "errors": [],
            "insert_statements": insert_statements,
            "message": f"¡Función de prueba completada! 1 registro de prueba generado para usuario {user_id}"
        }
        
    except Exception as e:
        print(f"❌ Error en función de prueba: {str(e)}")
        return {
            "success": False,
            "error": f"Error en función de prueba: {str(e)}",
            "records_processed": 0,
            "errors": [str(e)],
            "insert_statements": []
        }