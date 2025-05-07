import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Adicionar o diretório raiz do projeto ao sys.path
# para que o Alembic possa encontrar os módulos da aplicação.
# Supondo que alembic.ini está na raiz do projeto e app/ está no mesmo nível.
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "app"))

# Importar a Base dos modelos da aplicação e os próprios modelos
# A estrutura exata de importação dependerá de como você organiza seus modelos.
# Exemplo, se Base está em app.db.base_class e modelos em app.db.models:
from db.base_class import Base # Ajuste este import conforme sua estrutura final
# Importe todos os seus modelos aqui para que o Alembic os detecte para autogenerate
from db.models import usuario, mesa, produto, cliente, comanda, pedido, item_pedido, pagamento, fiado # Ajuste estes imports

# Importar as configurações da aplicação para obter a DATABASE_URL
from core.config import settings # Ajuste este import

# Esta é a configuração do Alembic, que fornece acesso aos valores
# dentro do arquivo .ini em uso.
config = context.config

# Interpretar o arquivo de configuração para logging do Python.
# Esta linha basicamente configura os loggers apenas uma vez.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Adicionar aqui o objeto MetaData do seu modelo para suporte a "autogenerate"
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata # Usando a Base importada

# Outras opções podem ser configuradas aqui, como:
# name, schema, etc. Para mais informações consulte:
# https://alembic.sqlalchemy.org/en/latest/autogenerate.html

def get_url():
    return settings.DATABASE_URL

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # url = config.get_main_option("sqlalchemy.url") # Comentado para usar a URL da app
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # configuration = config.get_section(config.config_ini_section, {})
    # configuration["sqlalchemy.url"] = get_url()
    # connectable = engine_from_config(
    #     configuration,
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    # )

    # Usar a URL diretamente da configuração da aplicação
    connectable_config = config.get_section(config.config_ini_section, {})
    connectable_config["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        connectable_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )


    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

