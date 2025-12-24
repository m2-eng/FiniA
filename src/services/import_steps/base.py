from abc import ABC, abstractmethod


class ImportStep(ABC):
   @abstractmethod
   def name(self) -> str: ...

   @abstractmethod
   def run(self, data: dict, uow) -> bool: ...
