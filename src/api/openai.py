import os
import re
from asyncio import run
from pathlib import Path
from typing import Self

from dotenv import load_dotenv
from loguru import logger
from msgspec import DecodeError
from msgspec.json import decode as json_decode
from revChatGPT.typings import Error
from revChatGPT.V1 import Chatbot

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
        "other than the json object and do your best at translating in "
        "the context of a homebrew Pathfinder game. "
        "The object should follow this format with the null values replaced "
        "with the corresponding translated input string:\n"
        '{"ruRU": null,"deDE": null,"frFR": null,"zhCN": null,"esES": null}'
    )

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.rate_limited = False

    @classmethod
    def create(cls) -> Self:
        """Create an instance of the OpenAIAPI."""
        load_dotenv()
        return cls(os.getenv("OPENAI_ACCESS_TOKEN", ""))

    def start(self, chatbot: Chatbot) -> str:
        for data in chatbot.ask(self.SYSTEM_PROMPT):
            return data["conversation_id"]

    def get_translation(self, entry: LocalizedString) -> LocalizedString:
        """Get the translation for a LocalizedString."""
        if self.rate_limited:
            logger.warning(f"{entry.SimpleName} skipped due to rate limit.")
            return entry
        if all((entry.ruRU, entry.deDE, entry.frFR, entry.zhCN, entry.esES)):
            logger.info(
                f"{entry.SimpleName} already has a translation; skipped."
            )
            return entry
        if len(entry.enGB or "") >= self.OPENAI_CHAR_LIMIT:
            logger.warning(
                f"{entry.SimpleName} exceeds {self.OPENAI_CHAR_LIMIT} "
                "characters; cannot translate."
            )
            return entry
        reply: str = ""
        try:
            chatbot = Chatbot(config={"access_token": self.access_token})
            conversation_id = self.start(chatbot)
            for response in chatbot.ask(entry.enGB, conversation_id):
                reply = response["message"]
            chatbot.delete_conversation(conversation_id)
            reply_json = re.findall(r"\{[\s\S]*}", reply)[0]
            translation = json_decode(reply_json, type=Translation)
            logger.info(f"{entry.SimpleName} translated successfully.")
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
        except Error as err:
            # Rate Limit Error
            if err.code == 429:
                self.rate_limited = True
            logger.error(
                f"Tried to translate {entry.SimpleName} but failed. "
                f"OpenAI api returned this error:\n{err}"
            )
            return entry
        except Exception as err:
            logger.error(
                f"Tried to translate {entry.SimpleName} but failed. "
                f"OpenAI api returned this error:\n{err}"
            )
            return entry

    async def translate(self, pack: LocalizationPack) -> LocalizationPack:
        """Translate the localization pack."""
        localised_strings = []
        for entry in pack.LocalizedStrings:
            localised_strings.append(self.get_translation(entry))
        return LocalizationPack(LocalizedStrings=localised_strings)


if __name__ == "__main__":
    path_pack = Path(__file__).parent.parent.parent / "data" / "TestPack.json"
    translator_api = OpenAIAPI.create()
    serializer = PackSerializer()

    pack_original = serializer.load(path_pack)
    pack_translated = run(translator_api.translate(pack_original))
    print(pack_translated)
