# 📦 Backend de Normalización y Geocodificación de Direcciones

## 1. Objetivo General
Diseñar e implementar un **backend en Python (FastAPI)** que permita:  
1. Recibir direcciones en bruto desde archivos Excel/CSV o API.  
2. Normalizar las direcciones para estandarizarlas.  
3. Consultar servicios externos de geocodificación (ej. Nominatim, Google Maps, Mapbox) para obtener coordenadas y códigos postales.  
4. Almacenar direcciones originales, normalizadas y sugeridas en una base de datos.  
5. Exponer una **API REST documentada (Swagger/OpenAPI)** para integraciones con otras plataformas (ej. n8n, dashboards, apps).  

---

## 2. Alcance de la Versión Inicial (MVP)
- Subida de archivos Excel/CSV.  
- Normalización básica de direcciones con reglas simples (regex, diccionario de abreviaturas).  
- Consulta automática a un servicio de geocodificación (ej. Nominatim como primera opción).  
- Almacenamiento en base de datos con historial de versiones (dirección original, normalizada y sugerida).  
- API pública/documentada para CRUD de direcciones.  
- Exportación de datos procesados en CSV.  

---

## 3. Arquitectura
- **Lenguaje principal**: Python 3.x  
- **Framework API**: FastAPI  
- **Base de datos**: PostgreSQL (persistencia de direcciones y resultados)  
- **Cache**: Redis (opcional, para evitar consultas repetidas a APIs externas)  
- **Contenerización**: Docker + Docker Compose  
- **Infraestructura**: VPS propio (ej. 2 vCPU, 4GB RAM)  

---

## 4. Modelo de Datos (DB PostgreSQL)
### Tabla: `addresses`
| Campo              | Tipo        | Descripción |
|--------------------|------------|-------------|
| `id`               | UUID (PK)  | Identificador único |
| `original_address` | TEXT       | Dirección ingresada por el usuario |
| `normalized_address` | TEXT     | Dirección normalizada por reglas/NLP |
| `suggested_address` | TEXT      | Dirección sugerida por API externa |
| `latitude`         | FLOAT      | Latitud obtenida |
| `longitude`        | FLOAT      | Longitud obtenida |
| `postal_code`      | VARCHAR(10) | Código postal (si aplica) |
| `status`           | ENUM(`pending`,`normalized`,`verified`) | Estado del procesamiento |
| `created_at`       | TIMESTAMP  | Fecha de creación |
| `updated_at`       | TIMESTAMP  | Última actualización |

---

## 5. Endpoints API (FastAPI)
### 📂 Gestión de direcciones
- `POST /upload` → Subir Excel/CSV con direcciones.  
- `POST /addresses` → Insertar una dirección individual (JSON).  
- `GET /addresses` → Listar direcciones (con filtros: estado, barrio, CP).  
- `GET /addresses/{id}` → Obtener detalle de una dirección.  
- `PUT /addresses/{id}` → Actualizar dirección manualmente (ej. corregida).  
- `DELETE /addresses/{id}` → Eliminar dirección.  

### ⚙️ Procesamiento
- `POST /normalize/{id}` → Normalizar una dirección específica.  
- `POST /geocode/{id}` → Consultar API externa para obtener coordenadas y CP.  
- `POST /batch/normalize` → Normalizar en lote.  
- `POST /batch/geocode` → Geocodificar en lote.  

### 📊 Utilidades
- `GET /stats` → Métricas generales (ej. % direcciones normalizadas, con CP, fallidas).  
- `GET /export` → Descargar resultados en CSV/Excel.  

---

## 6. Flujo de Procesamiento
1. **Input**: Excel/CSV o entrada manual → `POST /upload` o `POST /addresses`.  
2. **Normalización**: limpieza de texto, abreviaturas (ej. "Cra" → "Carrera").  
3. **Geocodificación**: consulta a Nominatim o Google Maps → devuelve dirección sugerida + coordenadas + CP.  
4. **Almacenamiento**: guardar original, normalizada y sugerida en DB.  
5. **Corrección manual (opcional)**: vía `PUT /addresses/{id}`.  
6. **Exportación**: descargar CSV con resultados finales.  

---

## 7. Integraciones Externas
- **Nominatim (OpenStreetMap)**: geocodificación gratuita (con límites).  
- **Google Maps API / Mapbox / HERE**: alternativas pagas para mayor confiabilidad.  
- **n8n**: posible integración como cliente de la API en la fase inicial.  

---

## 8. Seguridad y Control
- **Autenticación básica (token o API key)** para acceso al backend.  
- **Rate limiting** para proteger contra abuso de la API.  
- **Logs y monitoreo**: guardar errores de normalización o fallos en consultas externas.  

---

## 9. Roadmap
### Fase 1 – MVP
- Backend en FastAPI + PostgreSQL.  
- Normalización básica + geocodificación con Nominatim.  
- Subida y exportación de Excel/CSV.  
- Documentación Swagger.  

### Fase 2 – Optimización
- Cache con Redis para evitar consultas repetidas.  
- Validación cruzada con múltiples APIs externas.  
- Dashboard simple (puede ser con n8n o interfaz mínima).  

### Fase 3 – Producto Comercial
- Normalización avanzada con NLP/IA.  
- Frontend en Nuxt (dashboard completo).  
- Multiusuario con roles y autenticación.  
- Monetización (API como servicio).  

---
