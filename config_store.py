from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_CATEGORIES = {
    "canais": True,
    "cargos": True,
    "permissoes": True,
    "membros": True,
    "moderacao": True,
    "servidor": True,
}


def default_config() -> dict[str, Any]:
    return {
        "log_channel_id": None,
        "admin_role_id": None,
        "categories": DEFAULT_CATEGORIES.copy(),
    }


class ConfigStore:
    """Armazena configurações separadas por servidor."""

    def __init__(self, path: str | Path = "data/config.json"):
        self.path = Path(path)
        self._lock = asyncio.Lock()
        self._configs: dict[str, dict[str, Any]] = {}

    async def load(self) -> None:
        async with self._lock:
            if not self.path.exists():
                self._configs = {}
                return

            raw = await asyncio.to_thread(
                self.path.read_text,
                encoding="utf-8",
            )

            data = json.loads(raw)

            if not isinstance(data, dict):
                raise ValueError("Configuração inválida.")

            self._configs = data

    async def get(self, guild_id: int) -> dict[str, Any]:
        async with self._lock:
            stored = self._configs.get(str(guild_id), {})
            config = default_config()
            config.update(stored)

            categories = DEFAULT_CATEGORIES.copy()
            categories.update(stored.get("categories", {}))
            config["categories"] = categories

            return config

    async def update(
        self,
        guild_id: int,
        **changes: Any,
    ) -> dict[str, Any]:
        async with self._lock:
            key = str(guild_id)

            config = default_config()
            stored = self._configs.get(key, {})
            config.update(stored)

            categories = DEFAULT_CATEGORIES.copy()
            categories.update(stored.get("categories", {}))

            new_categories = changes.pop("categories", {})
            categories.update(new_categories)

            config.update(changes)
            config["categories"] = categories

            self._configs[key] = config

            await self._save()

            return config.copy()

    async def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        temporary = self.path.with_suffix(".tmp")

        content = json.dumps(
            self._configs,
            ensure_ascii=False,
            indent=2,
        )

        await asyncio.to_thread(
            temporary.write_text,
            content,
            encoding="utf-8",
        )

        await asyncio.to_thread(
            os.replace,
            temporary,
            self.path,
        )
