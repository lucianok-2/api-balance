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
            
            # Mapeo de columnas para VENTAS soportando múltiples formatos
            opciones_fecha = ["Fecha Venta", "Fecha"]
            opciones_producto = ["Producto Vendido", "Producto"]
            opciones_cliente = ["Cliente"]
            opciones_vol = ["Volumen M3", "Total m3"]
            opciones_cert = ["Certificacion"]
            opciones_factura = ["Numero Factura", "N° Guía", "N° Guia"]
            opciones_precio = ["Precio Unitario"]
            
            def encontrar_columna(opciones, df_cols):
                for opc in opciones:
                    for real_col in df_cols:
                        if real_col.strip().lower() == opc.lower():
                            return real_col
                return None
            
            fecha_col = encontrar_columna(opciones_fecha, df.columns)
            producto_col = encontrar_columna(opciones_producto, df.columns)
            cliente_col = encontrar_columna(opciones_cliente, df.columns)
            vol_col = encontrar_columna(opciones_vol, df.columns)
            cert_col = encontrar_columna(opciones_cert, df.columns)
            factura_col = encontrar_columna(opciones_factura, df.columns)
            precio_col = encontrar_columna(opciones_precio, df.columns)
            
            # Requeridas: Fecha, Producto, Cliente, Vol
            requeridas = {
                "Fecha": fecha_col,
                "Producto": producto_col,
                "Cliente": cliente_col,
                "Volumen M3": vol_col
            }
            
            faltan = []
            for req_name, fnd_col in requeridas.items():
                if not fnd_col:
                    faltan.append(req_name)
                    
            if faltan:
                error_msg = f"Faltan columnas requeridas en la hoja «{sheet_name}»: {', '.join(faltan)}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")
                continue

            sheet_records = 0

            for index, row in df.iterrows():
                try:
                    # Parsear Fecha robustamente
                    val_fecha = row[fecha_col]
                    if pd.isna(val_fecha): continue
                    
                    try:
                        if isinstance(val_fecha, pd.Timestamp):
                            fecha_dt = val_fecha
                        else:
                            fecha_dt = pd.to_datetime(val_fecha, errors='coerce')
                        
                        if pd.isna(fecha_dt):
                            continue
                        fecha_iso = fecha_dt.isoformat()
                    except:
                        continue

                    # Parsear M3 (Volumen)
                    val_vol = row[vol_col]
                    try:
                        volumen = float(val_vol) if pd.notna(val_vol) else 0.0
                    except:
                        volumen = 0.0
                    
                    if volumen <= 0: continue

                    # Parsear Producto detectando Pallets para asignar W10.3
                    val_tipo_mat = row[producto_col]
                    producto_codigo = ""
                    es_pallet = False
                    
                    if pd.notna(val_tipo_mat):
                        desc = str(val_tipo_mat).strip()
                        if 'pallet' in desc.lower():
                            producto_codigo = 'W10.3'
                            es_pallet = True
                        else:
                            # Buscar el primer código (palabra) de la descripción
                            match = re.match(r"^(\S+)", desc)
                            if match:
                                producto_codigo = match.group(1)

                    if not producto_codigo:
                        continue
                        
                    # Parsear Cliente
                    val_cliente = row[cliente_col]
                    cliente = str(val_cliente).strip() if pd.notna(val_cliente) else ""
                    
                    # Parsear Certificacion (vacio para pallets)
                    certificacion = "Material Controlado"
                    if es_pallet:
                        certificacion = "" # Pallets sin certificación según requerimiento
                    elif cert_col:
                        val_cert = row[cert_col]
                        certificacion = str(val_cert).strip() if pd.notna(val_cert) else "Material Controlado"

                    # Parsear Factura/Guia (opcional)
                    num_factura = ""
                    if factura_col:
                        val_fac = row[factura_col]
                        if pd.notna(val_fac):
                            num_factura = str(val_fac).strip()
                            
                    # Parsear Precio (opcional)
                    precio_unitario = "NULL"
                    if precio_col:
                        val_precio = row[precio_col]
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
