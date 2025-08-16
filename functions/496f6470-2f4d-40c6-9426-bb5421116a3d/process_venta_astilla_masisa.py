# process_venta_astilla_masisa.py - Procesador específico para ventas de astilla MASISA (archivos XLSX)
import os
import pandas as pd
from datetime import datetime
import tempfile


def process_file(file, user_id):
    """
    Función principal que será llamada por la API Flask para procesar ventas de astilla MASISA

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


def convert_date_number_to_datetime(date_number):
    """
    Convierte un número de fecha como 20250728 a datetime

    Args:
        date_number: Número de fecha en formato YYYYMMDD

    Returns:
        datetime: Fecha convertida
    """
    try:
        # Convertir a string y extraer año, mes, día
        date_str = str(int(date_number))
        if len(date_str) == 8:  # YYYYMMDD
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            return datetime(year, month, day)
        else:
            raise ValueError(f"Formato de fecha inválido: {date_number}")
    except Exception as e:
        raise ValueError(f"Error al convertir fecha {date_number}: {str(e)}")


def process_excel_file(file_path, user_id):
    """
    Procesa el archivo Excel de ventas MASISA y genera INSERT statements

    Args:
        file_path: Ruta del archivo Excel a procesar
        user_id: ID del usuario autenticado
    """

    print("🚀🚀🚀 EJECUTANDO SCRIPT DE VENTAS MASISA - NO RECEPCIONES 🚀🚀🚀")
    print(f"🎯 Archivo: {file_path}")
    print(f"👤 Usuario: {user_id}")
    print("🚀🚀🚀 ESTE ES EL SCRIPT CORRECTO PARA VENTAS 🚀🚀🚀")

    # ————————————————
    # 1) CONFIGURACIÓN
    # ————————————————

    # Certificación por defecto
    CERTIFICACION_DEFAULT = "Material Controlado"

    # Mapeo de productos según descripción
    PRODUCTO_MAPPING = {
        "MATERIAL VERDE VALOR. COMB. COGENERACION": {
            "codigo": "W3.2",  # Aserrín
            "nombre": "Aserrín pinus radiata",
            "factor_conversion": 1.0  # Sin conversión
        },
        "ASTILLA VERDE (TS)": {
            "codigo": "W3.1",  # Astilla
            "nombre": "Astillas pinus radiata",
            "factor_conversion": 2.54 / 1000  # (Recepción/1000)*2,54
        }
    }

    total_records = 0
    processed_sheets = 0
    errors = []
    insert_statements = []

    try:
        print(f"📁 Procesando archivo XLSX: {file_path}")
        print(f"📁 Extensión del archivo: {file_path.lower().split('.')[-1]}")

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

            # Buscar "Fecha contabiliz." (con variaciones de caracteres especiales)
            for col in df.columns:
                col_clean = str(col).upper().replace(
                    'Ó', 'O').replace('Í', 'I').replace('Á', 'A')
                if 'FECHA' in col_clean and ('CONTABILIZ' in col_clean or 'CONTABIL' in col_clean):
                    column_mapping['fecha_contabiliz'] = col
                    print(f"📅 Columna de fecha encontrada: {col}")
                    break

            # Buscar "Guía Flete" (con variaciones de caracteres especiales)
            for col in df.columns:
                col_clean = str(col).upper().replace(
                    'Í', 'I').replace('Á', 'A')
                if ('GUIA' in col_clean or 'GU�A' in col_clean) and 'FLETE' in col_clean:
                    column_mapping['guia_flete'] = col
                    print(f"🚚 Columna de guía flete encontrada: {col}")
                    break

            # Buscar "Descripción Material" (con variaciones de caracteres especiales)
            for col in df.columns:
                col_clean = str(col).upper().replace(
                    'Ó', 'O').replace('Í', 'I').replace('Á', 'A')
                if ('DESCRIPCION' in col_clean or 'DESCRIPC' in col_clean) and 'MATERIAL' in col_clean:
                    column_mapping['descripcion_material'] = col
                    print(
                        f"📝 Columna de descripción material encontrada: {col}")
                    break

            # Buscar "Recepción" (con variaciones de caracteres especiales)
            for col in df.columns:
                col_clean = str(col).upper().replace(
                    'Ó', 'O').replace('Í', 'I').replace('Á', 'A')
                if 'RECEPCION' in col_clean or 'RECEPC' in col_clean:
                    column_mapping['recepcion'] = col
                    print(f"📦 Columna de recepción encontrada: {col}")
                    break

            print(f"📋 Mapeo de columnas: {column_mapping}")

            # Verificar que se encontraron las columnas requeridas
            required_fields = ['fecha_contabiliz',
                               'guia_flete', 'descripcion_material', 'recepcion']
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
                    # Obtener fecha contabilización (requerido)
                    if pd.notna(row[column_mapping['fecha_contabiliz']]):
                        try:
                            fecha_numero = int(
                                float(row[column_mapping['fecha_contabiliz']]))
                            fecha_venta = convert_date_number_to_datetime(
                                fecha_numero)
                            print(
                                f"📅 Fila {index}: Fecha convertida: {fecha_numero} → {fecha_venta}")
                        except (ValueError, TypeError) as e:
                            print(
                                f"⚠️ Saltando fila {index}: error al convertir fecha: {e}")
                            continue
                    else:
                        print(
                            f"⚠️ Saltando fila {index}: fecha contabilización vacía")
                        continue

                    # Obtener guía flete (requerido)
                    if pd.notna(row[column_mapping['guia_flete']]):
                        try:
                            # Convertir a entero para eliminar decimales si es necesario
                            guia_flete_int = int(
                                float(row[column_mapping['guia_flete']]))
                            guia_flete = str(guia_flete_int)
                            print(
                                f"📋 Fila {index}: Guía flete convertida: {row[column_mapping['guia_flete']]} → {guia_flete}")
                        except (ValueError, TypeError):
                            guia_flete = str(
                                row[column_mapping['guia_flete']]).strip()
                            print(
                                f"📋 Fila {index}: Guía flete como string: {guia_flete}")
                    else:
                        print(f"⚠️ Saltando fila {index}: guía flete vacía")
                        continue

                    # Obtener descripción material (requerido)
                    if pd.notna(row[column_mapping['descripcion_material']]):
                        descripcion_material = str(
                            row[column_mapping['descripcion_material']]).strip()
                        print(
                            f"📋 Fila {index}: Descripción material: {descripcion_material}")
                    else:
                        print(
                            f"⚠️ Saltando fila {index}: descripción material vacía")
                        continue

                    # Verificar si la descripción coincide con algún producto conocido
                    producto_info = None
                    for desc_key, info in PRODUCTO_MAPPING.items():
                        if desc_key.upper() in descripcion_material.upper():
                            producto_info = info
                            print(
                                f"✅ Fila {index}: Producto identificado: {desc_key} → {info['codigo']}")
                            break

                    if not producto_info:
                        print(
                            f"⚠️ Saltando fila {index}: descripción material no reconocida: {descripcion_material}")
                        continue

                    # Obtener volumen de recepción (requerido y debe ser > 0)
                    try:
                        if pd.notna(row[column_mapping['recepcion']]):
                            volumen_original = float(
                                row[column_mapping['recepcion']])
                            if volumen_original <= 0:
                                print(
                                    f"⚠️ Saltando fila {index}: volumen es 0 o negativo ({volumen_original})")
                                continue

                            # Aplicar factor de conversión según el producto
                            if producto_info['codigo'] == 'W3.1':  # Astilla
                                volumen_final = volumen_original * \
                                    producto_info['factor_conversion']
                                print(
                                    f"🔄 Fila {index}: Conversión astilla: {volumen_original} * {producto_info['factor_conversion']} = {volumen_final}")
                            else:  # Aserrín
                                volumen_final = volumen_original
                                print(
                                    f"📊 Fila {index}: Volumen aserrín sin conversión: {volumen_final}")
                        else:
                            print(
                                f"⚠️ Saltando fila {index}: volumen recepción vacío")
                            continue
                    except (ValueError, TypeError):
                        print(
                            f"⚠️ Saltando fila {index}: error al convertir volumen")
                        continue

                    # Validar que no sean valores vacíos
                    if guia_flete in ["nan", "None", ""] or descripcion_material in ["nan", "None", ""]:
                        print(f"⚠️ Saltando fila {index}: datos vacíos")
                        continue

                    # Generar INSERT statement para la tabla ventas (usando num_factura como num_guia)
                    insert_sql = f"""INSERT INTO ventas (fecha_venta, producto_codigo, cliente, num_factura, volumen_m3, certificacion, user_id) 
