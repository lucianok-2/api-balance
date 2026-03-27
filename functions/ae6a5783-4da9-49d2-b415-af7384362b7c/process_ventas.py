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
            
            # Mapeo de columnas para VENTAS
            fecha_col = "Fecha Venta"
            producto_col = "Producto Vendido"
            cliente_col = "Cliente"
            vol_col = "Volumen M3"
            cert_col = "Certificacion"
            factura_col = "Numero Factura"
            precio_col = "Precio Unitario"
            
            columnas_esperadas = [fecha_col, producto_col, cliente_col, vol_col, cert_col] # Factura y Precio son opcionales
            
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
            
            # Buscar opcionales
            for actual in df.columns:
                if actual.strip().lower() == factura_col.lower():
                    columnas_map[factura_col] = actual
                if actual.strip().lower() == precio_col.lower():
                    columnas_map[precio_col] = actual

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

                    # Parsear Producto
                    val_tipo_mat = row[columnas_map[producto_col]]
                    producto_codigo = ""
                    if pd.notna(val_tipo_mat):
                        match = re.match(r"^(\S+)", str(val_tipo_mat).strip())
                        if match:
                            producto_codigo = match.group(1)

                    if not producto_codigo:
                        continue
                        
                    # Parsear Cliente
                    val_cliente = row[columnas_map[cliente_col]]
                    cliente = str(val_cliente).strip() if pd.notna(val_cliente) else ""
                    
                    # Parsear Certificacion
                    val_cert = row[columnas_map[cert_col]]
                    certificacion = str(val_cert).strip() if pd.notna(val_cert) else "Material Controlado"

                    # Parsear Factura (opcional)
                    num_factura = ""
                    if factura_col in columnas_map:
                        val_fac = row[columnas_map[factura_col]]
                        if pd.notna(val_fac):
                            num_factura = str(val_fac).strip()
                            
                    # Parsear Precio (opcional)
                    precio_unitario = "NULL"
                    if precio_col in columnas_map:
                        val_precio = row[columnas_map[precio_col]]
                        if pd.notna(val_precio):
                            try:
                                precio_unitario = float(val_precio)
                            except:
                                pass

                    # Generar INSERT statement
                    guardar_pc = producto_codigo.replace("'", "''")
                    guardar_cliente = cliente.replace("'", "''")
                    guardar_cert = certificacion.replace("'", "''")
                    guardar_fac = num_factura.replace("'", "''")

                    insert_sql = f"""INSERT INTO ventas (fecha_venta, producto_codigo, cliente, num_factura, volumen_m3, certificacion, precio_unitario, user_id) 
VALUES ('{fecha_iso}', '{guardar_pc}', '{guardar_cliente}', '{guardar_fac}', {volumen}, '{guardar_cert}', {precio_unitario}, '{user_id}');"""

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
            "message": f"¡Procesamiento Completado! {total_records} ventas extraídas."
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
