#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for planning cycles.
#
import logging

from services.import_steps.base import ImportStep
from repositories.planning_cycle_repository import PlanningCycleRepository


logger = logging.getLogger("uvicorn.error")


class PlanningCyclesStep(ImportStep):
   def name(self) -> str:
      return "planning_cycles"

   def run(self, data: dict, uow) -> bool:
      key = "planningCycle"
      if not data or key not in data:
         logger.info("No planningCycle data found in YAML")
         return True
      repo = PlanningCycleRepository(uow)
      inserted = 0
      cycles = data[key]

      if isinstance(cycles, dict):
         for cycle_name, cycle_id in cycles.items():
            repo.insert_ignore(cycle_id, cycle_name)
            inserted += 1
      elif isinstance(cycles, list):
         for item in cycles:
            cycle_name = item.get("cycle") if isinstance(item, dict) else None
            period_value = item.get("periodValue", 1) if isinstance(item, dict) else 1
            period_unit = item.get("periodUnit", "m") if isinstance(item, dict) else "m"
            if not cycle_name:
               continue
            repo.insert(cycle_name, period_value, period_unit)
            inserted += 1
      else:
         logger.warning("Unsupported planningCycle format in YAML")
         return True
      logger.info("Inserted %s planning cycles into tbl_planningCycle", inserted)
      return True
