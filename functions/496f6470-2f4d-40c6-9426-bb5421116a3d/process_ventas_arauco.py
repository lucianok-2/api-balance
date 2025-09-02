# process_ventas_arauco.py - Procesador para proforma ARAUCO (archivos XLSX)
import os
import pandas as pd
from datetime import datetime
import tempfile


def process_file(file, user_id):
    """
    Función principal que será llamada por la API Flask para procesar proforma ARAUCO

    Args:
        file: Archivo subido desde el frontend
        user_id: ID del usuario autenticado

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
    Procesa el archivo Excel de proforma ARAUCO y genera INSERT statements

    Args:
        file_path: Ruta del archivo Excel a procesar
        user_id: ID del usuario autenticado
    """
    
    print("🔥🔥🔥 EJECUTANDO SCRIPT DE PROFORMA ARAUCO 🔥🔥🔥")
    print(f"🎯 Archivo: {file_path}")
    print(f"👤 Usuario: {user_id}")
    print("🔥🔥🔥 ESTE ES EL SCRIPT PARA PROFORMA ARAUCO 🔥🔥🔥")

    # ————————————————
    # 1) CONFIGURACIÓN
    # ————————————————

    # Cliente fijo para todas las ventas ARAUCO
    CLIENTE = "ARAUCO"

    # Certificación por defecto
    CERTIFICACION_DEFAULT = "Material Controlado"

    # Mapeo de códigos adicionales a productos
    CODIGO_PRODUCTO_MAPPING = {
        "ASCM": "W3.2",  # Aserrín
        "ASTI": "W3.1"   # Astillas
    }

    total_records = 0
    processed_sheets = 0
    errors = []
    insert_statements = []

    try:
        print(f"📁 Procesando archivo XLSX: {file_path}")
        
        # ————————————————
        # 2) CARGAR TODO EL EXCEL
        # ————————————————
        # Leer archivo XLSX usando openpyxl
        try:
            print("🔧 Usando engine 'openpyxl' para archivo .xlsx")
            xf = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
        except Exception as read_error:
            print(f"❌ Error leyendo archivo Excel: {read_error}")
            # Intentar con engine automático como fallback
            print("🔄 Intentando con engine automático...")
            xf = pd.read_excel(file_path, sheet_name=None)

        # ————————————————
        # 3) PROCESAR CADA HOJA
        # ————————————————
        for sheet_name, df in xf.items():
            print(f"📊 Procesando hoja: {sheet_name} con {len(df)} filas")

            # Limpieza de nombres de columna (quita espacios al inicio/fin)
            df.columns = df.columns.str.strip()

            print(f"📋 Columnas encontradas: {list(df.columns)}")

            # Mapear las columnas requeridas (buscar variaciones)
            column_mapping = {}

            # Buscar FCH_RECEPCION (fecha de venta)
            for col in df.columns:
                col_clean = str(col).upper().replace('_', '').replace(' ', '')
                if 'FCHRECEPCION' in col_clean or 'FCH_RECEPCION' in col.upper():
                    column_mapping['fecha_venta'] = col
                    print(f"📅 Columna de fecha recepción encontrada: {col}")
                    break

            # Buscar NUM_GUIA_SERIE_C (número de factura)
            for col in df.columns:
                col_clean = str(col).upper().replace('_', '').replace(' ', '')
                if 'NUMGUIASERIEC' in col_clean or 'NUM_GUIA_SERIE_C' in col.upper():
                    column_mapping['num_factura'] = col
                    print(f"📄 Columna de número guía encontrada: {col}")
                    break

            # Buscar VOLUMEN_M3_RECEPCION (volumen)
            for col in df.columns:
                col_clean = str(col).upper().replace('_', '').replace(' ', '')
                if 'VOLUMENM3RECEPCION' in col_clean or 'VOLUMEN_M3_RECEPCION' in col.upper():
                    column_mapping['volumen_m3'] = col
                    print(f"📦 Columna de volumen encontrada: {col}")
                    break

            # Buscar COD_ADICIONAL (para determinar producto)
            for col in df.columns:
                col_clean = str(col).upper().replace('_', '').replace(' ', '')
                if 'CODADICIONAL' in col_clean or 'COD_ADICIONAL' in col.upper():
                    column_mapping['cod_adicional'] = col
                    print(f"🏷️ Columna de código adicional encontrada: {col}")
                    break

            print(f"📋 Mapeo de columnas: {column_mapping}")

            # Verificar que se encontraron las columnas requeridas
            required_fields = ['fecha_venta', 'num_factura', 'volumen_m3', 'cod_adicional']
            missing_fields = [
                field for field in required_fields if field not in column_mapping]

            if missing_fields:
                error_msg = f"No se encontraron las columnas requeridas en la hoja «{sheet_name}»: {missing_fields}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")
                continue

            sheet_records = 0

            # Itera sobre cada fila de la hoja
            for index, row in df.iterrows():
                try:
                    # Obtener fecha de venta (requerido)
                    if pd.notna(row[column_mapping['fecha_venta']]):
                        try:
                            fecha_venta = pd.to_datetime(row[column_mapping['fecha_venta']])
                            print(f"📅 Fila {index}: Fecha procesada: {fecha_venta}")
                        except Exception as date_error:
                            print(f"⚠️ Saltando fila {index}: error al procesar fecha - {date_error}")
                            continue
                    else:
                        print(f"⚠️ Saltando fila {index}: fecha venta vacía")
                        continue

                    # Cliente fijo ARAUCO
                    cliente = CLIENTE
                    print(f"👤 Fila {index}: Cliente fijo: {cliente}")

                    # Obtener número de factura (requerido)
                    if pd.notna(row[column_mapping['num_factura']]):
                        try:
                            # Convertir a string y limpiar
                            num_factura = str(row[column_mapping['num_factura']]).strip()
                            # Si es un número, convertir a entero para eliminar decimales
                            try:
                                num_factura_int = int(float(num_factura))
                                num_factura = str(num_factura_int)
                            except (ValueError, TypeError):
                                pass  # Mantener como string si no es numérico
                            print(f"📄 Fila {index}: Número factura: {num_factura}")
                        except Exception:
                            print(f"⚠️ Saltando fila {index}: error al procesar número de factura")
                            continue
                    else:
                        print(f"⚠️ Saltando fila {index}: número de factura vacío")
                        continue

                    # Obtener volumen (requerido y debe ser > 0)
                    try:
                        if pd.notna(row[column_mapping['volumen_m3']]):
                            volumen = float(row[column_mapping['volumen_m3']])
                            if volumen <= 0:
                                print(f"⚠️ Saltando fila {index}: volumen es 0 o negativo ({volumen})")
                                continue
                            print(f"📦 Fila {index}: Volumen: {volumen}")
                        else:
                            print(f"⚠️ Saltando fila {index}: volumen vacío")
                            continue
                    except (ValueError, TypeError):
                        print(f"⚠️ Saltando fila {index}: error al convertir volumen")
                        continue

                    # Determinar código de producto basado en COD_ADICIONAL
                    producto_codigo = "W3.2"  # Valor por defecto (aserrín)
                    
                    if pd.notna(row[column_mapping['cod_adicional']]):
                        cod_adicional = str(row[column_mapping['cod_adicional']]).strip().upper()
                        print(f"🏷️ Fila {index}: Código adicional: {cod_adicional}")
                        
                        if cod_adicional in CODIGO_PRODUCTO_MAPPING:
                            producto_codigo = CODIGO_PRODUCTO_MAPPING[cod_adicional]
                            print(f"✅ Fila {index}: Producto identificado: {cod_adicional} → {producto_codigo}")
                        else:
                            print(f"⚠️ Fila {index}: Código adicional no reconocido '{cod_adicional}', usando W3.2 por defecto")
                    else:
                        print(f"🏷️ Fila {index}: Sin código adicional, usando W3.2 por defecto")

                    # Validar que no sean valores vacíos
                    if num_factura in ["nan", "None", ""] or cliente in ["nan", "None", ""]:
                        print(f"⚠️ Saltando fila {index}: datos vacíos")
                        continue

                    # Generar INSERT statement para la tabla ventas (precio_unitario como NULL)
                    insert_sql = f"""INSERT INTO ventas (fecha_venta, producto_codigo, cliente, num_factura, volumen_m3, certificacion, precio_unitario, user_id) 
VALUES ('{fecha_venta.isoformat()}', '{producto_codigo}', '{cliente.replace("'", "''")}', '{num_factura}', {volumen}, '{CERTIFICACION_DEFAULT}', NULL, '{user_id}');"""

                    insert_statements.append(insert_sql)

                    # Log del registro procesado
                    record = {
                        "fecha_venta": fecha_venta.isoformat(),
                        "producto_codigo": producto_codigo,
                        "cliente": cliente,
                        "num_factura": num_factura,
                        "volumen_m3": volumen,
                        "certificacion": CERTIFICACION_DEFAULT,
                        "precio_unitario": None,
                        "user_id": user_id
                    }

                    print(f"✅ Procesado: {record}")
                    sheet_records += 1
                    total_records += 1

                except Exception as row_error:
                    print(f"❌ Error procesando fila {index}: {row_error}")
                    errors.append(f"Error en fila {index}: {str(row_error)}")
                    continue

            processed_sheets += 1
            print(f"✅ Hoja {sheet_name} procesada: {sheet_records} registros")

        print("¡Procesamiento de proforma ARAUCO completado!")
        
        # DEBUG: Mostrar los primeros INSERT statements generados
        print("🔍 DEBUG - PRIMEROS INSERT STATEMENTS GENERADOS:")
        for i, stmt in enumerate(insert_statements[:3]):
            print(f"📝 Statement {i+1}: {stmt}")
        print(f"📊 Total de INSERT statements generados: {len(insert_statements)}")

        return {
            "success": True,
            "records_processed": total_records,
            "sheets_processed": processed_sheets,
            "total_sheets": len(xf),
            "errors": errors,
            "insert_statements": insert_statements,
            "message": f"¡Procesamiento de proforma ARAUCO completado! {total_records} registros procesados de {processed_sheets} hojas."
        }

    except Exception as e:
        error_msg = f"Error en el procesamiento de proforma ARAUCO: {str(e)}"
        print(f"❌ {error_msg}")
        errors.append(error_msg)

        return {
            "success": False,
            "error": error_msg,
            "records_processed": total_records,
            "errors": errors,
            "insert_statements": insert_statements
        }