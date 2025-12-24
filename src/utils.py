import yaml

from pathlib import Path
from typing import Any

def load_config(config_path: str = 'config.yaml') -> dict[str, Any]:
   """
   Load database configuration from YAML file.
   
   Args:
      config_path: Path to config.yaml file.
      
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
            if config and 'database' in config:
               return config['database']
            else:
               raise KeyError("Database configuration not found in config.yaml")

   except Exception as e:
      raise RuntimeError(f"Failed to load config.yaml: {e}")