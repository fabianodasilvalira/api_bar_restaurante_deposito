from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # Renomeado para evitar conflito
import uuid # Import uuid

from app.db.base_class import Base # Garanta que o caminho de importação esteja correto

class Usuario(Base):
    # __tablename__ será "usuarios" por causa da Base

    # id, data_criacao, data_atualizacao são herdados da Base

    nome_completo = Column(String, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    cargo = Column(String, nullable=True)  # Ex: "Garçom", "Gerente", "Caixa"
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False) # Opcional, para controle de acesso mais granular

    # Adicionar relacionamentos se necessário, por exemplo:
    # pedidos_registrados = relationship("Pedido", back_populates="usuario_solicitante")
    # pagamentos_registrados = relationship("Pagamento", back_populates="usuario_registrou")
    # mesas_abertas = relationship("Mesa", back_populates="usuario_responsavel")

