# 🚛 HappyRobot TMS Middleware & Integration Layer

> **High-Performance Async Integration Engine**  
> Middleware asíncrono diseñado para cerrar la brecha entre agentes de IA modernos (`REST/JSON`) y sistemas legados de gestión de transporte (`TMS`) basados en sockets TCP crudos con payloads delimitados por pipes (`|`), incorporando validación de transportistas en tiempo real vía FMCSA.

---

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![AsyncIO](https://img.shields.io/badge/AsyncIO-Native-FF6F00)
![Deploy](https://img.shields.io/badge/Deploy-Render%20%7C%20Railway-informational)

---

## 🏛 Arquitectura del Sistema

```text
┌───────────────────────────┐
│   Agente IA / Swagger UI  │
└─────────────┬─────────────┘
              │ HTTP / JSON
              ▼
┌───────────────────────────┐
│    FastAPI Middleware     │
└──────┬─────────────┬──────┘
       │             │
       │ (REST)      │ (Raw TCP / ASCII Pipe-delimited)
       ▼             ▼
┌─────────────┐ ┌───────────────────────────┐
│  FMCSA API  │ │   Legacy TMS TCP Server   │
└─────────────┘ └───────────────────────────┘

```

🛠 Stack Tecnológico
Core Runtime: Python 3.10+
API Framework: FastAPI & Uvicorn (ASGI)
Data Validation: Pydantic v2

🚀 Asynchronous Networking:
asyncio para gestión de streams crudos vía sockets TCP
httpx para consumo asíncrono de APIs externas (FMCSA)
Infraestructura & Despliegue: Docker, Docker Compose, Render / Railway

🚀 Puesta en Marcha
Opción 1: Docker Compose (Recomendado)
Construye y levanta el middleware junto con sus dependencias en un solo comando:
docker compose up --build
Opción 2: Entorno Local (Python)
Crear y activar el entorno virtual:
# En Linux / macOS:
python -m venv venv
source venv/bin/activate

# En Windows:
python -m venv venv
.\venv\Scripts\activate
Instalar dependencias:
pip install -r requirements.txt
Iniciar el servidor:
uvicorn Protocolo_de_conexion_TCP:app --host 0.0.0.0 --port 8000 --reload

## 📍 Endpoints Principales

| Método | Ruta | Descripción | Protocolo Destino |
| :--- | :--- | :--- | :--- |
| `POST` | `/verify-carrier` | Valida el estatus del MC Number con la API de FMCSA | HTTPS / JSON |
| `POST` | `/loads/*` | Consulta y actualización de cargas en el TMS legado | TCP Socket crudo (`\|`) |
