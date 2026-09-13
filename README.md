HappyRobot TMS Middleware & Integration Layer

Middleware asíncrono de alto rendimiento desarrollado con FastAPI y Docker diseñado para cerrar la brecha entre agentes de IA modernos (REST/JSON) y un sistema heredado de gestión de transporte (TMS) que opera sobre sockets TCP crudos con protocolos delimitados por pipes (|), complementado con validación de transportistas en tiempo real mediante la API oficial de FMCSA.

Arquitectura del Sistema
[ Agente de IA / Swagger UI ]
              │ (HTTP / JSON)
              ▼
    [ FastAPI Middleware ]
     ├── /verify-carrier ──────► [ FMCSA REST API ] (Validación de MC Number)
     └── /loads/* ─────────────► [ Legacy TMS TCP Server ] (Sockets crudos ASCII)

     
Tecnologías Utilizadas
Lenguaje: Python 3.10+
Framework Web: FastAPI & Uvicorn
Validación de Datos: Pydantic
Networking Asíncrono: asyncio (para streams TCP crudos) y httpx (para llamadas REST externas)
Contenerización: Docker & Docker Compose
Plataforma de Despliegue: Render / Railway

Ejecución Local
Con Docker Compose (Recomendado)
Bash
docker compose up --build
Manualmente con Python
Bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn Protocolo_de_conexion_TCP:app --host 0.0.0.0 --port 8000 --reload
