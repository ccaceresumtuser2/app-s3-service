# app-s3-service

Servicio REST construido con FastAPI para administrar buckets y objetos de Amazon S3. La arquitectura separa las rutas HTTP, los casos de uso, el acceso a S3 y los modelos de entrada y salida.

## Estructura

```text
app/
  api/routes.py                 Rutas HTTP y documentacion de operaciones
  repositories/s3_repository.py Acceso a boto3 y Amazon S3
  schemas/s3.py                 Modelos de request y response
  services/s3_service.py        Casos de uso
main.py                         Configuracion FastAPI y manejo de errores
s3_operations.py                Cliente S3 y configuracion de region
requirements.txt                Dependencias del servicio
```

## Requisitos

- Python 3.10 o superior.
- Una cuenta AWS con permisos para las operaciones S3 que se vayan a utilizar.
- Credenciales validas en el perfil AWS `default`. En AWS Academy, usa las credenciales temporales vigentes del laboratorio.

El cliente reutiliza el perfil `default` y la region `us-east-1` configurados en `s3_operations.py`. No guardes claves AWS en el repositorio.

## Instalacion en Windows PowerShell

1. Abre PowerShell en la carpeta del proyecto.
2. Crea un entorno virtual:

   ```powershell
   py -3 -m venv .venv
   ```

3. Activa el entorno:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

