import os
import re
from asyncio import Task, create_task, gather, run
from pathlib import Path
from typing import Self

from dotenv import load_dotenv
from loguru import logger
from msgspec import DecodeError
from msgspec.json import decode as json_decode
from revChatGPT.V1 import AsyncChatbot

from api import TranslatorAPI
from models import LocalizationPack, LocalizedString, Translation
from pack_processors import PackSerializer


class OpenAIAPI(TranslatorAPI):
    OPENAI_CHAR_LIMIT = 4000
    SYSTEM_PROMPT = (
        "You are a translator. You will translate the user input from English "
        "to russian (ruRU), german (deDE), french (frFR), chinese (zhCN), "
        "and spanish (esES) and return a json object where the language ISO "
        "is the key and the translation is the value. Do not return anything "
        "other than the json object and will do your best at translating in "
        "the context of homebrew Pathfinder class, feat, and ability names "
        "and descriptions. The object should follow this format with the null "
        "values replaced with the corresponding translation:\n"
        '{"ruRU": null,"deDE": null,"frFR": null,"zhCN": null,"esES": null}'
    )
    DESC = "ChatGPT Openai Language Model"
    SLUG = "gpt-3.5"
    MODEL = "gpt-3.5-turbo"

    def __init__(self, access_token: str):
        self.access_token = access_token

    @classmethod
    def create(cls) -> Self:
        """Create an instance of the OpenAIAPI."""
        load_dotenv()
        return cls(os.getenv("OPENAI_ACCESS_TOKEN", ""))

    async def start(self, chatbot: AsyncChatbot) -> str:
        async for data in chatbot.ask(self.SYSTEM_PROMPT):
            return data["conversation_id"]

    async def get_translation(
        self,
        chatbot: AsyncChatbot,
        conversation_id: str,
        entry: LocalizedString,
        max_retries: int = 3,
    ) -> LocalizedString:
        """Get the translation for a LocalizedString."""
        if len(entry.enGB or "") >= self.OPENAI_CHAR_LIMIT:
            logger.warning(
                f"{entry.SimpleName} exceeds {self.OPENAI_CHAR_LIMIT} "
                "characters; cannot translate."
            )
            return entry
        retry_count = 0
        errors: list[Exception] = []
        while retry_count < max_retries:
            async for response in chatbot.ask(entry.enGB, conversation_id):
                try:
                    reply: str = response["message"]
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
                        f"{response['message']}"
                    )
                    return entry
                except Exception as err:
                    errors.append(err)
        error_msg = "\n".join(str(err) for err in errors)
        logger.warning(
            f"Tried to translate {entry.SimpleName} but failed "
            f"after {max_retries=}. OpenAI api returned these errors:\n"
            f"{error_msg}"
        )
        return entry

    def get_translation_tasks(
        self,
        chatbot: AsyncChatbot,
        conversation_id: str,
        pack: LocalizationPack,
        max_retries: int = 3,
    ) -> list[Task[LocalizedString]]:
        """Get a list of the translation tasks."""
        return [
            create_task(
                self.get_translation(
                    chatbot, conversation_id, entry, max_retries
                )
            )
            for entry in pack.LocalizedStrings
        ]

    async def translate(self, pack: LocalizationPack) -> LocalizationPack:
        """Translate the localization pack."""
        chatbot = AsyncChatbot(config={"access_token": self.access_token})
        conversation_id = await self.start(chatbot)
        localised_strings = []
        n = len(pack.LocalizedStrings)
        for i, entry in enumerate(pack.LocalizedStrings, 1):
            localised_strings.append(
                await self.get_translation(
                    chatbot, conversation_id, entry, max_retries=3
                )
            )
            print(f"Entries translated: {i} ({i/n:.3%})")
        return LocalizationPack(LocalizedStrings=localised_strings)


if __name__ == "__main__":
    path_pack = Path(__file__).parent.parent.parent / "data" / "TestPack.json"
    translator_api = OpenAIAPI.create()
    serializer = PackSerializer()

    pack_original = serializer.load(path_pack)
    pack_translated = run(translator_api.translate(pack_original))
    print(pack_translated)
