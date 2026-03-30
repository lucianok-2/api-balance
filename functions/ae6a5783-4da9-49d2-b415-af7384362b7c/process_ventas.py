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
    temp_name = f"upload_{user_id}_{int(time.time())}.xlsx"
    temp_path = os.path.join(tempfile.gettempdir(), temp_name)
    
    try:
        # Guardar directamente con Flask
        file.save(temp_path)
        
        # Pequeño retardo para asegurar que Windows libere el handle de escritura
        # (A veces el sistema de archivos es más lento que la CPU)
        time.sleep(0.5)
        
        result = process_excel_file(temp_path, user_id)
        return result

    except Exception as e:
        return {"success": False, "error": f"Error general: {str(e)}", "records_processed": 0}
    finally:
        # Limpiar
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
        print(f"📄 Hojas encontradas en el archivo: {sheet_names}")

        for sheet_name in sheet_names:
            print(f"📊 Analizando hoja: {sheet_name}")
            
            # Leer las primeras 20 filas para buscar el header
            df_head = xl.parse(sheet_name, nrows=20, header=None)
            
            # Mapeo de palabras clave para identificar columnas (más flexible)
            mapeo_keywords = {
                "fecha": ["fecha", "fec", "date", "dia", "día"],
                "producto": ["producto", "prod", "item", "descripcion", "descripción", "artículo", "articulo"],
                "cliente": ["cliente", "destinatario", "receptor", "comprador"],
                "volumen": ["volumen", "m3", "m^3", "cantidad", "cant", "m3 total", "total m3"],
                "cert": ["certificacion", "certificación", "cert", "scs", "material"],
                "factura": ["factura", "guia", "guía", "n°", "numero", "número", "doc", "comprobante", "remisión"],
                "precio": ["precio", "unitario", "valor", "monto", "costo"]
            }

            header_row_idx = -1
            columnas_map = {} # target_name -> index
            
            # Buscar en cada una de las primeras 20 filas
            for i, row in df_head.iterrows():
                row_values = [str(val).strip().lower() for val in row.values]
                
                temp_map = {}
                # Buscar columnas requeridas (fecha, producto, cliente, volumen)
                requeridas = ["fecha", "producto", "cliente", "volumen"]
                
                for target in requeridas:
                    keywords = mapeo_keywords[target]
                    for idx, cell_val in enumerate(row_values):
                        if cell_val != "nan":
                            # Coincidencia exacta o la palabra clave está contenida en la celda
                            if any(k == cell_val or k in cell_val for k in keywords):
                                temp_map[target] = idx
                                break
                
                # Si encontramos al menos 3 de las 4 requeridas, es nuestra fila de encabezado
                if len(temp_map) >= 3:
                    header_row_idx = i
                    columnas_map = temp_map
                    # Buscar las opcionales (cert, factura, precio)
                    for target in ["cert", "factura", "precio"]:
                        keywords = mapeo_keywords[target]
                        for idx, cell_val in enumerate(row_values):
                            if cell_val != "nan" and idx not in columnas_map.values():
                                if any(k == cell_val or k in cell_val for k in keywords):
                                    columnas_map[target] = idx
                                    break
                    break
            
            if header_row_idx == -1:
                msg = f"No se encontró la estructura de columnas requerida en la hoja «{sheet_name}»"
                print(f"⚠️ {msg}")
                if len(df_head) > 5:
                    errors.append(msg)
                continue

            # 2. Leer la data real saltando hasta el header
            df = xl.parse(sheet_name, skiprows=header_row_idx + 1, header=None)
            print(f"✅ Hoja {sheet_name}: Header en fila {header_row_idx+1}. Procesando {len(df)} filas.")

            sheet_records = 0
            for index, row in df.iterrows():
                try:
                    # Validar que tengamos los índices necesarios
                    idx_fecha = columnas_map.get("fecha")
                    idx_vol = columnas_map.get("volumen")
                    idx_prod = columnas_map.get("producto")
                    idx_cli = columnas_map.get("cliente")

                    if idx_fecha is None or idx_vol is None or idx_prod is None or idx_cli is None:
                        continue

                    # Parsear Fecha robustamente
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

                    # Parsear M3 (Volumen)
                    val_vol = row[idx_vol] if idx_vol < len(row) else 0.0
                    try:
                        volumen = float(val_vol) if pd.notna(val_vol) else 0.0
                    except:
                        volumen = 0.0
                    
                    if volumen <= 0: continue

                    # Parsear Producto detectando Pallets para asignar W10.3
                    val_tipo_mat = row[idx_prod] if idx_prod < len(row) else ""
                    producto_codigo = ""
                    es_pallet = False
                    
                    if pd.notna(val_tipo_mat):
                        desc = str(val_tipo_mat).strip()
                        if 'pallet' in desc.lower():
                            producto_codigo = 'W10.3'
                            es_pallet = True
                        else:
                            match = re.match(r"^(\S+)", desc)
                            if match:
                                producto_codigo = match.group(1)

                    if not producto_codigo:
                        continue
                        
                    # Parsear Cliente
                    val_cliente = row[idx_cli] if idx_cli < len(row) else ""
                    cliente = str(val_cliente).strip() if pd.notna(val_cliente) else ""
                    
                    # Parsear Certificacion (vacio para pallets)
                    certificacion = "Material Controlado"
                    if es_pallet:
                        certificacion = ""
                    elif "cert" in columnas_map:
                        idx_cert = columnas_map["cert"]
                        val_cert = row[idx_cert] if idx_cert < len(row) else None
                        certificacion = str(val_cert).strip() if pd.notna(val_cert) else "Material Controlado"

                    # Parsear Factura/Guia (opcional)
                    num_factura = ""
                    if "factura" in columnas_map:
                        idx_fac = columnas_map["factura"]
                        val_fac = row[idx_fac] if idx_fac < len(row) else None
                        if pd.notna(val_fac):
                            num_factura = str(val_fac).strip()
                            
                    # Parsear Precio (opcional)
                    precio_unitario = "NULL"
                    if "precio" in columnas_map:
                        idx_pre = columnas_map["precio"]
                        val_precio = row[idx_pre] if idx_pre < len(row) else None
                        if pd.notna(val_precio):
                            try:
                                precio_unitario = float(val_precio)
                            except:
                                pass

                    # Generar INSERT statement (escapando comillas simples)
                    guardar_pc = producto_codigo.replace("'", "''")
                    guardar_cliente = cliente.replace("'", "''")
                    guardar_cert = certificacion.replace("'", "''")
                    guardar_fac = num_factura.replace("'", "''")

                    insert_sql = f"INSERT INTO ventas (fecha_venta, producto_codigo, cliente, num_factura, volumen_m3, certificacion, precio_unitario, user_id) VALUES ('{fecha_iso}', '{guardar_pc}', '{guardar_cliente}', '{guardar_fac}', {volumen}, '{guardar_cert}', {precio_unitario}, '{user_id}');"
                    
                    insert_statements.append(insert_sql)
                    sheet_records += 1
                    total_records += 1
                    
                except Exception as row_error:
                    continue

            processed_sheets += 1
            print(f"✅ Hoja {sheet_name} finalizada: {sheet_records} registros")

        return {
            "success": True,
            "records_processed": total_records,
            "sheets_processed": processed_sheets,
            "errors": errors,
            "insert_statements": insert_statements,
            "message": f"¡Procesamiento Completado! {total_records} ventas de pallets extraídas."
        }

    except Exception as e:
        error_msg = f"Error en el procesamiento: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "records_processed": total_records,
            "errors": errors,
            "insert_statements": insert_statements
        }
