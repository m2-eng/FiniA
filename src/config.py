#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Central configuration access.
#
"""
Central configuration access helpers.
"""

from typing import Any

from utils import load_config


DEFAULT_CONFIG_PATH = "cfg/config.yaml"


def get_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    return load_config(config_path=config_path)


def get_config_section(
    section: str | None = None,
    config_path: str = DEFAULT_CONFIG_PATH,
) -> dict[str, Any]:
    if section:
        return load_config(config_path=config_path, subconfig=section)
    return load_config(config_path=config_path)
