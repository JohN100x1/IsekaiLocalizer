import os
import re
from asyncio import run
from pathlib import Path
from typing import Self

from dotenv import load_dotenv
from loguru import logger
from msgspec import DecodeError
from msgspec.json import decode as json_decode
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
        "other than the json object and will do your best at translating in "
        "the context of homebrew Pathfinder feature names and descriptions. "
        "The object should follow this format with the null values replaced "
        "with the corresponding translation:\n"
        '{"ruRU": null,"deDE": null,"frFR": null,"zhCN": null,"esES": null}'
    )

    def __init__(self, access_token: str):
        self.access_token = access_token

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
        chatbot = Chatbot(config={"access_token": self.access_token})
        conversation_id = self.start(chatbot)
        if len(entry.enGB or "") >= self.OPENAI_CHAR_LIMIT:
            logger.warning(
                f"{entry.SimpleName} exceeds {self.OPENAI_CHAR_LIMIT} "
                "characters; cannot translate."
            )
            return entry
        reply: str = ""
        for response in chatbot.ask(entry.enGB, conversation_id):
            reply = response["message"]
        try:
            chatbot.delete_conversation(conversation_id)
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
        except Exception as err:
            logger.warning(
                f"Tried to translate {entry.SimpleName} but failed. "
                f"OpenAI api returned this error:\n{err}"
            )
            return entry

    async def translate(self, pack: LocalizationPack) -> LocalizationPack:
        """Translate the localization pack."""
        # TODO: entry replacement logic (so filled entries are re-translated)
        localised_strings = []
        n = len(pack.LocalizedStrings)
        for i, entry in enumerate(pack.LocalizedStrings, 1):
            localised_strings.append(self.get_translation(entry))
            print(f"Entries translated: {i} ({i/n:.3%})")
        return LocalizationPack(LocalizedStrings=localised_strings)


if __name__ == "__main__":
    path_pack = Path(__file__).parent.parent.parent / "data" / "TestPack.json"
    translator_api = OpenAIAPI.create()
    serializer = PackSerializer()

    pack_original = serializer.load(path_pack)
    pack_translated = run(translator_api.translate(pack_original))
    print(pack_translated)
