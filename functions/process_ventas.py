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
    temp_name = f"upload_gen_sales_{user_id}_{int(time.time())}.xlsx"
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
        print(f"📄 Hojas encontradas (Gen): {sheet_names}")

        for sheet_name in sheet_names:
            print(f"📊 Analizando hoja: {sheet_name}")
            
            df_head = xl.parse(sheet_name, nrows=20, header=None)
            
            mapeo_keywords = {
                "fecha": ["fecha", "fec", "date", "dia", "día"],
                "producto": ["producto", "prod", "item", "descripcion", "descripción", "artículo", "articulo"],
                "cliente": ["cliente", "destinatario", "receptor", "comprador", "proveedor"],
                "volumen": ["volumen", "m3", "m^3", "cantidad", "cant", "neto"],
                "cert": ["certificacion", "certificación", "cert", "scs", "material"],
                "factura": ["factura", "guia", "guía", "n°", "numero", "número", "doc", "comprobante", "remisión"],
                "precio": ["precio", "unitario", "valor", "monto", "costo"]
            }

            header_row_idx = -1
            columnas_map = {} 
            
            for i, row in df_head.iterrows():
                row_values = [str(val).strip().lower() for val in row.values]
                temp_map = {}
                requeridas = ["fecha", "producto", "cliente", "volumen"]
                
                for target in requeridas:
                    keywords = mapeo_keywords[target]
                    for idx, cell_val in enumerate(row_values):
                        if cell_val != "nan":
                            if any(k == cell_val or k in cell_val for k in keywords):
                                temp_map[target] = idx
                                break
                
                if len(temp_map) >= 3:
                    header_row_idx = i
                    columnas_map = temp_map
                    for target in ["cert", "factura", "precio"]:
                        keywords = mapeo_keywords[target]
                        for idx, cell_val in enumerate(row_values):
                            if cell_val != "nan" and idx not in columnas_map.values():
                                if any(k == cell_val or k in cell_val for k in keywords):
                                    columnas_map[target] = idx
                                    break
                    break
            
            if header_row_idx == -1:
                print(f"⚠️ Estructura no detectada en {sheet_name}")
                continue

            df = xl.parse(sheet_name, skiprows=header_row_idx + 1, header=None)
            sheet_records = 0
            for index, row in df.iterrows():
                try:
                    idx_fecha = columnas_map.get("fecha")
                    idx_vol = columnas_map.get("volumen")
                    idx_prod = columnas_map.get("producto")
                    idx_cli = columnas_map.get("cliente")

                    if idx_fecha is None or idx_vol is None or idx_prod is None or idx_cli is None:
                        continue

                    val_fecha = row[idx_fecha] if idx_fecha < len(row) else None
                    if pd.isna(val_fecha): continue
                    
                    try:
                        fecha_dt = pd.to_datetime(val_fecha, errors='coerce')
                        if pd.isna(fecha_dt): continue
                        fecha_iso = fecha_dt.isoformat()
                    except:
                        continue

                    val_vol = row[idx_vol] if idx_vol < len(row) else 0.0
                    try:
                        volumen = float(val_vol) if pd.notna(val_vol) else 0.0
                    except:
                        volumen = 0.0
                    
                    if volumen <= 0: continue

                    # Detección de producto
                    val_prod = row[idx_prod] if idx_prod < len(row) else ""
                    producto_codigo = "W1.1" # Default genérico
                    
                    if pd.notna(val_prod):
                        desc = str(val_prod).strip()
                        if 'pallet' in desc.lower():
                            producto_codigo = 'W10.3'
                        elif 'w5.2' in desc.lower() or 'madera' in desc.lower():
                            producto_codigo = 'W5.2'
                        elif 'w3.1' in desc.lower() or 'astilla' in desc.lower():
                            producto_codigo = 'W3.1'
                        elif 'w3.2' in desc.lower() or 'aserrin' in desc.lower() or 'aserrín' in desc.lower():
                            producto_codigo = 'W3.2'
                        else:
                            # Intentar capturar primer palabra si parece un código
                            match = re.match(r"^(W\d+\.\d+)", desc, re.I)
                            if match:
                                producto_codigo = match.group(1).upper()

                    # Cliente
                    val_cliente = row[idx_cli] if idx_cli < len(row) else ""
                    cliente = str(val_cliente).strip() if pd.notna(val_cliente) else "Venta Genérica"
                    
                    # Certificación
                    certificacion = "Material Controlado"
                    if "cert" in columnas_map:
                        idx_cert = columnas_map["cert"]
                        val_cert = row[idx_cert] if idx_cert < len(row) else None
                        if pd.notna(val_cert):
                            certificacion = str(val_cert).strip()

                    # Factura
                    num_factura = ""
                    if "factura" in columnas_map:
                        idx_fac = columnas_map["factura"]
                        val_fac = row[idx_fac] if idx_fac < len(row) else None
                        if pd.notna(val_fac):
                            num_factura = str(val_fac).strip()
                            
                    # Precio
                    precio_unitario = "NULL"
                    if "precio" in columnas_map:
                        idx_pre = columnas_map["precio"]
                        val_precio = row[idx_pre] if idx_pre < len(row) else None
                        if pd.notna(val_precio):
                            try:
                                precio_unitario = float(val_precio)
                            except:
                                pass

                    # SQL
                    g_pc = producto_codigo.replace("'", "''")
                    g_cli = cliente.replace("'", "''")
                    g_cert = certificacion.replace("'", "''")
                    g_fac = num_factura.replace("'", "''")

                    insert_sql = f"INSERT INTO ventas (fecha_venta, producto_codigo, cliente, num_factura, volumen_m3, certificacion, precio_unitario, user_id) VALUES ('{fecha_iso}', '{g_pc}', '{g_cli}', '{g_fac}', {volumen}, '{g_cert}', {precio_unitario}, '{user_id}');"
                    
                    insert_statements.append(insert_sql)
                    sheet_records += 1
                    total_records += 1
                    
                except Exception:
                    continue

            processed_sheets += 1
            print(f"✅ Hoja {sheet_name} Gen finalizada: {sheet_records} registros")

        return {
            "success": True,
            "records_processed": total_records,
            "sheets_processed": processed_sheets,
            "errors": errors,
            "insert_statements": insert_statements,
            "message": f"¡Procesamiento Completado (Gen)! {total_records} registros extraídos."
        }

    except Exception as e:
        return {"success": False, "error": str(e), "records_processed": total_records}