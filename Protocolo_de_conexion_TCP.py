#Creado por: Andres Arturo Olvera Cano
#Fecha 11/09/2026 
# Version 1.0
# Funcionalidad: Middleware para conectar con TMS vía TCP y exponer endpoints REST para HappyRobot para entregar cargas, verificar MC Number y bookear cargas.
import asyncio
import os
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

load_dotenv()

app = FastAPI(title="HappyRobot TMS Middleware")

# --- CONFIGURACIÓN DEL ENTORNO ---
TMS_HOST = os.getenv("TMS_HOST", "tramway.proxy.rlwy.net").strip()
TMS_PORT = int(os.getenv("TMS_PORT", "17159"))
TMS_TOKEN = os.getenv("TMS_TOKEN").strip()
FMCSA_API_KEY = os.getenv("FMCSA_API_KEY").strip()
FMCSA_BASE_URL = os.getenv("FMCSA_BASE_URL", "https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number").strip()

# --- MODELOS PYDANTIC ---
class FMCSAVerificationResponse(BaseModel):
    mc_number: str
    is_authorized: bool
    details: Optional[Dict[str, Any]] = None

class BookRequest(BaseModel):
    mc_number: str = Field(..., description="MC Number verificado del Carrier")
    rate: float = Field(..., description="Tarifa final acordada")#Tarifa acordada para la carga
    outcome: str = Field(..., description="Resultado de la llamada (ej. Booked, Failed Negotiation)")
    notes: Optional[str] = Field(None, description="Notas adicionales")

# --- FUNCIONES TCP CORE ---

async def send_tms_request(command: str, retries: int = 2, **kwargs) -> List[Dict[str, Any]]:
    # 1. Ensamblado del payload
    request_parts = [f"CMD:{command}", f"AUTH:{TMS_TOKEN}"]
    for key, value in kwargs.items():
        if value is not None:
            # Agregamos .upper() para que envíe ATLANTA y DALLAS
            clean_value = str(value).replace("|", "").replace("\r\n", "").upper()
            request_parts.append(f"{key.upper()}:{clean_value}")
            
    request_str = "|".join(request_parts) + "\r\n"
    payload_bytes = request_str.encode('ascii')
    
    if len(payload_bytes) > 4096:
        raise ValueError("La petición supera el límite de 4096 bytes del protocolo.")

    # --- DEBUG: Ver exactamente qué vamos a enviar al TMS ---
    print(f"--- DEBUG TMS PAYLOAD ---: {repr(request_str)}", flush=True)
    
    # 2. Conexión y envío
    for attempt in range(retries + 1):
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(TMS_HOST, TMS_PORT), timeout=5.0
            )
            
            writer.write(payload_bytes)
            await writer.drain()
            
            response_data = ""
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=10.0)
                if not line:
                    break
                    
                decoded_line = line.decode('ascii')
                response_data += decoded_line
                
                if decoded_line == "END\r\n" or decoded_line.startswith("ERR|"):
                    break
            
            writer.close()
            await writer.wait_closed()
            
            # --- DEBUG: Ver la respuesta como tabla ---
            print("\n--- DEBUG TMS RESPUESTA (TABLA) ---", flush=True)
            
            lineas = [linea for linea in response_data.split('\r\n') if linea and linea != "END"]
            
            if lineas:
                encabezados = [campo.split(':')[0].strip() for campo in lineas[0].split('|') if ':' in campo]
                print(" | ".join(f"{h:<15}" for h in encabezados), flush=True)
                print("-" * (18 * len(encabezados)), flush=True)
                
                for linea in lineas:
                    valores = [campo.split(':', 1)[1].strip() for campo in linea.split('|') if ':' in campo]
                    print(" | ".join(f"{v:<15}" for v in valores), flush=True)
            else:
                 print("No se encontraron resultados o solo se recibió END.", flush=True)
                 
            print("-" * 50 + "\n", flush=True)
            
            return parse_tms_response(response_data)
            
        except (asyncio.TimeoutError, ConnectionError) as e:
            if attempt == retries:
                raise HTTPException(status_code=503, detail="TMS inestable tras múltiples intentos.")
            await asyncio.sleep(1)

