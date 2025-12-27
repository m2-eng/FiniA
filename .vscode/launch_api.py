"""
Wrapper-Skript zum Laden der API-Argumente aus der cmd-Datei
"""
import sys
import os
from pathlib import Path

# Lese Argumente aus cmd-Datei (eine Ebene höher)
cmd_file = Path(__file__).parent.parent / "cmd"
with open(cmd_file, 'r', encoding='utf-8') as f:
    args_string = f.read().strip()

# Parse Argumente (einfaches Split, behält Quotes)
import shlex
args = shlex.split(args_string)

# Füge Argumente zu sys.argv hinzu
sys.argv.extend(args)

# Setze Working Directory auf Projektroot (nicht src!)
project_root = Path(__file__).parent.parent
os.chdir(str(project_root))  # Wechsle ins Projektverzeichnis (wo cfg/ liegt)

# Füge src zum Python-Pfad hinzu
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

# Main-Skript direkt ausführen
main_script = src_dir / "main.py"

# Führe main.py aus als wäre es das Hauptprogramm
import runpy
runpy.run_path(str(main_script), run_name="__main__")
