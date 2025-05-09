from asyncio.log import logger

import redis.asyncio as redis
from typing import Optional, AsyncIterator
from app.core.config import settings


class RedisService:
    def __init__(self):
        self._client = None
        self._pubsub = None
        self.connected = False

    async def connect(self) -> bool:
        """Estabelece conexão com o Redis"""
        if self.connected:
            return True

        try:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )

            # Test connection
            await self._client.ping()
            self.connected = True
            logger.info(f"Conexão Redis estabelecida em {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            return True

        except Exception as e:
            logger.error(f"Falha na conexão Redis: {str(e)}")
            self._client = None
            self.connected = False
            return False

    async def disconnect(self):
        """Fecha a conexão com o Redis"""
        if self._client and self.connected:
            try:
                if self._pubsub:
                    await self._pubsub.close()
                await self._client.close()
                logger.info("Conexão Redis encerrada")
            except Exception as e:
                logger.error(f"Erro ao desconectar Redis: {str(e)}")
            finally:
                self._client = None
                self._pubsub = None
                self.connected = False

    async def publish(self, channel: str, message: str) -> bool:
        """
        Publica mensagem em um canal Redis
        Retorna True se bem sucedido, False caso contrário
        """
        if not self.connected and not await self.connect():
            return False

        try:
            await self._client.publish(channel, message)
            logger.debug(f"Mensagem publicada no canal {channel}: {message[:100]}...")
            return True
        except Exception as e:
            logger.error(f"Erro ao publicar no Redis: {str(e)}")
            self.connected = False
            return False

    async def subscribe(self, channel: str) -> bool:
        """
        Inscreve em um canal Redis
        Retorna True se bem sucedido, False caso contrário
        """
        if not self.connected and not await self.connect():
            return False

        try:
            self._pubsub = self._client.pubsub()
            await self._pubsub.subscribe(channel)
            logger.info(f"Inscrito no canal Redis: {channel}")
            return True
        except Exception as e:
            logger.error(f"Erro ao inscrever no Redis: {str(e)}")
            self.connected = False
            return False

    async def listen(self) -> AsyncIterator[Optional[dict]]:
        """
        Gera mensagens recebidas dos canais inscritos
        """
        if not self._pubsub:
            yield None

        try:
            async for message in self._pubsub.listen():
                if message['type'] == 'message':
                    yield message
        except Exception as e:
            logger.error(f"Erro ao escutar Redis: {str(e)}")
            yield None

    async def set_key(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Armazena um valor com TTL opcional"""
        if not self.connected and not await self.connect():
            return False

        try:
            if ttl:
                await self._client.setex(key, ttl, value)
            else:
                await self._client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Erro ao definir chave Redis: {str(e)}")
            self.connected = False
            return False

    async def get_key(self, key: str) -> Optional[str]:
        """Obtém um valor armazenado"""
        if not self.connected and not await self.connect():
            return None

        try:
            return await self._client.get(key)
        except Exception as e:
            logger.error(f"Erro ao obter chave Redis: {str(e)}")
            self.connected = False
            return None

    async def delete_key(self, key: str) -> bool:
        """Remove uma chave"""
        if not self.connected and not await self.connect():
            return False

        try:
            return await self._client.delete(key) > 0
        except Exception as e:
            logger.error(f"Erro ao deletar chave Redis: {str(e)}")
            self.connected = False
            return False


# Instância singleton do serviço
redis_service = RedisService()


# Funções para injeção de dependência
async def get_redis_publisher():
    """Retorna instância para publicação de mensagens"""
    if not redis_service.connected:
        await redis_service.connect()
    return redis_service


async def get_redis_subscriber():
    """Retorna instância para inscrição em canais"""
    if not redis_service.connected:
        await redis_service.connect()
    return redis_service