def parse_tms_response(data: str) -> List[Dict[str, Any]]:
    # Usar split('\r\n') directamente sin .strip() general para no perder saltos de línea vitales
    lines = [line for line in data.split('\r\n') if line]
    
    if not lines:
        return []
        
    # Parseo de error más robusto para evitar IndexError
    if lines[0].startswith("ERR|"):
        parts = lines[0].split('|')
        err_code = parts[1].replace("CODE:", "") if len(parts) > 1 else "UNKNOWN"
        err_msg = parts[2].replace("MSG:", "") if len(parts) > 2 else "Error desconocido"
        raise HTTPException(status_code=400, detail=f"TMS Error {err_code}: {err_msg.strip()}")

    results = []
    for line in lines:
        if line == "END":
            continue
            
        item = {}
        for part in line.split('|'):
            if ':' in part:
                k, v = part.split(':', 1)
                # Uso rstrip() en el valor para eliminar solo el relleno a la derecha
                item[k.strip().lower()] = v.rstrip() 
                
        if item:
            results.append(item)
            
    return results

# --- ENDPOINTS PARA FMCSA ---

@app.get("/verify-carrier/{mc_number}", response_model=FMCSAVerificationResponse)#Datos de Carrier OK
async def verify_carrier(mc_number: str):
    async with httpx.AsyncClient() as client:
        try:
            # Pasa la API key como Query Parameter webKey
            url = f"{FMCSA_BASE_URL}/{mc_number}"
            params = {"webKey": FMCSA_API_KEY}
            
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            
            data = response.json()
            content = data.get("content", [])

            # Si 'content' está vacío, el MC number no existe
            if not content:
                return {
                    "mc_number": mc_number,
                    "is_authorized": False,
                    "details": {"error": "No encontrado"}
                }

            # Extrae la información de carrier y valida 'allowedToOperate'
            carrier_info = content[0].get("carrier", {})
            is_authorized = carrier_info.get("allowedToOperate") == "Y"

            return {
                "mc_number": mc_number,
                "is_authorized": is_authorized,
                "details": carrier_info
            }

        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Error FMCSA: {str(exc)}")

# --- ENDPOINTS PARA TMS ---
@app.get("/loads", response_model=Dict[str, Any])#Datos de carga OK
async def search_loads(
    origin: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    equipment_type: Optional[str] = Query(None)
):
    # 1. Inicializar el diccionario vacío para controlar el orden de inserción
    params = {}
    
    # 2. Primero Origen (como en Transcript 1)
    if origin:
        if len(origin.strip()) == 2:
            params["orig_state"] = origin.strip()
        else:
            params["orig_city"] = origin.strip()
            
    # 3. Luego Destino
    if destination:
        if len(destination.strip()) == 2:
            params["dest_state"] = destination.strip()
        else:
            params["dest_city"] = destination.strip()
            
    # 4. Después Tipo de Equipo
    if equipment_type:
        params["eqtype"] = equipment_type
        
    # 5. (Opcional pero recomendado) Agregar MAX_RESULTS como en la documentación
    # Esto también puede ayudar a que el servidor responda mucho más rápido
    params["max_results"] = 5

    valid_params = {k: v for k, v in params.items() if v is not None}
    data = await send_tms_request("LOAD_QUERY", **valid_params)
    return {"status": "success", "data": data}

@app.get("/loads/{load_id}", response_model=Dict[str, Any])#Datos de carga OK
async def get_load_details(load_id: str):
    data = await send_tms_request("LOAD_GET", LOAD_ID=load_id)
    if not data:
        raise HTTPException(status_code=404, detail="Carga no encontrada")
    return {"status": "success", "data": data[0]}

@app.post("/loads/{load_id}/book")
async def book_load(load_id: str, payload: BookRequest):
    data = await send_tms_request(
        "LOAD_BOOK",
        LOAD_ID=load_id,
        MC_NUM=payload.mc_number,      
        AGREED_RATE=int(payload.rate)  #Tarifa final acordada, convertida a entero para cumplir con el protocolo TCP
    )
    return {"status": "success", "data": data[0] if data else {}}

