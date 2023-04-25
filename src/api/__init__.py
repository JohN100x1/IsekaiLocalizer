from abc import ABC, abstractmethod
from typing import Self

from models import LocalizationPack


class TranslatorAPI(ABC):
    @classmethod
    @abstractmethod
    def create(cls) -> Self:
        """Create an instance of the TranslatorAPI."""
        ...

    @abstractmethod
    async def translate(self, pack: LocalizationPack) -> LocalizationPack:
        """Translate the localization pack from enGB."""
        ...
