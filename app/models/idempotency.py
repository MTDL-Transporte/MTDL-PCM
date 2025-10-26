"""
Modelo para controle de idempotência de requisições mutáveis
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base

class IdempotencyRecord(Base):
    """Armazena a resposta de uma operação mutável para uma chave de idempotência.
    Identificação: (key, method, path, body_hash)
    """
    __tablename__ = "idempotency_records"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(200), index=True, nullable=False)
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    body_hash = Column(String(64), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())