4. Instala las dependencias:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Configura las credenciales temporales siguiendo [Configurar las credenciales del Laboratorio 3.1](#configurar-las-credenciales-del-laboratorio-31).

### Configurar las credenciales del Laboratorio 3.1

1. Inicia el Laboratorio 3.1 en AWS Academy y copia los valores vigentes de `AWS Details`: `aws_access_key_id`, `aws_secret_access_key` y `aws_session_token`.
2. En PowerShell, configura el perfil `default` con el Access Key ID y el Secret Access Key:

   ```powershell
   aws configure --profile default
   ```

   Cuando solicite la region, escribe `us-east-1`. El cliente de este proyecto usa esa region en `s3_operations.py`.

3. Abre el archivo de credenciales de Windows:

   ```powershell
   notepad $env:USERPROFILE\.aws\credentials
   ```

   En la sección `[default]`, agrega el token temporal que copiaste:

   ```ini
   aws_session_token = PEGAR_AQUI_EL_TOKEN_TEMPORAL
   ```

   El perfil debe contener los tres valores bajo `[default]`. Este archivo está fuera del repositorio; no pegues credenciales en el código ni en archivos versionados.

4. Comprueba que el perfil funciona:

   ```powershell
   aws sts get-caller-identity --profile default
   ```

   Si el laboratorio se reinicia o las credenciales expiran, repite estos pasos con valores nuevos.

## Ejecutar

Desde la carpeta del proyecto y con el entorno virtual activo:

```powershell
python -m uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```

La API queda disponible en `http://localhost:8090`. Para detenerla, usa `Ctrl+C` en la terminal.

## Swagger y comprobacion

- Swagger UI: `http://localhost:8090/docs`
- ReDoc: `http://localhost:8090/redoc`
- Estado del servicio: `http://localhost:8090/healthz`
- Conexion con AWS: `http://localhost:8090/health/aws`

Desde Swagger puedes probar los endpoints y subir archivos usando el formulario multipart. Para validar que la API responde, ejecuta:

```powershell
Invoke-RestMethod http://localhost:8090/healthz
```

Para verificar las credenciales y conectividad con AWS mediante STS:

```powershell
Invoke-RestMethod http://localhost:8090/health/aws
```

Todas las respuestas JSON exitosas usan el formato `success`, `message`, `data` y `errors`. La información propia de cada operación se encuentra dentro de `data`.

Una respuesta `200` de `/health/aws` incluye `data.connected: true`, `data.account_id`, `data.region` y `data.arn`. El campo `arn` muestra la identidad AWS asociada al perfil `default`; para un usuario IAM normalmente empieza por `arn:aws:iam`. Si las credenciales corresponden a un rol asumido, el ARN puede empezar por `arn:aws:sts`.

Ejemplo de respuesta:

```json
{
   "success": true,
   "message": "Conexión con AWS verificada.",
   "data": {
      "connected": true,
      "account_id": "123456789012",
      "arn": "arn:aws:iam::123456789012:user/nombre-usuario",
      "region": "us-east-1",
      "message": null
   },
   "errors": []
}
```

Las respuestas de error también tienen el mismo sobre; `data` será `null` y `errors` contendrá código, mensaje y, cuando aplique, el campo inválido.

## Endpoints

| Metodo | Ruta | Funcion |
| --- | --- | --- |
| `GET` | `/healthz` | Estado del servicio |
| `GET` | `/health/aws` | Verificar conexión y credenciales AWS mediante STS |
| `GET` | `/buckets` | Listar buckets |
| `POST` | `/buckets` | Crear bucket con JSON `{"name":"nombre-base"}`; agrega `-DD-MM-YYYY`; responde `409` si el nombre generado ya existe |
| `DELETE` | `/buckets/{bucket}` | Eliminar bucket vacio |
| `PUT` | `/buckets/{bucket}/policy` | Aplicar la politica JSON enviada en el atributo `policies` |
| `DELETE` | `/buckets/{bucket}/policy` | Eliminar la politica del bucket |
| `GET` | `/buckets/{bucket}/objects` | Listar objetos; acepta `?prefix=carpeta/` |
| `DELETE` | `/buckets/{bucket}/objects?confirm=true` | Eliminar todos los objetos y versiones del bucket |
| `PUT` | `/buckets/{bucket}/objects/{key}` | Subir archivo multipart en el campo `file` |
| `GET` | `/buckets/{bucket}/objects/{key}` | Guardar en `C:/download/<bucket>/<object-key>` y descargar como archivo adjunto |
| `DELETE` | `/buckets/{bucket}/objects/{key}` | Eliminar objeto |

Los errores de AWS se devuelven como respuestas HTTP: por ejemplo, `404` para bucket u objeto inexistente, `403` para acceso denegado y `409` si el bucket no se puede eliminar por estar ocupado.

Para vaciar un bucket usa `DELETE /buckets/{bucket}/objects?confirm=true`. La confirmacion es obligatoria porque el borrado es irreversible. La respuesta incluye `deleted_count` y cualquier error por objeto. En buckets versionados tambien elimina versiones anteriores y delete markers; el perfil AWS necesita `s3:GetBucketVersioning`, `s3:ListBucket`, `s3:ListBucketVersions`, `s3:DeleteObject` y `s3:DeleteObjectVersion`.

La ruta `PUT /buckets/{bucket}/policy` recibe el documento de politica dentro del atributo `policies`; no requiere seleccionar un archivo. Aplicar una politica reemplaza la politica actual; revisa cuidadosamente sus permisos antes de enviarla. El endpoint `DELETE` elimina la politica existente.

Ejemplo de body:

```json
{
   "policies": {
      "Version": "2012-10-17",
      "Statement": [
         {
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
            "Action": ["s3:GetBucketVersioning", "s3:ListBucket", "s3:ListBucketVersions"],
            "Resource": "arn:aws:s3:::mi-bucket"
         },
         {
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
            "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"],
            "Resource": "arn:aws:s3:::mi-bucket/*"
         }
      ]
   }
}
```

La API no implementa autenticacion propia. No la expongas a redes no confiables sin agregar autenticacion y controles de acceso.

Las respuestas JSON de los endpoints siguen el mismo formato. Las descargas de objetos son la excepción: conservan el cuerpo binario y las cabeceras necesarias para que el archivo no se corrompa.

## Referencia tecnica de endpoints

La URL base local es `http://localhost:8090`. Los parametros entre llaves son segmentos de ruta; `key` admite subrutas separadas por `/`. Los requests JSON usan `Content-Type: application/json`, y la subida de archivos usa `multipart/form-data`.

El flujo normal es: FastAPI recibe la solicitud y valida los datos con los schemas Pydantic; `app/api/routes.py` invoca el caso de uso de `app/services/s3_service.py`; el servicio delega las operaciones AWS a `app/repositories/s3_repository.py`, que usa los clientes de `s3_operations.py`. Las operaciones JSON exitosas devuelven:

```json
{
  "success": true,
  "message": "Operacion completada.",
  "data": {},
  "errors": []
}
```

`data` contiene el resultado especifico de la operacion. Las respuestas de error usan `success: false`, `data: null` y una lista `errors` con `code`, `message` y, en errores de validacion, `field`.

### Salud y conectividad

| Metodo y ruta | Entrada | Ejecucion y respuesta |
| --- | --- | --- |
| `GET /healthz` | Sin parametros. | Comprueba que el proceso responde. Devuelve `200` y `data.status: "ok"`; no consulta AWS. |
| `GET /health/aws` | Sin parametros. | Llama a AWS STS `GetCallerIdentity` con el perfil configurado. Devuelve `200` con `connected`, `account_id`, `arn` y `region`. Un fallo de credenciales o conectividad devuelve `503`. |

### Buckets

| Metodo y ruta | Entrada | Ejecucion y respuesta |
| --- | --- | --- |
| `GET /buckets` | Sin parametros. | Lista los buckets visibles para las credenciales y devuelve `name` y `creation_date` ISO 8601 por bucket. |
| `POST /buckets` | JSON `{"name":"nombre-base"}`. `name` debe tener entre 3 y 52 caracteres. | Construye el nombre final como `<name>-DD-MM-YYYY`, usando la fecha local del proceso; verifica si ya aparece en la lista de buckets y luego lo crea. Devuelve `201` con `name` y `created: true`; si el nombre generado ya existe, devuelve `409`. |
| `DELETE /buckets/{bucket}` | Nombre del bucket en la ruta. | Solicita a S3 eliminar el bucket. Devuelve `200` con `name` y `deleted: true`. S3 solo permite eliminar buckets vacios; un bucket no vacio se informa como `409`. |

### Politicas de bucket

| Metodo y ruta | Entrada | Ejecucion y respuesta |
| --- | --- | --- |
| `PUT /buckets/{bucket}/policy` | JSON con la politica dentro de `policies`, por ejemplo `{"policies":{"Version":"2012-10-17","Statement":[]}}`. | Serializa el objeto `policies` como JSON y llama a `PutBucketPolicy`. Si se acepta, devuelve `200` con `bucket` y `applied: true`. La politica nueva reemplaza la politica existente. |
| `DELETE /buckets/{bucket}/policy` | Nombre del bucket en la ruta. | Llama a `DeleteBucketPolicy`. Si se acepta, devuelve `200` con `bucket` y `deleted: true`. |

### Objetos

| Metodo y ruta | Entrada | Ejecucion y respuesta |
| --- | --- | --- |
| `GET /buckets/{bucket}/objects` | Parametro query opcional `prefix`; por ejemplo `?prefix=carpeta/`. | Usa el paginador `list_objects_v2` y devuelve `key`, `size` en bytes y `last_modified` ISO 8601 para cada objeto coincidente. |
| `PUT /buckets/{bucket}/objects/{key}` | Cuerpo `multipart/form-data` con el campo `file`. `key` puede incluir subcarpetas. | Transfiere el archivo a S3 con la key solicitada. Devuelve `201` con `bucket`, `key` y `uploaded: true`. El archivo recibido se cierra al terminar, incluso si la operacion falla. |
| `GET /buckets/{bucket}/objects/{key}` | Bucket y key en la ruta. | Obtiene el objeto desde S3, lo escribe en bloques de 1 MiB en `C:/download/<bucket>/<key>` y entrega el mismo archivo como respuesta binaria. Incluye `Content-Disposition` para la descarga y `X-Saved-To` con la ruta local. Los segmentos invalidos para Windows se sustituyen para formar la ruta local. |
| `DELETE /buckets/{bucket}/objects/{key}` | Bucket y key en la ruta. | Llama a `DeleteObject` para esa key. Devuelve `200` con `bucket`, `key` y `deleted: true` si S3 acepta la solicitud. |
| `DELETE /buckets/{bucket}/objects` | Query obligatorio `confirm=true`; por defecto `confirm=false`. | Sin confirmacion responde `400` y no inicia el borrado. Con confirmacion, pagina los objetos y elimina lotes de hasta 1.000. Si el versionado esta habilitado o suspendido, tambien elimina todas las versiones y delete markers. Devuelve `200` con `deleted_count` y `errors`; revisa `errors` para detectar fallos parciales por objeto. |

### Errores y permisos AWS

Los datos invalidos o faltantes se rechazan con `422`. Los errores AWS se traducen a respuestas HTTP: bucket u objeto inexistente, `404`; acceso denegado, `403`; bucket existente, no vacio o conflicto de nombre, `409`; argumentos o politica invalidos, `400`; otros errores de AWS, `502`. Los errores inesperados devuelven `500` sin exponer detalles internos.

El perfil AWS `default` debe tener permisos para la operacion solicitada. Entre las acciones usadas estan `sts:GetCallerIdentity`, las acciones de listado/creacion/eliminacion de buckets y las acciones `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` y de politicas. Para vaciar buckets versionados se necesitan ademas `s3:GetBucketVersioning`, `s3:ListBucketVersions` y `s3:DeleteObjectVersion`. La API no agrega autenticacion propia; no la expongas a redes no confiables.

### Ejemplos de request y response

Los siguientes ejemplos usan `curl.exe` desde PowerShell contra `http://localhost:8090`. Los nombres de bucket, cuenta, fechas, rutas y metadatos de los ejemplos son ilustrativos; las respuestas dependen de los recursos reales y de las credenciales AWS.

#### `GET /healthz`

Request:

```powershell
curl.exe -i http://localhost:8090/healthz
```

Response (`200 OK`):

```json
{
  "success": true,
  "message": "Servicio disponible.",
  "data": {"status": "ok"},
  "errors": []
}
```

#### `GET /health/aws`

Request:

```powershell
curl.exe -i http://localhost:8090/health/aws
```

Response (`200 OK`):

```json
{
  "success": true,
  "message": "Conexión con AWS verificada.",
  "data": {
    "connected": true,
    "account_id": "123456789012",
    "arn": "arn:aws:iam::123456789012:user/lab-user",
    "region": "us-east-1",
    "message": null
  },
  "errors": []
}
```

#### `GET /buckets`

Request:

```powershell
curl.exe -i http://localhost:8090/buckets
```

Response (`200 OK`):

```json
{
  "success": true,
  "message": "Buckets listados.",
  "data": [
    {"name": "documentos-lab", "creation_date": "2026-09-20T12:30:15+00:00"}
  ],
  "errors": []
}
```

#### `POST /buckets`

Request:

```powershell
curl.exe -i -X POST http://localhost:8090/buckets `
  -H "Content-Type: application/json" `
  -d '{"name":"documentos-lab"}'
```

Response (`201 Created`):

```json
{
  "success": true,
  "message": "Bucket creado.",
  "data": {"name": "documentos-lab-03-10-2026", "created": true},
  "errors": []
}
```

#### `DELETE /buckets/{bucket}`

Request:

```powershell
curl.exe -i -X DELETE http://localhost:8090/buckets/documentos-lab-03-10-2026
```

Response (`200 OK`):

```json
{
  "success": true,
  "message": "Bucket eliminado.",
  "data": {"name": "documentos-lab-03-10-2026", "deleted": true},
  "errors": []
}
```

#### `PUT /buckets/{bucket}/policy`

Este ejemplo aplica una politica que permite a la cuenta indicada listar el bucket. `PutBucketPolicy` reemplaza la politica actual; adapta la cuenta y los permisos con cuidado.

Request:

```powershell
curl.exe -i -X PUT http://localhost:8090/buckets/documentos-lab/policy `
  -H "Content-Type: application/json" `
  -d '{"policies":{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789012:root"},"Action":"s3:ListBucket","Resource":"arn:aws:s3:::documentos-lab"}]}}'
```

Response (`200 OK`):

```json
{
  "success": true,
  "message": "Política del bucket aplicada.",
  "data": {"bucket": "documentos-lab", "applied": true},
  "errors": []
}
```

#### `DELETE /buckets/{bucket}/policy`

Request:

```powershell
curl.exe -i -X DELETE http://localhost:8090/buckets/documentos-lab/policy
```

Response (`200 OK`):

```json
{
  "success": true,
  "message": "Política del bucket eliminada.",
  "data": {"bucket": "documentos-lab", "deleted": true},
  "errors": []
}
```

#### `GET /buckets/{bucket}/objects`

Request (lista objetos cuyo key empieza con `reportes/`):

```powershell
curl.exe -i "http://localhost:8090/buckets/documentos-lab/objects?prefix=reportes/"
```

Response (`200 OK`):

```json
{
  "success": true,
  "message": "Objetos listados.",
  "data": [
    {
      "key": "reportes/resumen.pdf",
      "size": 2048,
      "last_modified": "2026-10-02T18:42:10+00:00"
    }
  ],
  "errors": []
}
```

#### `PUT /buckets/{bucket}/objects/{key}`

Request (cambia la ruta local por el archivo que quieras subir):

```powershell
curl.exe -i -X PUT "http://localhost:8090/buckets/documentos-lab/objects/reportes/resumen.pdf" `
  -F "file=@C:\archivos\resumen.pdf"
```

Response (`201 Created`):

```json
{
  "success": true,
  "message": "Objeto subido.",
  "data": {
    "bucket": "documentos-lab",
    "key": "reportes/resumen.pdf",
    "uploaded": true
  },
  "errors": []
}
```

#### `GET /buckets/{bucket}/objects/{key}`

Request:

```powershell
curl.exe -i -OJ "http://localhost:8090/buckets/documentos-lab/objects/reportes/resumen.pdf"
```

Response (`200 OK`): el cuerpo es el contenido binario del archivo, no un documento JSON. La API tambien guarda una copia en `C:/download/documentos-lab/reportes/resumen.pdf`. Las cabeceras incluyen, por ejemplo:

```http
Content-Disposition: attachment; filename="resumen.pdf"
Content-Type: application/pdf
X-Saved-To: C:/download/documentos-lab/reportes/resumen.pdf
```

#### `DELETE /buckets/{bucket}/objects/{key}`

Request:

```powershell
curl.exe -i -X DELETE "http://localhost:8090/buckets/documentos-lab/objects/reportes/resumen.pdf"
```

Response (`200 OK`):

```json
{
  "success": true,
  "message": "Objeto eliminado.",
  "data": {
    "bucket": "documentos-lab",
    "key": "reportes/resumen.pdf",
    "deleted": true
  },
  "errors": []
}
```

#### `DELETE /buckets/{bucket}/objects?confirm=true`

Request:

```powershell
curl.exe -i -X DELETE "http://localhost:8090/buckets/documentos-lab/objects?confirm=true"
```

Response (`200 OK`; `errors` puede contener fallos parciales devueltos por S3):

```json
{
  "success": true,
  "message": "Operación de borrado masivo completada.",
  "data": {
    "bucket": "documentos-lab",
    "deleted_count": 2,
    "errors": []
  },
  "errors": []
}
```

## Historias de usuario y criterios de aceptación

### HU-01: Comprobar el estado y la conexión con AWS

Como operador, quiero verificar que la API está activa y que las credenciales AWS funcionan para diagnosticar el servicio.

- Dado que la API está iniciada, cuando consulto `GET /healthz`, entonces recibo `200` con `success: true` y `data.status: "ok"`.
- Dadas credenciales AWS válidas, cuando consulto `GET /health/aws`, entonces recibo `200` con `data.connected: true`, cuenta, ARN y región.
- Dadas credenciales inválidas o vencidas, cuando consulto `/health/aws`, entonces recibo un error HTTP con el formato común `success: false`, `data: null` y detalle en `errors`.

### HU-02: Administrar buckets

Como operador, quiero consultar, crear y eliminar buckets para organizar el almacenamiento del laboratorio.

- Cuando consulto `GET /buckets`, entonces recibo la lista de buckets accesibles dentro de `data`.
- Cuando envío `POST /buckets` con un nombre base válido, entonces se crea un bucket con sufijo `-DD-MM-YYYY` y la respuesta indica su nombre final.
- Cuando el nombre generado ya existe, entonces la API responde `409` con el sobre de error estándar.
- Cuando solicito eliminar un bucket no vacío, entonces AWS rechaza la operación y la API informa el error sin presentarlo como éxito.

### HU-03: Administrar políticas de bucket

Como operador, quiero aplicar o quitar una política JSON para controlar las acciones permitidas sobre un bucket.

- Cuando envío `PUT /buckets/{bucket}/policy` con el objeto de política dentro de `policies`, entonces la API aplica ese documento al bucket.
- Cuando falta el atributo `policies` o no contiene un objeto JSON, entonces la API responde `422` con el formato de error estándar.
- Cuando envío `DELETE /buckets/{bucket}/policy`, entonces la política del bucket se elimina.
- Cuando AWS rechaza la política, entonces la respuesta indica el error y no confirma una aplicación exitosa.

### HU-04: Administrar objetos

Como operador, quiero listar, subir, descargar y eliminar objetos para gestionar archivos en S3.

- Cuando consulto `GET /buckets/{bucket}/objects`, entonces recibo los objetos del bucket y puedo filtrar con `prefix`.
- Cuando envío un archivo multipart a `PUT /buckets/{bucket}/objects/{key}`, entonces el objeto se sube con la key indicada.
- Cuando solicito `GET /buckets/{bucket}/objects/{key}`, entonces recibo el archivo como descarga y se guarda una copia en `C:/download/<bucket>/<key>`.
- Cuando solicito `DELETE /buckets/{bucket}/objects/{key}`, entonces se elimina ese objeto y la respuesta confirma la key afectada.

### HU-05: Vaciar un bucket

Como operador, quiero eliminar todos los objetos de un bucket para dejarlo vacío antes de retirarlo o reutilizarlo.

- Cuando solicito `DELETE /buckets/{bucket}/objects` sin `confirm=true`, entonces la API responde `400` y no inicia el borrado.
- Cuando confirmo con `?confirm=true`, entonces la API procesa todas las páginas y elimina los objetos en lotes de hasta 1.000.
- Cuando el bucket tiene versionado, entonces también se procesan las versiones anteriores y los delete markers.
- Al terminar, la respuesta incluye `deleted_count` y una lista `errors` con los elementos que AWS no pudo eliminar.

### HU-06: Mantener respuestas consistentes

Como consumidor de la API, quiero interpretar una misma estructura JSON en todos los endpoints para manejar resultados y errores de manera uniforme.

- Dada una operación JSON exitosa, entonces la respuesta contiene `success`, `message`, `data` y `errors`.
- Dada una validación o una operación AWS fallida, entonces la respuesta contiene `success: false`, `data: null` y detalles en `errors`.
- Al descargar un objeto, entonces se conserva el cuerpo binario y las cabeceras de descarga en vez de envolver el archivo en JSON.

## Sprint backlog

| Sprint | Objetivo | Trabajo incluido |
| --- | --- | --- |
| Sprint 1 | Conectividad y buckets | HU-01: health checks de API/AWS; HU-02: listar, crear con fecha y eliminar buckets; documentar credenciales del Lab 3.1. |
| Sprint 2 | Políticas y objetos | HU-03: aplicar/eliminar políticas mediante JSON; HU-04: listar, subir, descargar a `C:/download` y eliminar objetos. |
| Sprint 3 | Borrado masivo y contrato API | HU-05: vaciado confirmado, paginado y compatible con versionado; HU-06: sobre JSON uniforme, errores, Swagger y documentación. |

## Diagramas de arquitectura

El archivo [arquitectura/arquitectura_s3.drawio](arquitectura/arquitectura_s3.drawio) contiene dos páginas editables en diagrams.net: **Componentes** muestra `main.py`, rutas, schemas Pydantic, servicios, repositorio y `s3_operations.py`; **Despliegue** representa la ejecución local actual en Windows, el puerto `8090`, las credenciales AWS, la carpeta `C:/download` y las conexiones HTTPS a S3/STS.