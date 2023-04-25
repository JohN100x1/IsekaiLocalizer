import asyncio
from pathlib import Path

from msgspec.json import decode as json_decode
from msgspec.json import encode as json_encode
from msgspec.json import format as json_format

from api import TranslatorAPI
from models import LocalizationPack


class PackSerializer:
    @staticmethod
    def load(path: Path) -> LocalizationPack:
        """Load the localization pack from a specified path."""
        with open(path, "rb") as file:
            return json_decode(file.read(), type=LocalizationPack)

    @staticmethod
    def save(path: Path, pack: LocalizationPack, indent: int = 2):
        """Save the localization pack at specified path."""
        with open(path, "wb") as file:
            file.write(json_format(json_encode(pack), indent=indent))


class PackTranslator:
    def __init__(self, translator_api: TranslatorAPI):
        self.translator_api = translator_api

    def translate(self, pack: LocalizationPack) -> LocalizationPack:
        """Translate the localization pack."""
        return asyncio.run(self.translator_api.translate(pack))
