from typing import List
from services.import_steps.base import ImportStep
from infrastructure.unit_of_work import UnitOfWork


class ImportService:
   def __init__(self, connection, steps: List[ImportStep]):
      self.connection = connection
      self.steps = steps

   def run(self, data: dict) -> bool:
      success = True
      for step in self.steps:
         print(f"Running step: {step.name()}")
         with UnitOfWork(self.connection) as uow:
            ok = step.run(data, uow)
            success = success and ok
      return success
