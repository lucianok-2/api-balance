# Python API Flask - Procesador de Funciones

Esta API Flask maneja la ejecución de funciones Python personalizadas para procesar diferentes tipos de archivos Excel.

## 🚀 Instalación y Configuración

### 1. Instalar Dependencias

```bash
cd python-api
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

Copia el archivo `.env.example` a `.env` y configura tus variables:

```bash
cp .env.example .env
```

Edita el archivo `.env` con tus credenciales de Supabase:

```env
NEXT_PUBLIC_SUPABASE_URL=https://tu-proyecto.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=tu_anon_key_aqui
FLASK_ENV=development
FLASK_DEBUG=True
```

### 3. Ejecutar la API

```bash
python app.py
```

La API estará disponible en `http://localhost:5000`

## 📋 Endpoints Disponibles

### Health Check
- **GET** `/health`
- Verifica que la API esté funcionando

### Ejecutar Función
- **POST** `/execute-function`
- Parámetros:
  - `functionId`: ID de la función a ejecutar
  - `userId`: ID del usuario
  - `file`: Archivo Excel a procesar

### Listar Funciones
- **GET** `/functions?userId=USER_ID`
- Lista todas las funciones disponibles para un usuario

## 🔧 Funciones Implementadas

### Función ID 1: Procesador de Reportes de Ingreso
- **Archivo**: `functions/process_ingresos.py`
- **Propósito**: Procesa archivos Excel de reportes de ingreso de planta
- **Columnas requeridas**:
  - NOMBRE PROVEEDOR
  - ROL
  - Descripción de material código FSC
  - M3 o m3st
- **Tabla destino**: `recepciones`

### Función ID 2: Procesador de Ventas
- **Archivo**: `functions/process_ventas.py`
- **Propósito**: Procesa archivos Excel de reportes de ventas
- **Columnas requeridas**:
  - FECHA
  - CLIENTE
  - PRODUCTO
  - CANTIDAD
  - PRECIO_UNITARIO
- **Tabla destino**: `ventas`

### Función ID 3: Procesador de Inventario
- **Archivo**: `functions/process_inventario.py`
- **Propósito**: Procesa archivos Excel de inventario y stock
- **Columnas requeridas**:
  - PRODUCTO_CODIGO
  - DESCRIPCION
  - STOCK_ACTUAL
  - STOCK_MINIMO
  - UBICACION
- **Tabla destino**: `inventario`

## 🎯 Agregar Nuevas Funciones

Para agregar una nueva función:

1. **Crear archivo Python** en `functions/nueva_funcion.py`
2. **Implementar función** `process_file(file, supabase)`
3. **Agregar mapeo** en `app.py` en el diccionario `function_files`
4. **Crear registro** en la tabla `user_functions` de Supabase

### Ejemplo de nueva función:

```python
# functions/nueva_funcion.py
def process_file(file, supabase):
    try:
        # Tu lógica de procesamiento aquí
        return {
            "success": True,
            "records_processed": 100,
            "message": "Procesamiento completado"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

## 🔒 Seguridad

- La API usa CORS para permitir requests desde el frontend
- Los archivos temporales se eliminan automáticamente
- Se registra el historial de procesamiento en la base de datos
- Manejo robusto de errores con logs detallados

## 📊 Monitoreo

La API registra automáticamente:
- Estado de procesamiento en `document_processing_history`
- Logs detallados en la consola
- Errores y excepciones con stack traces

## 🚨 Solución de Problemas

### Error: "Variables de entorno no encontradas"
- Verifica que el archivo `.env` esté configurado correctamente
- Asegúrate de que `NEXT_PUBLIC_SUPABASE_URL` y `NEXT_PUBLIC_SUPABASE_ANON_KEY` estén definidas

### Error: "Función no encontrada"
- Verifica que el `function_id` exista en la tabla `user_functions`
- Confirma que el archivo Python correspondiente esté en `functions/`

### Error: "Columnas faltantes"
- Revisa que el archivo Excel tenga las columnas requeridas
- Verifica que los nombres de las columnas coincidan exactamente