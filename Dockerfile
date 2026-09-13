FROM python:3.11-slim

WORKDIR /app

# Copiar requerimientos e instalarlos
# Esto ayuda a que Docker cachee este paso y no reinstale todo si solo cambias tu código
COPY requirements.txt .

# Instalar las dependencias sin guardar archivos temporales para mantener la imagen pequeña
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Exponer el puerto donde correrá FastAPI
EXPOSE 8000

# Comando para iniciar el servidor
CMD ["uvicorn", "Protocolo_de_conexion_TCP:app", "--host", "0.0.0.0", "--port", "8000"]