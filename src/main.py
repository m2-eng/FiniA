#!/usr/bin/env python3
#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: API entrypoint for FiniA
#
"""
API entrypoint for FiniA.
Starts the FastAPI server using config.yaml settings.
"""

import asyncio
import logging
import platform

import uvicorn

from config import get_config_section


if __name__ == "__main__":
   logger = logging.getLogger("uvicorn.error")
   api_config = get_config_section("api")

   host = api_config.get("host", "127.0.0.1")
   port = api_config.get("port", 8000)
   log_level = api_config.get("log_level", "info")

   logger.info("Starting FiniA API server on http://%s:%s", host, port)
   logger.info("API documentation: http://%s:%s/api/docs", host, port)
   logger.info("Web interface: http://%s:%s/", host, port)
   logger.info("User authentication via login form - memory-only sessions")

   # Windows: use SelectorEventLoop to avoid Proactor connection_lost errors (WinError 10054)
   if platform.system() == "Windows":
      try:
         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
      except Exception:
         pass

   uvicorn.run(
      "api.main:app",
      host=host,
      port=port,
      reload=False,
      log_level=log_level
   )
