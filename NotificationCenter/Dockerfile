# specifica l'immagine di base da cui partire. 
FROM python:3.13-alpine

# imposta la directory di lavoro all'interno del container. 
WORKDIR /app

# copia i file dalla  macchina locale al container.
COPY requirements.txt .

# esegue comandi all'interno del container durante il processo di build. 
RUN pip install -r requirements.txt

# indica quale porta sarà esposta dal container, cioè la porta sulla quale il container ascolterà le connessioni in ingresso.
EXPOSE 5000

# specifica il comando che viene eseguito quando il container viene avviato
CMD ["python", "messaging/__init__.py"]