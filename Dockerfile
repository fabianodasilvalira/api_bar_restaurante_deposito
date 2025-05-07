# Dockerfile para a API FastAPI

# Usar uma imagem base oficial do Python
FROM python:3.11-slim

# Definir o diretório de trabalho no contêiner
WORKDIR /app

# Copiar o arquivo de dependências primeiro para aproveitar o cache do Docker
COPY ./requirements.txt /app/requirements.txt

# Instalar as dependências
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código da aplicação para o contêiner
COPY . /app

# Expor a porta que a aplicação FastAPI usará (configurada no Uvicorn)
EXPOSE 8000

# Comando para rodar a aplicação usando Uvicorn
# O host 0.0.0.0 é importante para que a aplicação seja acessível de fora do contêiner
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

