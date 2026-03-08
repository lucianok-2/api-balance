import os
import pandas as pd
from datetime import datetime
import tempfile
import re

def process_file(file, user_id):
    """
    Función principal que será llamada por la API Flask para procesar el ID 6

    Args:
        file: Archivo subido desde el frontend
        user_id: ID del usuario autenticado que está procesando el archivo

    Returns:
        dict: Resultado del procesamiento con INSERT statements
    """
    if not file:
        return {
            "success": False,
            "error": "No se proporcionó ningún archivo"
        }

    try:
        # Guardar archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name

        try:
            # Ejecutar el procesamiento principal
            result = process_excel_file(temp_path, user_id)
            return result

        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        return {
            "success": False,
            "error": f"Error general: {str(e)}",
            "records_processed": 0
        }

def process_excel_file(file_path, user_id):
    """
    Procesa el archivo Excel para recepciones y genera INSERT statements
    
    Args:
        file_path: Ruta del archivo Excel a procesar
        user_id: ID del usuario autenticado
    """

    total_records = 0
    processed_sheets = 0
    errors = []
    insert_statements = []

    try:
        # Cargar excel con múltiples hojas, aunque usualmente es una sola
        xf = pd.read_excel(file_path, sheet_name=None)

        for sheet_name, df in xf.items():
            print(f"📊 Procesando hoja: {sheet_name} con {len(df)} filas")
            
            # Limpieza de nombres de columna (quita espacios al inicio/fin)
            df.columns = df.columns.astype(str).str.strip()
            
            # Mapeo de columnas desde el Excel a las variables internas
            fecha_col = "fecha"
            proveedor_col = "proveedor"
            guia_col = "Guía"
            vol_col = "M3"
            cert_col = "Categoría Proveedor"
            rol_col = "rol predio"
            comuna_col = "comuna"
            tipo_mat_col = "Tipo de material"
            
            # Buscar columnas ignorando case si es necesario, pero intentamos exacto primero
            columnas_esperadas = [fecha_col, proveedor_col, guia_col, vol_col, cert_col, rol_col, comuna_col, tipo_mat_col]
            
            # Normalizar columnas (case insensitive fallback) si no se encuentran exactamente
            columnas_map = {}
            for expected in columnas_esperadas:
                found = False
                for actual in df.columns:
                    if actual.lower() == expected.lower():
                        columnas_map[expected] = actual
                        found = True
                        break
                if not found:
                    error_msg = f"No encontré la columna '{expected}' en la hoja «{sheet_name}»"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
            
            if len(columnas_map) < len(columnas_esperadas):
                print(f"⚠️ Faltan columnas requeridas en hoja {sheet_name}, se omitirá.")
                continue

            sheet_records = 0

            # Itera sobre cada fila del DataFrame
            for index, row in df.iterrows():
                try:
                    # Parsear Fecha
                    val_fecha = row[columnas_map[fecha_col]]
                    if pd.isna(val_fecha):
                        continue # requerida
                    if isinstance(val_fecha, pd.Timestamp):
                        fecha_iso = val_fecha.isoformat()
                    else:
                        fecha_iso = pd.to_datetime(val_fecha, errors='coerce').isoformat()

                    # Parsear Proveedor
                    val_prov = row[columnas_map[proveedor_col]]
                    if pd.isna(val_prov) or str(val_prov).strip() == "":
                        continue
                    proveedor = str(val_prov).strip()

                    # Parsear Guía
                    val_guia = row[columnas_map[guia_col]]
                    num_guia = str(val_guia).strip() if pd.notna(val_guia) else ""

                    # Parsear M3 (Volumen)
                    val_vol = row[columnas_map[vol_col]]
                    try:
                        volumen = float(val_vol) if pd.notna(val_vol) else 0.0
                    except:
                        volumen = 0.0
                    
                    if volumen <= 0:
                        continue

                    # Parsear Certificación
                    val_cert = row[columnas_map[cert_col]]
                    certificacion = str(val_cert).strip() if pd.notna(val_cert) else "Material Controlado"

                    # Parsear Rol Predio
                    val_rol = row[columnas_map[rol_col]]
                    rol_predio = str(val_rol).strip() if pd.notna(val_rol) else ""

                    # Parsear Comuna
                    val_comuna = row[columnas_map[comuna_col]]
                    comuna = str(val_comuna).strip() if pd.notna(val_comuna) else ""

                    # Parsear Tipo de Material -> Producto Codigo
                    val_tipo_mat = row[columnas_map[tipo_mat_col]]
                    producto_codigo = ""
                    if pd.notna(val_tipo_mat):
                        # Extraer solo el codigo (e.g. "W1.1" de "W1.1 Trozo de pinus radiata")
                        match = re.match(r"^(\S+)", str(val_tipo_mat).strip())
                        if match:
                            producto_codigo = match.group(1)

                    # Generar INSERT statement
                    guardar_p = proveedor.replace("'", "''")
                    guardar_g = num_guia.replace("'", "''")
                    guardar_c = certificacion.replace("'", "''")
                    guardar_r = rol_predio.replace("'", "''")
                    guardar_com = comuna.replace("'", "''")
                    guardar_pc = producto_codigo.replace("'", "''")

                    insert_sql = f"""INSERT INTO recepciones (fecha_recepcion, proveedor, num_guia, volumen_m3, certificacion, rol_predio, comuna, producto_codigo, user_id) 
VALUES ('{fecha_iso}', '{guardar_p}', '{guardar_g}', {volumen}, '{guardar_c}', '{guardar_r}', '{guardar_com}', '{guardar_pc}', '{user_id}');"""

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
            "message": f"¡Procesamiento completado! {total_records} registros procesados."
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
