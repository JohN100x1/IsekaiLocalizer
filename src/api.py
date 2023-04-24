import asyncio
import re
from abc import ABC, abstractmethod
from asyncio import Task
from random import randint
from typing import Self
from uuid import uuid4

import requests
from aiohttp import ClientResponse, ClientSession
from msgspec.json import decode as json_decode
from msgspec.json import encode as json_encode

from models import LocalizationPack, LocalizedString


class TranslatorAPI(ABC):
    @classmethod
    @abstractmethod
    def create(cls) -> Self:
        """Create an instance of the TranslatorAPI"""
        ...

    @abstractmethod
    async def translate(
        self, pack: LocalizationPack, batch_size: int = 16
    ) -> LocalizationPack:
        """Localize the localization pack in batches."""
        ...


class OraAPI(TranslatorAPI):
    system_prompt = (
        "You are ChatGPT, a large language model trained by OpenAI. "
        "Answer only in a json code block."
    )
    description = "ChatGPT Openai Language Model"
    slug = "gpt-3.5"
    model = "gpt-3.5-turbo"

    def __init__(self, chat_id: str, created_by: str, created_at: str):
        self.chat_id = chat_id
        self.createdBy = created_by
        self.createdAt = created_at

    @classmethod
    def create(cls) -> Self:
        response_json = requests.post(
            "https://ora.sh/api/assistant",
            headers={
                "Origin": "https://ora.sh",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; "
                "rv:109.0) Gecko/20100101 Firefox/112.0",
                "Referer": "https://ora.sh/",
                "Host": "ora.sh",
            },
            json={
                "prompt": cls.system_prompt,
                "userId": f"auto:{uuid4()}",
                "name": cls.slug,
                "description": cls.description,
            },
        ).json()
        return cls(
            chat_id=response_json["id"],
            created_by=response_json["createdBy"],
            created_at=response_json["createdAt"],
        )

    def get_translation_tasks(
        self,
        session: ClientSession,
        pack: LocalizationPack,
        batch_size: int = 16,
    ) -> list[Task[ClientResponse]]:
        tasks = []
        for i in range(0, len(pack.LocalizedStrings), batch_size):
            entries = pack.LocalizedStrings[i : i + batch_size]
            entries_json = json_encode(entries).decode("utf-8")
            prompt = (
                "Translate the value of 'enGB' to russian (ruRU), german "
                "(deDE), french (frFR), chinese (zhCN), and spanish (esES) "
                "and replace the corresponding null value with that "
                "translation. Don't describe how, just translate\n"
                f"```{entries_json}```"
            )
            post_task = session.post(
                "https://ora.sh/api/conversation",
                headers={
                    "host": "ora.sh",
                    "authorization": f"Bearer AY0{randint(1111, 9999)}",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; "
                    "rv:109.0) Gecko/20100101 Firefox/112.0",
                    "origin": "https://ora.sh",
                    "referer": "https://ora.sh/chat/",
                },
                json={
                    "chatbotId": self.chat_id,
                    "input": prompt,
                    "userId": self.createdBy,
                    "model": self.model,
                    "provider": "OPEN_AI",
                    "includeHistory": False,
                },
            )
            tasks.append(asyncio.create_task(post_task))
        return tasks

    async def translate(
        self, pack: LocalizationPack, batch_size: int = 16
    ) -> LocalizationPack:
        """Localize the localization pack in batches."""
        pack_translated = LocalizationPack(LocalizedStrings=[])
        async with ClientSession() as session:
            translation_tasks = self.get_translation_tasks(
                session, pack, batch_size
            )
            responses = await asyncio.gather(*translation_tasks)
        for response in responses:
            # TODO: retry on timeout
            reply = (await response.json())["response"]
            code_block = re.findall(r"```[\s\S]*```", reply)[0]
            translation = code_block.replace("```json", "").replace("```", "")
            trans_json = json_decode(translation, type=list[LocalizedString])
            pack_translated.LocalizedStrings.extend(trans_json)
        return pack_translated


# batches_done = i + len(entries)
# print(
#     f"Entries localised: {batches_done} ({batches_done / n:.3%})"
# )
