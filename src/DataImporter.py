#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for DataImporter.
#
import logging
from pathlib import Path
import yaml
from typing import Any

from Database import Database
from services.import_service import ImportService
from services.import_steps.account_types import AccountTypesStep
from services.import_steps.planning_cycles import PlanningCyclesStep
from services.import_steps.accounts import AccountsStep
from services.import_steps.categories import CategoriesStep


logger = logging.getLogger("uvicorn.error")


class DataImporter:
   """Import predefined data from YAML into FiniA using a provided Database instance."""

   def __init__(self, db: Database):
      self.db = db

   def load_yaml_data(self, yaml_file_path: str) -> dict[str, Any] | None:
      """
      Load predefined data from YAML file.

      Args:
         yaml_file_path: Path to the data.yaml file.

      Returns:
         Dictionary with loaded data or None on failure.
      """
      try:
         yaml_file = Path(yaml_file_path)
         if not yaml_file.exists():
            raise FileNotFoundError(f"Data file not found: {yaml_file_path}")

         with open(yaml_file, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)

         logger.info("Successfully loaded data from %s", yaml_file_path)
         return data

      except FileNotFoundError as e:
         logger.error("%s", e)
         return None
      except Exception as e:
         logger.error("Error loading YAML data: %s", e)
         return None

   def import_data(self, yaml_file_path: str) -> bool:
      """
      Complete workflow for importing predefined data from YAML.

      Args:
         yaml_file_path: Path to data.yaml file.

      Returns:
         True if successful, False otherwise.
      """
      logger.info("%s", "=" * 100)
      logger.info("FiniA Data Import from YAML")
      logger.info("%s", "=" * 100)

      # Load YAML data
      data = self.load_yaml_data(yaml_file_path)
      if not data:
         return False

      # Ensure DB connection
      self.db.close()
      if not self.db.connect(use_database=True):
         raise RuntimeError("Failed to connect to MySQL database")

      logger.info("Importing data")

      # Build pipeline (order matters)
      steps = []
      if 'accountType' in data:
         steps.append(AccountTypesStep())
      if 'planningCycle' in data:
         steps.append(PlanningCyclesStep())
      if 'categories' in data:
         steps.append(CategoriesStep())
      if 'account_data' in data:
         steps.append(AccountsStep())

      service = ImportService(self.db.connection, steps)
      success = service.run(data)

      self.db.close()

      logger.info("%s", "=" * 100)
      if success:
         logger.info("Data import completed successfully!")
      else:
         logger.warning("Data import completed with warnings")
      logger.info("%s", "=" * 100)

      return success
