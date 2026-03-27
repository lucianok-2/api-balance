import os
import pandas as pd
from datetime import datetime
import tempfile
import re

def process_file(file, user_id):
    if not file:
        return {"success": False, "error": "No se proporcionó ningún archivo"}

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name

        try:
            result = process_excel_file(temp_path, user_id)
            return result
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        return {"success": False, "error": f"Error general: {str(e)}", "records_processed": 0}

def process_excel_file(file_path, user_id):
    total_records = 0
    processed_sheets = 0
    errors = []
    insert_statements = []

    try:
        xf = pd.read_excel(file_path, sheet_name=None)

        for sheet_name, df in xf.items():
            print(f"📊 Procesando hoja: {sheet_name} con {len(df)} filas")
            
            df.columns = df.columns.astype(str).str.strip()
            
            # Mapeo de columnas para PRODUCCIÓN
            fecha_col = "Fecha Produccion"
            producto_col = "Producto a Producir"
            vol_col = "Volumen M3"
            desc_col = "Descripcion"
            
            columnas_esperadas = [fecha_col, producto_col, vol_col] # Descripcion es opcional
            
            columnas_map = {}
            for expected in columnas_esperadas:
                found = False
                for actual in df.columns:
                    if actual.strip().lower() == expected.lower():
                        columnas_map[expected] = actual
                        found = True
                        break
                if not found:
                    error_msg = f"No encontré la columna requerida '{expected}' en la hoja «{sheet_name}»"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
            
            # Buscar opcional
            for actual in df.columns:
                if actual.strip().lower() == desc_col.lower():
                    columnas_map[desc_col] = actual
                    break

            if len([k for k in columnas_esperadas if k in columnas_map]) < len(columnas_esperadas):
                print(f"⚠️ Faltan columnas requeridas en hoja {sheet_name}, se omitirá.")
                continue

            sheet_records = 0

            for index, row in df.iterrows():
                try:
                    # Parsear Fecha
                    val_fecha = row[columnas_map[fecha_col]]
                    if pd.isna(val_fecha): continue
                    
                    if isinstance(val_fecha, pd.Timestamp):
                        fecha_iso = val_fecha.isoformat()
                    else:
                        fecha_iso = pd.to_datetime(val_fecha, errors='coerce').isoformat()

                    # Parsear M3 (Volumen)
                    val_vol = row[columnas_map[vol_col]]
                    try:
                        volumen = float(val_vol) if pd.notna(val_vol) else 0.0
                    except:
                        volumen = 0.0
                    
                    if volumen <= 0: continue

                    # Parsear Producto Destino
                    val_tipo_mat = row[columnas_map[producto_col]]
                    producto_destino = ""
                    if pd.notna(val_tipo_mat):
                        # Extraer solo el codigo (e.g. "W10.3" de "W10.3 Pallets")
                        match = re.match(r"^(\S+)", str(val_tipo_mat).strip())
                        if match:
                            producto_destino = match.group(1)

                    if not producto_destino:
                        continue

                    # Parsear Descripcion (opcional)
                    descripcion = ""
                    if desc_col in columnas_map:
                        val_desc = row[columnas_map[desc_col]]
                        if pd.notna(val_desc):
                            descripcion = str(val_desc).strip()

                    # Generar INSERT statement (Asumiendo consumo estricto origen W1.1 -> volumen 0 como default)
                    guardar_pd = producto_destino.replace("'", "''")
                    guardar_desc = descripcion.replace("'", "''")

                    insert_sql = f"""INSERT INTO produccion (fecha_produccion, producto_origen_codigo, producto_destino_codigo, volumen_origen_m3, volumen_destino_m3, descripcion, user_id) 
VALUES ('{fecha_iso}', 'W1.1', '{guardar_pd}', 0, {volumen}, '{guardar_desc}', '{user_id}');"""

                    insert_statements.append(insert_sql)
                    sheet_records += 1
                    total_records += 1
                    
                except Exception as row_error:
                    print(f"❌ Error procesando fila {index}: {row_error}")
                    continue

            processed_sheets += 1
            print(f"✅ Hoja {sheet_name} procesada: {sheet_records} registros")

        return {
            "success": True,
            "records_processed": total_records,
            "sheets_processed": processed_sheets,
            "errors": errors,
            "insert_statements": insert_statements,
            "message": f"¡Procesamiento Completado! {total_records} producciones extraídas."
        }

    except Exception as e:
        error_msg = f"Error en el procesamiento: {str(e)}"
        print(f"❌ {error_msg}")
        errors.append(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "records_processed": total_records,
            "errors": errors,
            "insert_statements": insert_statements
        }
