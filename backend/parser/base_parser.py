from abc import ABC, abstractmethod


class BaseParser(ABC):
    @abstractmethod
    def parse(self, code: str) -> dict:
        raise NotImplementedError