VALUES ('{fecha_venta.isoformat()}', '{producto_info['codigo']}', 'MASISA', '{guia_flete}', {volumen_final}, '{CERTIFICACION_DEFAULT}', '{user_id}');"""

                    insert_statements.append(insert_sql)

                    # Log del registro procesado
                    record = {
                        "fecha_venta": fecha_venta.isoformat(),
                        "producto_codigo": producto_info['codigo'],
                        "producto_nombre": producto_info['nombre'],
                        "cliente": "MASISA",
                        "num_factura": guia_flete,  # num_factura actúa como num_guia
                        "volumen_original": volumen_original,
                        "volumen_final": volumen_final,
                        "factor_conversion": producto_info['factor_conversion'],
                        "certificacion": CERTIFICACION_DEFAULT,
                        "user_id": user_id,
                        "descripcion_material": descripcion_material
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

        print("¡Procesamiento de ventas MASISA completado!")

        # DEBUG: Mostrar los primeros INSERT statements generados
        print("🔍 DEBUG - PRIMEROS INSERT STATEMENTS GENERADOS:")
        for i, stmt in enumerate(insert_statements[:3]):
            print(f"📝 Statement {i+1}: {stmt}")
        print(
            f"📊 Total de INSERT statements generados: {len(insert_statements)}")

        return {
            "success": True,
            "records_processed": total_records,
            "sheets_processed": processed_sheets,
            "total_sheets": len(xf),
            "errors": errors,
            "insert_statements": insert_statements,
            "message": f"¡Procesamiento de ventas MASISA completado! {total_records} registros procesados de {processed_sheets} hojas."
        }

    except Exception as e:
        error_msg = f"Error en el procesamiento de ventas MASISA: {str(e)}"
        print(f"❌ {error_msg}")
        errors.append(error_msg)

        return {
            "success": False,
            "error": error_msg,
            "records_processed": total_records,
            "errors": errors,
            "insert_statements": insert_statements
        }
