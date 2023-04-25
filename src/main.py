import asyncio
from pathlib import Path

from msgspec.json import decode as json_decode
from msgspec.json import encode as json_encode
from msgspec.json import format as json_format

from api import OraAPI, TranslatorAPI
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


class PackLocalizer:
    DEFAULT_TRANSLATOR_API = OraAPI

    def __init__(self, translator_api: TranslatorAPI | None = None):
        self.translator_api = (
            translator_api or self.DEFAULT_TRANSLATOR_API.create()
        )

    def localize(self, pack: LocalizationPack):
        """Localize the localization pack from path and save it."""
        return asyncio.run(self.translator_api.translate(pack))


if __name__ == "__main__":
    replace: bool = False
    json_indent: int = 2

    path_pack = Path(__file__).parent.parent / "data" / "LocalizationPack.json"
    # path_pack = Path(__file__).parent.parent / "data" / "TestPack.json"
    localizer = PackLocalizer()
    serializer = PackSerializer()

    pack_original = serializer.load(path_pack)
    pack_translated = localizer.localize(pack_original)
    if replace:
        save_path = path_pack
    else:
        save_path = path_pack.with_name(
            f"{path_pack.stem}Translated{path_pack.suffix}"
        )
    serializer.save(save_path, pack_translated, indent=json_indent)
