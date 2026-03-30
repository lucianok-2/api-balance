import os
import pandas as pd
from datetime import datetime
import tempfile
import re
import time

def process_file(file, user_id):
    if not file:
        return {"success": False, "error": "No se proporcionó ningún archivo"}

    # Crear una ruta manual única para evitar conflictos en Windows
    temp_name = f"cons_upload_{user_id}_{int(time.time())}.xlsx"
    temp_path = os.path.join(tempfile.gettempdir(), temp_name)
    
    try:
        # Guardar directamente con Flask
        file.save(temp_path)
        
        # Pequeño retardo para asegurar que Windows libere el handle de escritura
        time.sleep(0.5)
        
        result = process_excel_file(temp_path, user_id)
        return result

    except Exception as e:
        return {"success": False, "error": f"Error general: {str(e)}", "records_processed": 0}
    finally:
        # Limpiar archivo temporal con reintentos
        intentos = 0
        while intentos < 3:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                break
            except Exception:
                time.sleep(0.5)
                intentos += 1

def process_excel_file(file_path, user_id):
    total_records = 0
    processed_sheets = 0
    errors = []
    insert_statements = []

    try:
        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names
        print(f"📄 Hojas de consumo encontradas: {sheet_names}")

        for sheet_name in sheet_names:
            print(f"📊 Analizando hoja de consumo: {sheet_name}")
            
            # Leer las primeras 20 filas para buscar el header
            df_head = xl.parse(sheet_name, nrows=20, header=None)
            
            # Mapeo de palabras clave para CONSUMO
            mapeo_keywords = {
                "fecha": ["fecha", "fec", "dia", "día", "período", "periodo", "fecha consumo"],
                "volumen": ["consumo madera (m3)", "consumo madera m3", "consumo", "volumen", "consumido"],
                "descripcion": ["descripcion", "descripción", "detalle", "obs", "observacion"]
            }

            header_row_idx = -1
            columnas_map = {} # target_name -> index
            
            # Buscar en cada una de las primeras 20 filas
            for i, row in df_head.iterrows():
                row_values = [str(val).strip().lower() for val in row.values]
                
                temp_map = {}
                requeridas = ["fecha", "volumen"]
                
                for target in requeridas:
                    keywords = mapeo_keywords[target]
                    for idx, cell_val in enumerate(row_values):
                        if cell_val != "nan":
                            # Si buscamos volumen, ignorar si la celda contiene "stock" o "inicial"
                            if target == "volumen" and any(x in cell_val for x in ["stock", "inicial"]):
                                continue
                                
                            if any(k == cell_val or k in cell_val for k in keywords):
                                temp_map[target] = idx
                                break
                
                if len(temp_map) >= 2: # Fecha y Volumen
                    header_row_idx = i
                    columnas_map = temp_map
                    # Buscar la opcional descripcion
                    for idx, cell_val in enumerate(row_values):
                        if cell_val != "nan" and idx not in columnas_map.values():
                            if any(k in cell_val for k in mapeo_keywords["descripcion"]):
                                columnas_map["descripcion"] = idx
                                break
                    break
            
            if header_row_idx == -1:
                print(f"⚠️ No se detectó cabecera en hoja «{sheet_name}»")
                continue

            # Leer data real
            df = xl.parse(sheet_name, skiprows=header_row_idx + 1, header=None)
            print(f"✅ Hoja {sheet_name}: Procesando {len(df)} filas.")

            sheet_records = 0
            for index, row in df.iterrows():
                try:
                    idx_fecha = columnas_map.get("fecha")
                    idx_vol = columnas_map.get("volumen")

                    if idx_fecha is None or idx_vol is None:
                        continue

                    # Parsear Fecha
                    val_fecha = row[idx_fecha] if idx_fecha < len(row) else None
                    if pd.isna(val_fecha): continue
                    
                    try:
                        if isinstance(val_fecha, pd.Timestamp):
                            fecha_dt = val_fecha
                        else:
                            fecha_dt = pd.to_datetime(val_fecha, errors='coerce')
                        
                        if pd.isna(fecha_dt): continue
                        fecha_iso = fecha_dt.isoformat()
                    except:
                        continue

                    # Parsear Volumen
                    val_vol = row[idx_vol] if idx_vol < len(row) else 0.0
                    try:
                        volumen = float(val_vol) if pd.notna(val_vol) else 0.0
                    except:
                        volumen = 0.0
                    
                    if volumen <= 0: continue

                    # Para Vision, el consumo es de Materia Prima (W1.1)
                    producto_codigo = "W1.1"
                        
                    # Parsear Descripción (opcional)
                    descripcion = ""
                    if "descripcion" in columnas_map:
                        idx_desc = columnas_map["descripcion"]
                        val_desc = row[idx_desc] if idx_desc < len(row) else ""
                        descripcion = str(val_desc).strip() if pd.notna(val_desc) else ""

                    # Generar SQL INSERT para la tabla consumos
                    guardar_desc = descripcion.replace("'", "''")

                    insert_sql = f"INSERT INTO consumos (fecha_consumo, producto_codigo, volumen_m3, descripcion, user_id) VALUES ('{fecha_iso}', '{producto_codigo}', {volumen}, '{guardar_desc}', '{user_id}');"
                    
                    insert_statements.append(insert_sql)
                    sheet_records += 1
                    total_records += 1
                    
                except Exception:
                    continue

            processed_sheets += 1
            print(f"✅ Hoja {sheet_name} finalizada: {sheet_records} registros")

        return {
            "success": True,
            "records_processed": total_records,
            "sheets_processed": processed_sheets,
            "errors": errors,
            "insert_statements": insert_statements,
            "message": f"¡Procesamiento Completado! {total_records} consumos extraídos."
        }

    except Exception as e:
        error_msg = f"Error en el procesamiento: {str(e)}"
        return {
            "success": False,
            "error": error_msg,
            "records_processed": 0,
            "errors": [error_msg],
            "insert_statements": []
        }
