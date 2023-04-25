from pathlib import Path
from typing import Self

import pytest
from msgspec import DecodeError

from api import TranslatorAPI
from models import LocalizationPack, LocalizedString
from pack_processors import PackSerializer, PackTranslator


class TestPackSerializer:
    def test_load_valid(self):
        path_pack = Path(__file__).parent / "TestPackValid.json"
        serializer = PackSerializer()
        pack = serializer.load(path_pack)
        assert pack == LocalizationPack(
            LocalizedStrings=[
                LocalizedString(
                    Key="714b99be4cc74d8ea02500d4c7cffa4e",
                    SimpleName="$IsekaiProtagonistSpellbook.Name",
                    ProcessTemplates=False,
                    enGB="Isekai Protagonist",
                    ruRU=None,
                    deDE=None,
                    frFR=None,
                    zhCN=None,
                    esES=None,
                )
            ]
        )

    def test_load_invalid(self):
        path_pack = Path(__file__).parent / "TestPackInvalid.json"
        serializer = PackSerializer()
        with pytest.raises(DecodeError, match="malformed"):
            serializer.load(path_pack)

    def test_save_valid(self, tmp_path):
        tmp_file = tmp_path / "test_file.json"

        serializer = PackSerializer()
        pack = LocalizationPack(
            LocalizedStrings=[
                LocalizedString(
                    Key="102a73bb49154ffb9b7f924447f6941b",
                    SimpleName="FooBar.Name",
                    ProcessTemplates=True,
                    enGB="Foo Bar",
                    ruRU=None,
                    deDE=None,
                    frFR=None,
                    zhCN=None,
                    esES=None,
                )
            ]
        )
        serializer.save(tmp_file, pack)

        with open(tmp_file) as f:
            result = f.read()

        assert result == (
            "{\n"
            '  "LocalizedStrings": [\n'
            "    {\n"
            '      "Key": "102a73bb49154ffb9b7f924447f6941b",\n'
            '      "SimpleName": "FooBar.Name",\n'
            '      "ProcessTemplates": true,\n'
            '      "enGB": "Foo Bar",\n'
            '      "ruRU": null,\n'
            '      "deDE": null,\n'
            '      "frFR": null,\n'
            '      "zhCN": null,\n'
            '      "esES": null\n'
            "    }\n"
            "  ]\n"
            "}"
        )


class DummyTranslatorAPI(TranslatorAPI):
    @classmethod
    def create(cls) -> Self:
        return cls()

    async def translate(self, pack: LocalizationPack) -> LocalizationPack:
        return LocalizationPack(
            LocalizedStrings=[
                LocalizedString(
                    Key="102a73bb49154ffb9b7f924447f6941b",
                    SimpleName="FooBar.Name",
                    ProcessTemplates=True,
                    enGB="Foo Bar",
                    ruRU="what",
                    deDE="on",
                    frFR="earth",
                    zhCN="is",
                    esES="this",
                )
            ]
        )


class TestPackTranslator:
    def test_translate(self):
        translator_api = DummyTranslatorAPI.create()
        translator = PackTranslator(translator_api)
        pack = LocalizationPack(
            LocalizedStrings=[
                LocalizedString(
                    Key="102a73bb49154ffb9b7f924447f6941b",
                    SimpleName="FooBar.Name",
                    ProcessTemplates=True,
                    enGB="Foo Bar",
                    ruRU=None,
                    deDE=None,
                    frFR=None,
                    zhCN=None,
                    esES=None,
                )
            ]
        )
        assert translator.translate(pack) == LocalizationPack(
            LocalizedStrings=[
                LocalizedString(
                    Key="102a73bb49154ffb9b7f924447f6941b",
                    SimpleName="FooBar.Name",
                    ProcessTemplates=True,
                    enGB="Foo Bar",
                    ruRU="what",
                    deDE="on",
                    frFR="earth",
                    zhCN="is",
                    esES="this",
                )
            ]
        )
