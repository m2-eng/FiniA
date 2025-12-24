from services.import_steps.base import ImportStep
from repositories.planning_cycle_repository import PlanningCycleRepository


class PlanningCyclesStep(ImportStep):
   def name(self) -> str:
      return "planning_cycles"

   def run(self, data: dict, uow) -> bool:
      key = "planningCycle"
      if not data or key not in data:
         print("  No planningCycle data found in YAML")
         return True
      repo = PlanningCycleRepository(uow)
      inserted = 0
      for cycle_name, cycle_id in data[key].items():
         repo.insert_ignore(cycle_id, cycle_name)
         inserted += 1
      print(f"  Inserted {inserted} planning cycles into tbl_planningCycle")
      return True
