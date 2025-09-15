import re
import uuid
import requests
import os
import json
import google.generativeai as genai

from . import crud, models, schemas
from .database import SessionLocal


# Configuración de la API de IA (se lee de las variables de entorno)
if os.getenv("GEMINI_API_KEY"):
    try:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    except Exception as e:
        print(f"ADVERTENCIA: No se pudo configurar la API de Gemini. Error: {e}")
else:
    print("ADVERTENCIA: La variable de entorno GEMINI_API_KEY no está configurada. La IA no funcionará.")


def parse_address_with_ai(address: str) -> dict | None:
    """
    Usa un modelo de IA (Gemini) para parsear una dirección compleja en un formato estructurado,
    siguiendo reglas y ejemplos específicos.
    """
    if not genai.get_model("models/gemini-1.5-flash-latest"): 
        print("Error: El modelo de IA no está disponible. Verifica la configuración de la API Key.")
        return None

    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    # "Super-prompt" v4, con reglas jerárquicas.
    prompt = f""" 
    Eres un asistente experto en la limpieza y estructuración de direcciones de Colombia.
    Tu tarea es analizar la siguiente dirección en bruto y devolver un objeto JSON con los campos especificados.

    **Reglas Clave:**
    1.  **Regla de Jerarquía de Vías:**
        a. Primero, si encuentras "Avenida" (o "Av.") junto a "Carrera" o "Calle", **ignora "Avenida" por completo**.
        b. De los tipos de vía restantes (Carrera, Calle, Diagonal, etc.), el **primero que aparece** es el principal.
        c. Cualquier otro tipo de vía que aparezca **después** del principal se considera un error y debe ser ignorado al construir el `street_info`.
    2.  **Extracción de Componentes:**
        -   `street_info`: La parte principal y geocodificable, siguiendo la regla de jerarquía. Debe tener un formato estándar (Ej: "Carrera 44B # 13-16").
        -   `neighborhood`: El barrio, sector, o urbanización.
        -   `apartment_info`: Detalles como piso, apartamento, interior, torre, etc.
        -   `notes`: Cualquier otra información no esencial: colores, puntos de referencia, instrucciones, etc.
    3.  **Formato de Salida:** La respuesta debe ser **únicamente el objeto JSON**, sin explicaciones. Los campos no encontrados deben ser `null`.

    **Ejemplos:**

    Dirección Bruta: "Cra72a#113-21 2do piso"
    JSON:
    {{
      "street_info": "Carrera 72a # 113-21",
      "neighborhood": null,
      "apartment_info": "2do piso",
      "notes": null
    }}

    Dirección Bruta: "Av. Calle 108 A # 77 B-06 Primer piso"
    JSON:
    {{
      "street_info": "Calle 108 A # 77 B-06",
      "neighborhood": null,
      "apartment_info": "Primer piso",
      "notes": null
    }}

    Dirección Bruta: "Carrera 30 CC calle 100 B-7 la aldea santo domingo Medellín"
    JSON:
    {{
      "street_info": "Carrera 30 CC # 100 B-7",
      "neighborhood": "la aldea santo domingo Medellín",
      "apartment_info": null,
      "notes": null
    }}

    Dirección Bruta: "av. carrera 44B calle 13-16"
    JSON:
    {{
      "street_info": "Carrera 44B # 13-16",
      "neighborhood": null,
      "apartment_info": null,
      "notes": null
    }}

    ---

    **Analiza esta dirección:**

    Dirección Bruta: "{address}"

    JSON:
    """

    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(cleaned_response)
        return parsed_json
    except Exception as e:
        print(f"Error al parsear la dirección con IA: {e}")
        return None


def geocode_address(address: str) -> dict | None:
    # (Esta función no necesita cambios)
    if not address:
        return None
    url = "https://nominatim.openstreetmap.org/search"
    params = {'q': address, 'format': 'json', 'addressdetails': 1, 'limit': 1}
    headers = {'User-Agent': 'GeoFullApp/0.1 (mailto:tu-email-aqui@example.com)'}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data:
            print(f"Geocodificación no encontró resultados para: {address}")
            return None
        result = data[0]
        return {
            "latitude": float(result.get("lat")),
            "longitude": float(result.get("lon")),
            "suggested_address": result.get("display_name"),
            "postal_code": result.get("address", {}).get("postcode")
        }
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión al geocodificar: {e}")
        return None


def run_processing_pipeline(address_id: uuid.UUID):
    """
    Pipeline mejorado que usa el nuevo prompt de IA.
    """
    print(f"[AI PIPELINE v2] Iniciando para address_id: {address_id}")
    db = SessionLocal()
    try:
        db_address = crud.get_address(db, address_id=address_id)
        if not db_address:
            print(f"[AI PIPELINE v2] ERROR: No se encontró la dirección {address_id}")
            return

        # --- 1. Parseo con IA (versión mejorada) ---
        parsed_data = parse_address_with_ai(db_address.original_address)
        
        if parsed_data:
            # Construir la dirección normalizada para el geocodificador
            norm_parts = [
                parsed_data.get('street_info'), 
                parsed_data.get('neighborhood'), 
                "Medellin", 
                "Colombia"
            ]
            normalized_str = ", ".join(filter(None, norm_parts))

            update_data = schemas.AddressUpdate(
                street_info=parsed_data.get('street_info'),
                neighborhood=parsed_data.get('neighborhood'),
                apartment_info=parsed_data.get('apartment_info'),
                notes=parsed_data.get('notes'),
                normalized_address=normalized_str,
                status=models.AddressStatus.NORMALIZED
            )
            crud.update_address(db, address_id=address_id, address_update=update_data)
            print(f"[AI PIPELINE v2] Dirección {address_id} parseada con IA.")
            db.refresh(db_address)
        else:
            print(f"[AI PIPELINE v2] Fallo en el parseo con IA para la dirección {address_id}. No se hacen cambios.")
            return # Si la IA falla, detenemos el proceso para esta dirección

        # --- 2. Geocodificación ---
        address_to_geocode = db_address.normalized_address
        geocoded_data = geocode_address(address_to_geocode)
        
        if geocoded_data:
            update_geo = schemas.AddressUpdate(
                latitude=geocoded_data["latitude"],
                longitude=geocoded_data["longitude"],
                suggested_address=geocoded_data["suggested_address"],
                postal_code=geocoded_data["postal_code"],
                status=models.AddressStatus.VERIFIED
            )
            crud.update_address(db, address_id=address_id, address_update=update_geo)
            print(f"[AI PIPELINE v2] Dirección {address_id} geocodificada.")
        else:
            print(f"[AI PIPELINE v2] Fallo en geocodificación para la dirección {address_id}.")

    finally:
        db.close()
        print(f"[AI PIPELINE v2] Finalizado para address_id: {address_id}")
