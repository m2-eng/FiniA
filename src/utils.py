#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for utils.
#
import yaml

from pathlib import Path
from typing import Any

def load_config(config_path: str = 'config.yaml', subconfig: str = None) -> dict[str, Any]:
   """
   Load database configuration from YAML file.
   
   Args:
      config_path: Path to config.yaml file.
      subconfig: Optional sub-configuration key to extract specific configuration.
      
   Returns:
      Database configuration as a dictionary.
   """
   try:
      config_file = Path(config_path)
      if not config_file.exists():
         raise FileNotFoundError(f"config.yaml not found at: {config_path}")
      else:
         with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

            # Extract defaults from config if available
            if subconfig:
                if subconfig in config:
                    return config[subconfig]
                else:
                    raise KeyError(f"Sub-configuration '{subconfig}' not found in configuration")
            else:
                return config


   except Exception as e:
      raise RuntimeError(f"Failed to load config.yaml: {e}")