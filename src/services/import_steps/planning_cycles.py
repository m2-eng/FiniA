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
      defaults = {
         "einmalig": (0.0, "d"),
         "t\u00e4glich": (1.0, "d"),
         "w\u00f6chentlich": (7.0, "d"),
         "14-t\u00e4gig": (14.0, "d"),
         "monatlich": (1.0, "m"),
         "viertelj\u00e4hrlich": (3.0, "m"),
         "halbj\u00e4hrlich": (6.0, "m"),
         "j\u00e4hrlich": (1.0, "y"),
      }

      for cycle_name, value in data[key].items():
         if isinstance(value, dict):
            cycle_id = value.get("id")
            period_value = value.get("periodValue")
            period_unit = value.get("periodUnit")
         else:
            cycle_id = value
            period_value = None
            period_unit = None

         if cycle_id is None:
            raise ValueError(f"planningCycle entry '{cycle_name}' is missing required 'id'")

         if period_value is None or period_unit is None:
            period_value, period_unit = defaults.get(cycle_name, (1.0, "m"))

         repo.upsert(cycle_id, cycle_name, period_value, period_unit)
         inserted += 1

      print(f"  Upserted {inserted} planning cycles into tbl_planningCycle")
      return True
