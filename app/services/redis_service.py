# app/services/redis_service.py
import redis.asyncio as redis # Using asyncio version for FastAPI
from app.core.config import settings

class RedisClient:
    def __init__(self, host: str = settings.REDIS_HOST, port: int = settings.REDIS_PORT):
        self.host = host
        self.port = port
        self._client = None

    async def connect(self):
        if not self._client:
            try:
                self._client = await redis.Redis(host=self.host, port=self.port, decode_responses=True)
                # Test connection
                await self._client.ping()
                print(f"Conectado ao Redis em {self.host}:{self.port}")
            except redis.exceptions.ConnectionError as e:
                print(f"Falha ao conectar ao Redis: {e}")
                self._client = None # Ensure client is None if connection failed

    async def disconnect(self):
        if self._client:
            await self._client.close()
            self._client = None
            print("Desconectado do Redis.")

    @property
    async def client(self) -> Optional[redis.Redis]:
        if not self._client:
            await self.connect() # Attempt to connect if not already connected
        return self._client

    async def publish_message(self, channel: str, message: str):
        r = await self.client
        if r:
            await r.publish(channel, message)
            print(f"Mensagem 	\"{message}\" publicada no canal 	\"{channel}\"")
        else:
            print(f"Não foi possível publicar mensagem: cliente Redis não conectado.")

    async def subscribe_to_channel(self, channel: str):
        r = await self.client
        if r:
            pubsub = r.pubsub()
            await pubsub.subscribe(channel)
            print(f"Inscrito no canal 	\"{channel}\"")
            return pubsub
        else:
            print(f"Não foi possível inscrever-se no canal: cliente Redis não conectado.")
            return None

# Instância global para ser usada na aplicação
redis_client = RedisClient()

async def get_redis_client() -> redis.Redis:
    # This dependency can be used in FastAPI endpoints
    # It ensures the client is connected before use.
    client = await redis_client.client
    if not client:
        raise Exception("Não foi possível conectar ao Redis. Verifique os logs e a configuração.")
    return client

# Funções para serem chamadas no startup e shutdown da aplicação FastAPI
async def startup_redis_client():
    await redis_client.connect()

async def shutdown_redis_client():
    await redis_client.disconnect()


