import re
from asyncio import Task, create_task, gather, run
from random import randint
from typing import Self
from uuid import uuid4

from aiohttp import ClientSession
from loguru import logger
from msgspec import DecodeError
from msgspec.json import decode as json_decode

from api import TranslatorAPI
from models import LocalizationPack, LocalizedString, Translation


class OraAPI(TranslatorAPI):
    ORA_CHAR_LIMIT = 1000
    SYSTEM_PROMPT = (
        "Translate the user input from English to russian (ruRU), "
        "german (deDE), french (frFR), chinese (zhCN), and spanish (esES) "
        "and return a json object where the language ISO is the key and "
        "the translation is the value. Do not return anything other than the"
        "json object. The object should follow this format with the null "
        "values replaced with the corresponding translation:\n"
        '{"ruRU": null,"deDE": null,"frFR": null,"zhCN": null,"esES": null}'
    )
    DESC = "ChatGPT Openai Language Model"
    SLUG = "gpt-3.5"
    MODEL = "gpt-3.5-turbo"

    def __init__(
        self,
        chat_id: str,
        created_by: str,
        created_at: str,
        max_retries: int = 3,
    ):
        self.chat_id = chat_id
        self.createdBy = created_by
        self.createdAt = created_at
        self.max_retries = max_retries

    @classmethod
    def create(cls, max_retries: int = 3) -> Self:
        """Create an instance of the OraAPI."""
        return run(cls.create_ora_api(max_retries))

    @classmethod
    async def create_ora_api(cls, max_retries: int = 3) -> Self:
        """Create an instance of the OraAPI."""
        async with ClientSession() as session:
            response = await session.post(
                "https://ora.sh/api/assistant",
                headers={
                    "Origin": "https://ora.sh",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; "
                    "x64; rv:109.0) Gecko/20100101 Firefox/112.0",
                    "Referer": "https://ora.sh/",
                    "Host": "ora.sh",
                },
                json={
                    "prompt": cls.SYSTEM_PROMPT,
                    "userId": f"auto:{uuid4()}",
                    "name": cls.SLUG,
                    "description": cls.DESC,
                },
            )
            response_json = await response.json()
            return cls(
                chat_id=response_json["id"],
                created_by=response_json["createdBy"],
                created_at=response_json["createdAt"],
                max_retries=max_retries,
            )

    async def get_translation(
        self,
        session: ClientSession,
        entry: LocalizedString,
        max_retries: int = 3,
    ) -> LocalizedString:
        """Get the translation for a LocalizedString."""
        if len(entry.enGB or "") >= self.ORA_CHAR_LIMIT:
            logger.warning(
                f"{entry.SimpleName} exceeds {self.ORA_CHAR_LIMIT} "
                "characters; cannot translate."
            )
            return entry

        url = "https://ora.sh/api/conversation"
        headers = {
            "host": "ora.sh",
            "authorization": f"Bearer AY0{randint(1111, 9999)}",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; "
            "rv:109.0) Gecko/20100101 Firefox/112.0",
            "origin": "https://ora.sh",
            "referer": "https://ora.sh/chat/",
        }  # TODO: add x-signed-token to header
        data_json = {
            "chatbotId": self.chat_id,
            "input": entry.enGB,
            "userId": self.createdBy,
            "model": self.MODEL,
            "provider": "OPEN_AI",
            "includeHistory": False,
        }
        retry_count = 0
        errors: list[dict] = []
        while retry_count < max_retries:
            async with session.post(
                url, headers=headers, json=data_json
            ) as response:
                response_json = await response.json()
                if response.status != 200:
                    retry_count += 1
                    errors.append(response_json["error"])
                    continue
                reply: str = response_json["response"]
                try:
                    reply_json = re.findall(r"\{[\s\S]*}", reply)[0]
                    translation = json_decode(reply_json, type=Translation)
                    return LocalizedString(
                        Key=entry.Key,
                        SimpleName=entry.SimpleName,
                        ProcessTemplates=entry.ProcessTemplates,
                        enGB=entry.enGB,
                        ruRU=entry.ruRU if entry.ruRU else translation.ruRU,
                        deDE=entry.deDE if entry.deDE else translation.deDE,
                        frFR=entry.frFR if entry.frFR else translation.frFR,
                        zhCN=entry.zhCN if entry.zhCN else translation.zhCN,
                        esES=entry.esES if entry.esES else translation.esES,
                    )
                except DecodeError:
                    logger.error(
                        f"Tried to translate {entry.SimpleName} but "
                        "a json decode error occurred. Tried to parse this:\n"
                        f"{reply}"
                    )
                    return entry
        error_msg = "\n".join(str(err) for err in errors)
        logger.warning(
            f"Tried to translate {entry.SimpleName} but failed "
            f"after {max_retries=}. Ora api returned these errors:\n"
            f"{error_msg}"
        )
        return entry

    def get_translation_tasks(
        self,
        session: ClientSession,
        pack: LocalizationPack,
        max_retries: int = 3,
    ) -> list[Task[LocalizedString]]:
        """Get a list of the translation tasks."""
        return [
            create_task(self.get_translation(session, entry, max_retries))
            for entry in pack.LocalizedStrings
        ]

    async def translate(self, pack: LocalizationPack) -> LocalizationPack:
        """Translate the localization pack."""
        async with ClientSession() as session:
            translation_tasks = self.get_translation_tasks(
                session, pack, max_retries=self.max_retries
            )
            localised_strings = await gather(*translation_tasks)
        return LocalizationPack(LocalizedStrings=localised_strings)
