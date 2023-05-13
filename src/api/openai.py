import os
import re
from typing import Self

from dotenv import load_dotenv
from loguru import logger
from msgspec import DecodeError
from msgspec.json import decode as json_decode
from revChatGPT.typings import Error
from revChatGPT.V1 import Chatbot

from api import TranslatorAPI
from models import LocalizationPack, LocalizedString, Translation


class OpenAIAPI(TranslatorAPI):
    OPENAI_CHAR_LIMIT = 4000
    SYSTEM_PROMPT = """Act as a translator. You will translate the user input from English to russian, german, french, chinese, and spanish. Return this translation as a json object with the following format:
{"ruRU": null,"deDE": null,"frFR": null,"zhCN": null,"esES": null}
where the null values are replaced with the corresponding translation.
Do not return anything other than the json object and do your best at translating in the context of a homebrew Pathfinder game.
Make sure newlines are quotes are escaped"""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.rate_limited = False

    @classmethod
    def create(cls) -> Self:
        """Create an instance of the OpenAIAPI."""
        load_dotenv()
        os.environ[
            "CHATGPT_BASE_URL"
        ] = "https://bypass.churchless.tech/conversation"
        return cls(os.getenv("OPENAI_ACCESS_TOKEN", ""))

    @staticmethod
    def extract_localized_string(
        entry: LocalizedString, reply: str
    ) -> LocalizedString:
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

    def retry_get_translation(
        self, chatbot: Chatbot, conversation_id: str, entry: LocalizedString
    ) -> LocalizedString:
        """Retry getting the translation for a LocalizedString."""
        replies = [""]
        try:
            fixing_prompt = (
                "This is not the right json format. Please just replace the "
                "null values with the entire translated string."
            )
            finish_details = "max_tokens"
            for response in chatbot.ask(fixing_prompt, conversation_id):
                replies[0] = response["message"]
                finish_details = response["finish_details"]
            finished = finish_details == "stop"
            while not finished:
                reply = ""
                for response in chatbot.ask("continue", conversation_id):
                    reply = response["message"]
                    finish_details = response["finish_details"]
                replies.append(reply)
                finished = finish_details == "stop"
            return self.extract_localized_string(entry, "".join(replies))
        except DecodeError:
            logger.error(
                f"Tried to translate {entry.SimpleName} but "
                "a json decode error occurred. Tried to parse this:\n"
                f"{''.join(replies)}"
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

    def get_translation(self, entry: LocalizedString) -> LocalizedString:
        """Get the translation for a LocalizedString."""
        replies = [""]
        conversation_id: str = ""
        chatbot = Chatbot(config={"access_token": self.access_token})
        try:
            for data in chatbot.ask(self.SYSTEM_PROMPT):
                conversation_id = data["conversation_id"]
            finish_details = "max_tokens"
            for response in chatbot.ask(entry.enGB, conversation_id):
                replies[0] = response["message"]
                finish_details = response["finish_details"]
            finished = finish_details == "stop"
            while not finished:
                reply = ""
                for response in chatbot.ask("continue", conversation_id):
                    reply = response["message"]
                    finish_details = response["finish_details"]
                replies.append(reply)
                finished = finish_details == "stop"
            return self.extract_localized_string(entry, "".join(replies))
        except DecodeError:
            return self.retry_get_translation(chatbot, conversation_id, entry)
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
        finally:
            try:
                # conversation_id can be empty if it fails to ask SYSTEM_PROMPT
                chatbot.delete_conversation(conversation_id)
            except Exception as err:
                logger.warning(
                    f"{conversation_id=} could not be deleted. "
                    f"OpenAI api returned this error:\n{err}"
                )

    def translate(self, pack: LocalizationPack) -> LocalizationPack:
        """Translate the localization pack."""
        localised_strings = []
        rate_limited = 0
        already_translated = 0
        character_limited = 0
        for entry in pack.LocalizedStrings:
            if self.rate_limited:
                localised_strings.append(entry)
                rate_limited += 1
            elif all(
                (entry.ruRU, entry.deDE, entry.frFR, entry.zhCN, entry.esES)
            ):
                already_translated += 1
                localised_strings.append(entry)
            elif len(entry.enGB or "") >= self.OPENAI_CHAR_LIMIT:
                character_limited += 1
                localised_strings.append(entry)
            else:
                localised_strings.append(self.get_translation(entry))
        logger.info(
            f"Skipped {already_translated} entries due to existing "
            "translation."
        )
        logger.warning(
            f"Skipped {character_limited} entries due to character limit."
        )
        logger.warning(f"Skipped {rate_limited} entries due to rate limit.")
        return LocalizationPack(LocalizedStrings=localised_strings)
