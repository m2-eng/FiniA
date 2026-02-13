#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for base.
#
from abc import ABC, abstractmethod


class ImportStep(ABC):
   @abstractmethod
   def name(self) -> str: ...

   @abstractmethod
   def run(self, data: dict, uow) -> bool: ...
