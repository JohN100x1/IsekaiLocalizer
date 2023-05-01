from pathlib import Path

import click

from api.openai import OpenAIAPI
from pack_processors import PackSerializer, PackTranslator


@click.command(help="Add missing localization to LocalizationPack.json")
@click.argument("path", type=click.Path(exists=True))
@click.option("--json_indent", "-i", type=int, default=2, help="json indent")
def main(path: Path, json_indent: int = 2):
    """Add missing localization to LocalizationPack.json"""

    translator_api = OpenAIAPI.create()
    translator = PackTranslator(translator_api)
    serializer = PackSerializer()

    pack_original = serializer.load(path)
    pack_translated = translator.translate(pack_original)
    serializer.save(path, pack_translated, indent=json_indent)


if __name__ == "__main__":
    main()

# TODO: cycling between access tokens
