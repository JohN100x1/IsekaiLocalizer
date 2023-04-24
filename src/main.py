import asyncio
from pathlib import Path

from msgspec.json import decode as json_decode
from msgspec.json import encode as json_encode
from msgspec.json import format as json_format

from api import OraAPI, TranslatorAPI
from models import LocalizationPack


class PackLocalizer:
    DEFAULT_TRANSLATOR_API = OraAPI

    def __init__(self, translator_api: TranslatorAPI | None = None):
        self.translator_api = (
            translator_api or self.DEFAULT_TRANSLATOR_API.create()
        )

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

    def localize(
        self,
        path: Path,
        replace: bool = False,
        batch_size: int = 16,
        indent: int = 2,
    ):
        """Localize the localization pack from path and save it."""
        pack = self.load(path)
        pack_translated = asyncio.run(
            self.translator_api.translate(pack, batch_size)
        )

        if replace:
            save_path = path
        else:
            save_path = path.with_name(f"{path.stem}Translated{path.suffix}")
        self.save(save_path, pack_translated, indent=indent)


if __name__ == "__main__":
    # path_localization_pack = (
    #     Path(__file__).parent.parent / "data" / "LocalizationPack.json"
    # )
    path_localization_pack = (
        Path(__file__).parent.parent / "data" / "TestPack.json"
    )
    localizer = PackLocalizer()
    localizer.localize(path_localization_pack, batch_size=2)
