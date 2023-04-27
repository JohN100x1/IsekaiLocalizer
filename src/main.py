from pathlib import Path

from api.openai import OpenAIAPI
from pack_processors import PackSerializer, PackTranslator

if __name__ == "__main__":
    replace: bool = True
    json_indent: int = 2

    path_pack = Path(__file__).parent.parent / "data" / "LocalizationPack.json"
    # path_pack = Path(__file__).parent.parent / "data" / "TestPack.json"
    translator_api = OpenAIAPI.create()
    translator = PackTranslator(translator_api)
    serializer = PackSerializer()

    pack_original = serializer.load(path_pack)
    pack_translated = translator.translate(pack_original)
    if replace:
        save_path = path_pack
    else:
        save_path = path_pack.with_name(
            f"{path_pack.stem}Translated{path_pack.suffix}"
        )
    serializer.save(save_path, pack_translated, indent=json_indent)
