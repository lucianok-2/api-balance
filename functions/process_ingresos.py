# process_ingresos.py
import os
import pandas as pd
from datetime import datetime
import tempfile


def process_file(file, user_id):
    """
    Función principal que será llamada por la API Flask

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
            # Ejecutar el procesamiento principal CON EL USER_ID
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
    Procesa el archivo Excel y genera INSERT statements
    
    Args:
        file_path: Ruta del archivo Excel a procesar
        user_id: ID del usuario autenticado
    """

    # ————————————————
    # 1) CONFIGURACIÓN
    # ————————————————

    # Código de producto de las recepciones (raw logs)
    PRODUCTO_CODIGO = "W1.1"

    # Año del reporte (se extrae del nombre de tu archivo)
    AÑO = 2025

    # Mapeo de nombres de hoja (meses) a número de mes
    MESES = {
        "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4,
        "MAYO": 5, "JUNIO": 6, "JULIO": 7, "AGOSTO": 8,
        "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12
    }

    total_records = 0
    processed_sheets = 0
    errors = []
    insert_statements = []

    try:
        # ————————————————
        # 2) CARGAR TODO EL EXCEL
        # ————————————————
        xf = pd.read_excel(file_path, sheet_name=None)

        # ————————————————
        # 3) PROCESAR CADA HOJA
        # ————————————————
        for sheet_name, df in xf.items():
            print(f"📊 Procesando hoja: {sheet_name} con {len(df)} filas")
            
            # Limpieza de nombres de columna (quita espacios al inicio/fin)
            df.columns = df.columns.str.strip()
            
            print(f"📋 Columnas encontradas: {list(df.columns)}")
            
            # DEBUGGING: Mostrar las primeras 5 filas para entender la estructura
            print(f"🔍 Primeras 5 filas de datos:")
            for i in range(min(5, len(df))):
                print(f"  Fila {i}: NOMBRE PROVEEDOR = '{df.iloc[i]['NOMBRE PROVEEDOR']}' (tipo: {type(df.iloc[i]['NOMBRE PROVEEDOR'])})")
                if pd.notna(df.iloc[i]['NOMBRE PROVEEDOR']):
                    print(f"    -> Valor no nulo: '{str(df.iloc[i]['NOMBRE PROVEEDOR']).strip()}'")
                else:
                    print(f"    -> Valor nulo o NaN")

            # Detectar automáticamente las columnas correctas
            proveedor_col = "NOMBRE PROVEEDOR"
            
            # Buscar columna de número de guía (puede ser ROL, Folio, o Numero Guía)
            guia_cols = [col for col in df.columns if any(x in col.upper() for x in ['ROL', 'FOLIO', 'NUMERO GUIA', 'GUIA'])]
            if guia_cols:
                guia_col = guia_cols[0]
                print(f"📋 Usando columna de guía: {guia_col}")
            else:
                guia_col = "ROL"  # Fallback
            
            # Buscar columna de certificación FSC
            cert_cols = [col for col in df.columns if 'FSC' in col.upper() or 'CERTIFICACION' in col.upper() or 'DESCRIPCION' in col.upper()]
            if cert_cols:
                cert_col = cert_cols[0]
                print(f"📋 Usando columna de certificación: {cert_col}")
            else:
                cert_col = None  # Opcional
            
            # Buscar columna de volumen
            vol_cols = [col for col in df.columns if 'M3' in col.upper() or 'VOLUMEN' in col.upper()]
            if vol_cols:
                vol_col = vol_cols[0]
                print(f"📋 Usando columna de volumen: {vol_col}")
            else:
                vol_col = "M3 o m3st"  # Fallback
            
            # Verificar que las columnas principales existan
            required_cols = [proveedor_col, vol_col]
            if guia_col not in df.columns:
                print(f"⚠️ No se encontró columna de guía, se usará un valor genérico")
            else:
                required_cols.append(guia_col)
                
            missing_cols = [c for c in required_cols if c not in df.columns]
            
            # Verificar si existe columna de fecha
            fecha_cols = [col for col in df.columns if 'FECHA' in col.upper() or 'DATE' in col.upper()]
            if fecha_cols:
                fecha_col = fecha_cols[0]
                print(f"📅 Usando columna de fecha: {fecha_col}")
            else:
                print("⚠️ No se encontró columna de fecha, usando fecha fija")
                fecha_col = None
            
            if missing_cols:
                error_msg = f"No encontré las columnas {missing_cols} en la hoja «{sheet_name}»"
                errors.append(error_msg)
                print(f"❌ {error_msg}")
                continue

            sheet_records = 0

            # Itera sobre cada fila de la hoja
            for index, row in df.iterrows():
                try:
                    # Obtener proveedor (requerido)
                    if pd.notna(row[proveedor_col]):
                        proveedor = str(row[proveedor_col]).strip()
                    else:
                        print(f"⚠️ Saltando fila {index}: proveedor vacío")
                        continue
                    
                    # Obtener número de guía (puede ser opcional)
                    if guia_col in df.columns and pd.notna(row[guia_col]):
                        num_guia = str(row[guia_col]).strip()
                    else:
                        num_guia = f"AUTO-{sheet_name}-{index}"  # Generar un número automático
                        print(f"⚠️ Fila {index}: usando número de guía automático: {num_guia}")
                    
                    # Obtener certificación (puede ser opcional)
                    if cert_col and cert_col in df.columns and pd.notna(row[cert_col]):
                        certificacion = str(row[cert_col]).strip()
                    else:
                        certificacion = "Material Controlado"  # Valor por defecto
                        print(f"⚠️ Fila {index}: usando certificación por defecto")

                    # Validar que no sean valores vacíos o NaN
                    if proveedor in ["nan", "None", ""]:
                        print(f"⚠️ Saltando fila {index}: proveedor vacío")
                        continue
                    
                    # Obtener volumen (requerido)
                    try:
                        if pd.notna(row[vol_col]):
                            volumen = float(row[vol_col])
                            if volumen <= 0:
                                print(f"⚠️ Saltando fila {index}: volumen no positivo ({volumen})")
                                continue
                        else:
                            print(f"⚠️ Saltando fila {index}: volumen vacío")
                            continue
                    except (ValueError, TypeError):
                        print(f"⚠️ Saltando fila {index}: error al convertir volumen")
                        continue

                    # Obtener fecha del registro o usar fecha fija
                    if fecha_col and fecha_col in df.columns and pd.notna(row[fecha_col]):
                        try:
                            fecha = pd.to_datetime(row[fecha_col])
                            print(f"📅 Fila {index}: Fecha del registro: {fecha}")
                        except:
                            # Si hay error al convertir la fecha, usar el mes de la hoja
                            mes_num = MESES.get(sheet_name.strip().upper(), 1)  # Default a enero
                            fecha = datetime(AÑO, mes_num, 1)
                            print(f"📅 Fila {index}: Error en fecha, usando mes de la hoja: {fecha}")
                    else:
                        # Usar el mes de la hoja
                        mes_num = MESES.get(sheet_name.strip().upper(), 1)  # Default a enero
                        fecha = datetime(AÑO, mes_num, 1)
                        print(f"📅 Fila {index}: Usando fecha basada en hoja: {fecha}")

                    # Generar INSERT statement CON EL USER_ID REAL
                    insert_sql = f"""INSERT INTO recepciones (fecha_recepcion, producto_codigo, proveedor, num_guia, volumen_m3, certificacion, user_id) 
VALUES ('{fecha.isoformat()}', '{PRODUCTO_CODIGO}', '{proveedor.replace("'", "''")}', '{num_guia}', {volumen}, '{certificacion.replace("'", "''")}', '{user_id}');"""

                    insert_statements.append(insert_sql)

                    # Log del registro procesado CON EL USER_ID REAL
                    record = {
                        "fecha_recepcion": fecha.isoformat(),
                        "producto_codigo": PRODUCTO_CODIGO,
                        "proveedor": proveedor,
                        "num_guia": num_guia,
                        "volumen_m3": volumen,
                        "certificacion": certificacion,
                        "user_id": user_id  # USAR EL USER_ID REAL DEL USUARIO AUTENTICADO
                    }

                    print("✅ Procesado:", record)
                    sheet_records += 1
                    total_records += 1
                        
                except Exception as row_error:
                    print(f"❌ Error procesando fila {index}: {row_error}")
                    continue

            processed_sheets += 1
            print(f"✅ Hoja {sheet_name} procesada: {sheet_records} registros")

        print("¡Procesamiento completado!")

        return {
            "success": True,
            "records_processed": total_records,
            "sheets_processed": processed_sheets,
            "total_sheets": len(xf),
            "errors": errors,
            "insert_statements": insert_statements,
            "message": f"¡Procesamiento completado! {total_records} registros procesados de {processed_sheets} hojas."
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
