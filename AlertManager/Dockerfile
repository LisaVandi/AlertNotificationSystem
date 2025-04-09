# Usa un'immagine base di Alpine con Python
FROM python:3.13-alpine

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file di requirements
COPY requirements.txt .

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto del codice dell'applicazione
COPY . .

# Espone la porta su cui l'applicazione sarà in ascolto
EXPOSE 5000

# Comando per avviare l'applicazione
CMD ["python", "app/__init__.py"]
