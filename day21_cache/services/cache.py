import hashlib
import json
from typing import Any, Dict, Optional
from services.redis_client import get_redis

class PromptCache:
    """字串精確匹配的 Prompt Cache（Key 用 SHA256），內容以 JSON 存。"""

    @staticmethod
    def _key(prompt: str) -> str:
        h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return f"prompt_cache:{h}"

    async def get(self, prompt: str) -> Optional[Dict[str, Any]]:
        r = get_redis()
        raw = await r.get(self._key(prompt))
        return json.loads(raw) if raw else None

    async def set(self, prompt: str, value: Dict[str, Any], ttl: int = 3600) -> None:
        r = get_redis()
        await r.set(self._key(prompt), json.dumps(value, ensure_ascii=False), ex=ttl)
