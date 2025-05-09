# Instruções para a API do Restaurante/Bar

## 1. Visão Geral

Esta API foi desenvolvida em FastAPI para gerenciar pedidos, mesas, clientes, pagamentos e crediário (fiado) para um restaurante ou bar. Ela inclui autenticação OAuth2 com JWT para usuários internos, geração de QR Code para acesso à comanda digital pelos clientes, e relatórios de fiado.

## 2. Estrutura do Projeto

O código fonte está organizado da seguinte forma no arquivo `restaurant_api.zip`:

- `/app`: Contém o núcleo da aplicação FastAPI.
    - `main.py`: Ponto de entrada da API, define os endpoints.
    - `models.py`: Define os modelos de dados SQLAlchemy (tabelas do banco).
    - `schemas.py`: Define os schemas Pydantic para validação de dados e serialização.
    - `crud.py`: Contém as funções de Create, Read, Update, Delete para interagir com o banco de dados.
    - `auth.py`: Lógica de autenticação (OAuth2, JWT, hashing de senhas).
    - `database.py`: Configuração da conexão com o banco de dados SQLAlchemy.
    - `config.py`: Configurações da aplicação (chaves secretas, URL do banco, etc.).
- `requirements.txt`: Lista das dependências Python do projeto.

## 3. Pré-requisitos

- Python 3.9+
- PostgreSQL (serviço rodando)
- Redis (serviço rodando)

## 4. Configuração do Ambiente

### 4.1. Banco de Dados PostgreSQL

1.  Certifique-se de que o PostgreSQL está instalado e o serviço está em execução.
2.  Crie um banco de dados e um usuário para a API. Os comandos a seguir podem ser usados (ajuste conforme necessário):
    ```sql
    sudo -u postgres psql
    CREATE DATABASE restaurant_db;
    CREATE USER restaurant_user WITH PASSWORD 'securepassword';
    GRANT ALL PRIVILEGES ON DATABASE restaurant_db TO restaurant_user;
    ALTER USER restaurant_user CREATEDB; -- Opcional, mas pode ser útil
    \q
    ```
3.  A string de conexão com o banco de dados está definida em `app/config.py` (`DATABASE_URL`). Por padrão, é `postgresql://restaurant_user:securepassword@localhost/restaurant_db`. Ajuste se suas credenciais ou host forem diferentes.

### 4.2. Redis

1.  Certifique-se de que o Redis está instalado e o serviço está em execução.
    ```bash
    sudo systemctl status redis-server
    ```
    Se não estiver rodando, inicie-o:
    ```bash
    sudo systemctl start redis-server
    ```

### 4.3. Dependências Python

1.  Descompacte o arquivo `restaurant_api.zip`.
2.  Navegue até o diretório raiz do projeto (`restaurant_api`).
3.  Crie um ambiente virtual (recomendado):
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
4.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

## 5. Executando a API

Dentro do diretório `restaurant_api` (com o ambiente virtual ativado), execute o seguinte comando:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- `--reload`: Faz o servidor reiniciar automaticamente após alterações no código (útil para desenvolvimento).
- `--host 0.0.0.0`: Permite que a API seja acessível de fora do localhost.
- `--port 8000`: Define a porta em que a API será executada.

A API estará acessível em `http://localhost:8000` (ou o IP da sua máquina na porta 8000).
A documentação interativa da API (Swagger UI) estará disponível em `http://localhost:8000/docs`.

## 6. Funcionalidades Principais e Endpoints

Consulte a documentação interativa (`/docs`) para uma lista completa de endpoints, seus parâmetros e respostas esperadas. Alguns dos principais fluxos incluem:

- **Autenticação:**
    - `POST /auth/token`: Login para usuários internos (garçons, gerentes) para obter um token JWT.
    - `POST /auth/users/`: Criar um novo usuário interno.
    - `GET /auth/users/me`: Obter dados do usuário logado.
- **Mesas:**
    - `POST /mesas/`: Criar uma nova mesa.
    - `POST /mesas/{mesa_id}/abrir`: Abrir uma mesa e criar uma comanda.
    - `GET /mesas/{mesa_id}/qrcode`: Gerar a imagem do QR Code para a mesa.
- **Comanda Digital (Pública):**
    - `GET /comanda-digital/{qr_code_hash}`: Acessar a comanda digital escaneando o QR Code.
- **Produtos, Pedidos, Clientes, Pagamentos, Fiado:** Endpoints CRUD para gerenciar essas entidades.
- **Relatórios:**
    - `GET /relatorios/fiado/semanal`: Relatório semanal de fiados.
    - `GET /relatorios/fiado/mensal`: Relatório mensal de fiados.
    - `GET /relatorios/fiado/?data_inicio=YYYY-MM-DD&data_fim=YYYY-MM-DD`: Relatório de fiados por período customizado.

## 7. Considerações Adicionais

- **Segurança da Chave Secreta:** A `SECRET_KEY` em `app/config.py` deve ser alterada para um valor forte e único e, idealmente, gerenciada através de variáveis de ambiente em um ambiente de produção.
- **Impressão de Comanda:** O endpoint `/comandas/{id_comanda}/imprimir` (conforme planejado) não foi explicitamente implementado no código fornecido até o momento da compactação, mas a estrutura permite sua adição. A ideia seria gerar um HTML ou PDF simples.
- **Autenticação de Cliente (QR Code):** A autenticação para clientes realizarem ações (como fazer pedidos diretamente pela página do QR Code) não foi definida pelo usuário e, portanto, a página do QR Code é primariamente para visualização. A adição de pedidos pelo cliente via QR Code exigiria uma definição de como o cliente se autentica ou se identifica.

Lembre-se de que este é um ponto de partida. Para um ambiente de produção, considere práticas adicionais de segurança, logging, monitoramento e deployment (ex: usando Docker, Gunicorn, Nginx, etc.).

