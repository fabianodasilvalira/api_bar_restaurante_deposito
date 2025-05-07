from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy import Column, Integer, DateTime, func
import uuid
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # Renomeado para evitar conflito

@as_declarative()
class Base:
    """
    Base class which provides automated table name
    and surrogate primary key column.
    """

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s" # Ex: Usuario -> usuarios

    # Se quiser um id inteiro autoincrementável como PK padrão:
    # id = Column(Integer, primary_key=True, index=True)
    # Mas vamos usar UUID como padrão para a maioria dos modelos, conforme planejado.
    # Este id pode ser sobrescrito nos modelos específicos se necessário.
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), onupdate=func.now())

