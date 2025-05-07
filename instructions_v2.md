# Instruções para a API do Restaurante/Bar (Versão 2)

Esta documentação detalha como configurar, executar e utilizar a API FastAPI desenvolvida para o seu restaurante/bar. Esta versão inclui Docker, Docker Compose, Alembic para migrações de banco de dados, autenticação OAuth2 com JWT, integração com Redis para funcionalidades em tempo real, geração de QR Code para mesas, e gerenciamento completo de comandas, pedidos, pagamentos e fiado.

## Pré-requisitos

Antes de começar, garanta que você tenha os seguintes softwares instalados em sua máquina:

1.  **Docker:** Para executar a aplicação em contêineres. (Instruções: [https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/))
2.  **Docker Compose:** Para orquestrar os contêineres da aplicação, banco de dados e Redis. (Geralmente vem com o Docker Desktop. Instruções: [https://docs.docker.com/compose/install/](https://docs.docker.com/compose/install/))

## Estrutura do Projeto

O código fonte está organizado da seguinte forma dentro da pasta `restaurant_api`:

```
restaurant_api/
├── alembic/                  # Configurações e scripts de migração do Alembic
│   ├── versions/             # Arquivos de versão de migração gerados
│   ├── env.py                # Script de configuração do Alembic
│   └── script.py.mako        # Template para novos scripts de migração
├── app/                      # Código principal da aplicação FastAPI
│   ├── api/
│   │   ├── deps.py           # Dependências da API (ex: get_db, get_current_user)
│   │   └── v1/
│   │       ├── endpoints/    # Módulos dos endpoints (auth, produtos, mesas, etc.)
│   │       └── router.py     # Roteador principal da API v1
│   ├── core/
│   │   ├── config.py         # Configurações da aplicação (variáveis de ambiente)
│   │   └── security.py       # Funções de segurança (hash de senha, JWT)
│   ├── crud/                 # Operações CRUD para cada modelo (Create, Read, Update, Delete)
│   ├── db/
│   │   ├── base_class.py     # Classe base para os modelos SQLAlchemy (com ID, datas)
│   │   ├── models/           # Definições dos modelos SQLAlchemy (tabelas do banco)
│   │   └── session.py        # Configuração da sessão do SQLAlchemy e engine
│   ├── schemas/              # Modelos Pydantic para validação de dados e serialização
│   ├── services/             # Lógica de negócio mais complexa (ex: Redis, Pedidos)
│   └── main.py               # Ponto de entrada da aplicação FastAPI
├── .env                      # Arquivo para variáveis de ambiente (NÃO versionar com dados sensíveis)
├── .gitignore                # Arquivos e pastas a serem ignorados pelo Git
├── alembic.ini               # Configuração principal do Alembic
├── Dockerfile                # Instruções para construir a imagem Docker da API
├── docker-compose.yml        # Orquestração dos serviços (API, PostgreSQL, Redis)
├── requirements.txt          # Dependências Python do projeto
└── README.md                 # Este arquivo (ou um similar)
```

## Configuração Inicial

1.  **Clonar o Repositório (se aplicável) ou Extrair os Arquivos:**
    Certifique-se de que todos os arquivos fornecidos estejam na pasta `restaurant_api`.

2.  **Configurar Variáveis de Ambiente:**
    *   Crie um arquivo chamado `.env` na raiz do projeto (`restaurant_api/.env`).
    *   Copie o conteúdo do arquivo `.env.example` (se fornecido) ou adicione as seguintes variáveis, ajustando os valores conforme necessário:

    ```env
    PROJECT_NAME="API Restaurante"
    PROJECT_VERSION="2.0.0"

    # Configurações do PostgreSQL (usadas pelo Docker Compose e pela API)
    POSTGRES_SERVER=db_restaurant # Nome do serviço do banco no docker-compose.yml
    POSTGRES_USER=admin_restaurante
    POSTGRES_PASSWORD=senha_super_secreta
    POSTGRES_DB=restaurante_db
    DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_SERVER}:5432/${POSTGRES_DB}"

    # Configurações do Redis (usadas pelo Docker Compose e pela API)
    REDIS_HOST=redis_restaurant # Nome do serviço do Redis no docker-compose.yml
    REDIS_PORT=6379

    # Configurações de Segurança (OAuth2 com JWT)
    SECRET_KEY="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7" # Gere uma chave secreta forte e única!
    ALGORITHM="HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES=30

    # CORS Origins (separados por vírgula, sem espaços ao redor da vírgula)
    # Ex: BACKEND_CORS_ORIGINS=http://localhost,http://localhost:3000,https://seufrontend.com
    BACKEND_CORS_ORIGINS=*

    # Informações do Superusuário Inicial (para criação via script ou manual)
    FIRST_SUPERUSER_EMAIL=admin@example.com
    FIRST_SUPERUSER_PASSWORD=admin123
    ```
    **Importante:** Substitua `senha_super_secreta` e `SECRET_KEY` por valores seguros e únicos.

## Executando a Aplicação com Docker Compose

1.  **Navegue até a Raiz do Projeto:**
    Abra um terminal e navegue até a pasta `restaurant_api`.

2.  **Construir e Iniciar os Contêineres:**
    Execute o seguinte comando:
    ```bash
    docker-compose up --build -d
    ```
    *   `--build`: Força a reconstrução das imagens se houver alterações (ex: no Dockerfile).
    *   `-d`: Executa os contêineres em segundo plano (detached mode).

    Este comando irá:
    *   Construir a imagem Docker para a API FastAPI (se ainda não existir ou se `--build` for usado).
    *   Baixar as imagens oficiais do PostgreSQL e Redis.
    *   Iniciar os três contêineres: `api_restaurant`, `db_restaurant`, `redis_restaurant`.
    *   Configurar as redes e volumes conforme definido no `docker-compose.yml`.

3.  **Aplicar Migrações do Banco de Dados (Alembic):**
    Após os contêineres estarem em execução, especialmente o `db_restaurant`, você precisa aplicar as migrações para criar as tabelas no banco de dados.
    Execute o seguinte comando para entrar no contêiner da API e rodar o Alembic:
    ```bash
    docker-compose exec api_restaurant alembic upgrade head
    ```
    Isso aplicará todas as migrações pendentes que estão na pasta `alembic/versions`.

4.  **Criar Superusuário Inicial (Opcional, mas recomendado):**
    A aplicação está configurada para permitir a criação de um superusuário inicial. Você pode criar um script para isso ou fazer manualmente através da API após ela estar no ar (se houver um endpoint de criação de usuário inicial sem autenticação, o que não é o caso aqui por segurança). 
    Uma forma de fazer isso é executar um script Python dentro do contêiner da API. Um script `initial_data.py` pode ser criado na pasta `app/` e executado com:
    ```bash
    docker-compose exec api_restaurant python app/initial_data.py 
    ```
    (Este script `initial_data.py` precisaria ser criado por você, importando o `crud.usuario.create` e as configurações.)
    Alternativamente, após a API estar no ar, você pode criar o primeiro usuário (que será superuser se for o primeiro e as regras de criação permitirem) através de um cliente de API como Postman ou Insomnia, chamando o endpoint de criação de usuário (se ele não exigir autenticação para o primeiro superuser, o que não é o padrão aqui). A forma mais segura é um script de inicialização.

    Para este projeto, o superusuário pode ser criado ao registrar o primeiro usuário através do endpoint `/api/v1/auth/register` (se a lógica de `deps.py` ou `crud_usuario` for ajustada para permitir o primeiro como superuser, ou se você criar um endpoint específico para isso).
    Por enquanto, o primeiro usuário criado via `/api/v1/auth/register` será um usuário normal. Para ter um superusuário, você precisaria:
    a. Criar um usuário normal.
    b. Acessar o banco de dados diretamente (via `docker-compose exec db_restaurant psql -U seu_user -d sua_db`) e definir o campo `is_superuser` para `true` para esse usuário.

## Acessando a API

*   **API:** `http://localhost:8000` (ou a porta que você mapeou no `docker-compose.yml`)
*   **Documentação Interativa (Swagger UI):** `http://localhost:8000/docs`
*   **Documentação Alternativa (ReDoc):** `http://localhost:8000/redoc`

## Endpoints Principais

A documentação interativa (`/docs`) fornecerá a lista completa de endpoints, seus parâmetros e respostas. Alguns exemplos:

*   **Autenticação:**
    *   `POST /api/v1/auth/register`: Registrar novo usuário (garçom/gerente).
    *   `POST /api/v1/auth/login`: Obter token de acesso.
    *   `GET /api/v1/auth/me`: Obter informações do usuário logado.
*   **Produtos:** CRUD em `/api/v1/produtos/`
*   **Clientes:** CRUD em `/api/v1/clientes/`
*   **Mesas:**
    *   CRUD em `/api/v1/mesas/`
    *   `POST /api/v1/mesas/{mesa_id}/abrir`: Abrir mesa e criar comanda.
    *   `POST /api/v1/mesas/{mesa_id}/fechar`: Fechar mesa.
    *   `GET /api/v1/mesas/{mesa_id}/qrcode`: Obter imagem QR Code da mesa.
*   **Comandas:**
    *   `GET /api/v1/comandas/`: Listar comandas (com filtros).
    *   `GET /api/v1/comandas/{comanda_id}`: Detalhes da comanda.
    *   `POST /api/v1/comandas/{comanda_id}/solicitar-fechamento`: Mudar status para fechamento.
    *   `GET /api/v1/comandas/digital/{qr_code_hash}`: Acesso público à comanda digital via QR Code.
*   **Pedidos:**
    *   `POST /api/v1/pedidos/`: Criar novo pedido (com itens) para uma comanda.
    *   `PUT /api/v1/pedidos/{pedido_id}/status`: Atualizar status geral do pedido.
    *   `PUT /api/v1/pedidos/itens/{item_pedido_id}/status`: Atualizar status de um item específico.
*   **Pagamentos:**
    *   `POST /api/v1/pagamentos/`: Registrar pagamento para uma comanda.
*   **Fiado:**
    *   `POST /api/v1/fiado/`: Registrar um novo valor em fiado.
    *   `PUT /api/v1/fiado/{fiado_id}/pagar`: Registrar pagamento de um fiado existente.
*   **Relatórios:**
    *   `GET /api/v1/relatorios/fiado?data_inicio=YYYY-MM-DD&data_fim=YYYY-MM-DD`: Relatório de fiados.

## Migrações com Alembic

*   **Para criar uma nova migração (após alterar modelos SQLAlchemy em `app/db/models/`):**
    ```bash
    docker-compose exec api_restaurant alembic revision -m "nome_descritivo_da_migracao"
    ```
    Edite o arquivo gerado em `alembic/versions/` para definir as operações `upgrade` e `downgrade`.

*   **Para aplicar migrações:**
    ```bash
    docker-compose exec api_restaurant alembic upgrade head
    ```

*   **Para reverter a última migração:**
    ```bash
    docker-compose exec api_restaurant alembic downgrade -1
    ```

## Integração com Redis

O Redis é utilizado para funcionalidades em tempo real, como:
*   Notificar o frontend sobre atualizações no status de pedidos.
*   Notificar a cozinha/bar sobre novos pedidos ou itens.
*   Atualizar o status de mesas e comandas em tempo real.

A API publicará mensagens em canais Redis específicos quando eventos relevantes ocorrerem. O frontend (ou outros serviços) deverá se inscrever nesses canais para receber as atualizações.

Exemplos de canais (a serem definidos e implementados no frontend):
*   `pedidos_novos`: Notificação de novos pedidos.
*   `pedidos_status_updates`: Atualizações de status de pedidos ou itens.
*   `mesa_{mesa_id}_status`: Atualizações de status de uma mesa específica.
*   `comanda_{comanda_id}_updates`: Atualizações gerais de uma comanda (itens, valores, status).
*   `cozinha_pedidos`: Canal para a interface da cozinha/bar receber novos pedidos/itens.

O formato das mensagens será JSON. A estrutura exata de cada mensagem dependerá do evento.

## Parando a Aplicação

Para parar os contêineres:
```bash
docker-compose down
```
Se você quiser remover os volumes (e perder os dados do banco de dados e Redis, a menos que configurados para persistência externa):
```bash
docker-compose down -v
```

## Desenvolvimento

*   Para desenvolvimento, você pode montar o código da aplicação no contêiner para que as alterações sejam refletidas automaticamente (o `uvicorn` está configurado com `--reload` no `Dockerfile` e o `docker-compose.yml` monta o volume `.:/app`).
*   Lembre-se de reconstruir a imagem se alterar dependências em `requirements.txt` ou o `Dockerfile`.

## Considerações Finais

*   **Segurança:** Certifique-se de que a `SECRET_KEY` e as senhas do banco de dados sejam fortes e mantidas em segredo. Não versione o arquivo `.env` com dados sensíveis em repositórios públicos.
*   **Backup:** Implemente uma estratégia de backup para o banco de dados PostgreSQL.
*   **Frontend:** Esta API é o backend. Você precisará de um frontend (web ou mobile) para interagir com ela.

Se precisar de mais alguma informação ou ajuste, por favor, me avise!

