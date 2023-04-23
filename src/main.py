import re
from pathlib import Path

from msgspec.json import decode as json_decode
from msgspec.json import encode as json_encode
from msgspec.json import format as json_format

from api import ChatAPI, OraAPI
from models import LocalizationPack, LocalizedString


class PackLocalizer:
    DEFAULT_CHATAPI = OraAPI

    def __init__(self, chat_api: ChatAPI | None = None):
        self.chat_api = chat_api or self.DEFAULT_CHATAPI.create()

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

    @staticmethod
    def __get_prompt(entries_json: str) -> str:
        """Create prompt to get translation for entries."""
        return (
            "For each object in the list, translate the value of 'enGB' to "
            "russian, german, french, chinese, and spanish and replace the "
            "corresponding null value with that translation\n"
            f"```{entries_json}```"
        )

    @staticmethod
    def __extract_code_block(reply: str) -> str:
        """Extract a code block from a string."""
        return re.findall(r"```[\s\S]*```", reply)[0]

    def localize_pack(
        self, pack: LocalizationPack, batch_size: int = 16
    ) -> LocalizationPack:
        """Localize the localization pack in batches."""
        pack_translated = LocalizationPack(LocalizedStrings=[])
        n = (len(pack.LocalizedStrings) - 1) // batch_size + 1
        for i in range(0, len(pack.LocalizedStrings), batch_size):
            entries = pack.LocalizedStrings[i : i + batch_size]
            entries_json = json_encode(entries).decode("utf-8")
            # TODO: pray for no errors here
            reply = self.chat_api.chat(self.__get_prompt(entries_json))
            code_block = self.__extract_code_block(reply)
            translation = code_block.replace("```json", "").replace("```", "")
            trans_json = json_decode(translation, type=list[LocalizedString])
            pack_translated.LocalizedStrings.extend(trans_json)
            print(f"{(i+1)/n:.3%}")
        return pack_translated

    def localize(
        self,
        path: Path,
        replace: bool = False,
        batch_size: int = 16,
        indent: int = 2,
    ):
        """Localize the localization pack from path and save it."""
        pack = self.load(path)
        pack_translated = self.localize_pack(pack, batch_size)

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
