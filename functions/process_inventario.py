"""
Función ID 3: Procesador de Inventario
Procesa archivos Excel de inventario y stock
"""

import pandas as pd
from datetime import datetime
import os
import tempfile

def process_file(file, supabase):
    """
    Procesa un archivo Excel de inventario
    
    Args:
        file: Archivo subido desde el frontend
        supabase: Cliente de Supabase para insertar datos
    
    Returns:
        dict: Resultado del procesamiento
    """
    
    if not file:
        return {
            "success": False,
            "error": "No se proporcionó ningún archivo"
        }
    
    try:
        print("🚀 Iniciando procesamiento de inventario...")
        
        # Guardar archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Cargar archivo Excel
            print("📊 Cargando archivo Excel de inventario...")
            df = pd.read_excel(temp_path)
            print(f"✅ Archivo cargado. Encontradas {len(df)} filas.")
            
            # Limpieza de nombres de columna
            df.columns = df.columns.str.strip()
            
            # Verificar columnas requeridas para inventario
            cols_required = ["PRODUCTO_CODIGO", "DESCRIPCION", "STOCK_ACTUAL", "STOCK_MINIMO", "UBICACION"]
            missing_cols = [c for c in cols_required if c not in df.columns]
            
            if missing_cols:
                return {
                    "success": False,
                    "error": f"Faltan columnas requeridas: {missing_cols}. Columnas disponibles: {list(df.columns)}"
                }
            
            total_records = 0
            errors = []
            
            # Procesar cada fila
            for index, row in df.iterrows():
                try:
                    producto_codigo = str(row["PRODUCTO_CODIGO"]).strip()
                    descripcion = str(row["DESCRIPCION"]).strip()
                    stock_actual = float(row["STOCK_ACTUAL"])
                    stock_minimo = float(row["STOCK_MINIMO"])
                    ubicacion = str(row["UBICACION"]).strip()
                    
                    # Validar datos
                    if producto_codigo in ["nan", "None", ""] or descripcion in ["nan", "None", ""]:
                        continue
                    
                    if pd.isna(stock_actual) or stock_actual < 0:
                        continue
                    
                    if pd.isna(stock_minimo) or stock_minimo < 0:
                        continue
                    
                    # Determinar estado del stock
                    estado_stock = "CRITICO" if stock_actual <= stock_minimo else "NORMAL"
                    if stock_actual <= (stock_minimo * 1.2):
                        estado_stock = "BAJO"
                    
                    # Crear registro
                    record = {
                        "producto_codigo": producto_codigo,
                        "descripcion": descripcion,
                        "stock_actual": stock_actual,
                        "stock_minimo": stock_minimo,
                        "ubicacion": ubicacion,
                        "estado_stock": estado_stock,
                        "fecha_actualizacion": datetime.now().isoformat()
                    }
                    
                    # Insertar o actualizar en Supabase
                    # Primero intentar actualizar si existe
                    existing = supabase.table("inventario").select("id").eq("producto_codigo", producto_codigo).execute()
                    
                    if existing.data:
                        # Actualizar registro existente
                        result = supabase.table("inventario").update(record).eq("producto_codigo", producto_codigo).execute()
                        action = "actualizado"
                    else:
                        # Insertar nuevo registro
                        result = supabase.table("inventario").insert(record).execute()
                        action = "insertado"
                    
                    if not hasattr(result, 'error') or not result.error:
                        total_records += 1
                        print(f"✅ Producto {action}: {producto_codigo} - Stock: {stock_actual} ({estado_stock})")
                    else:
                        errors.append(f"Error en fila {index + 1}: {result.error.message}")
                        
                except Exception as e:
                    errors.append(f"Error procesando fila {index + 1}: {str(e)}")
                    continue
            
            print(f"🎉 Procesamiento de inventario completado: {total_records} registros procesados")
            
            return {
                "success": True,
                "records_processed": total_records,
                "errors": errors,
                "message": f"Procesamiento de inventario completado exitosamente. {total_records} registros procesados."
            }
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
    except Exception as e:
        error_msg = f"Error general en el procesamiento de inventario: {str(e)}"
        print(f"❌ {error_msg}")
        
        return {
            "success": False,
            "error": error_msg,
            "records_processed": 0
        }