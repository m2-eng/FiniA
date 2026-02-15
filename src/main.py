#!/usr/bin/env python3
#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Database creation script for FiniA
#
"""
Database creation script for FiniA
Creates the database structure from the SQL dump file on a specified MySQL/MariaDB server.
Can also launch the GUI application.
"""

import sys
import argparse
import logging

from Database import Database
from DatabaseCreator import DatabaseCreator
from DataImporter import DataImporter

from pathlib import Path
from utils import load_config


if __name__ == "__main__":
   """Main function with argument parsing"""
   logger = logging.getLogger("uvicorn.error")  # Use uvicorn's logger for consistency with API logs
   # Argument parser setup
   parser = argparse.ArgumentParser(
      description='FiniA - Finanzverwaltungssystem (uses config.yaml for defaults)',
      formatter_class=argparse.RawDescriptionHelpFormatter,
      epilog="""
   Examples:
     python main.py --user root --password secret --setup
     python main.py -u dbuser -p dbpass --init-database
     python main.py --api --user root --password secret --config cfg/config.yaml
  
   Note: Most parameters are read from config.yaml by default.
      Use command-line arguments to override config values.
      """
   )
   # finding: CLI shall be removed and replace by API calls. The API will be the main entry point for all operations, including database setup and initialization. 
   parser.add_argument('--user',
                       help='MySQL user (only required for --setup, --init-database)')
   parser.add_argument('--password',
                       help='MySQL password (only required for --setup, --init-database)')
   parser.add_argument('--config',
                       default='cfg/config.yaml',
                       help='Path to config file (default: cfg/config.yaml)')
   parser.add_argument('--init-database',
                       action="store_true",
                       help='Can be empty, used to initialize the database (see linked folders for each account)')
   parser.add_argument('--setup',
                       action="store_true",
                       help='Can be empty, used to create the database')
   parser.add_argument('--api',
                       action="store_true",
                       help='Launch the web API server (FastAPI)')
   parser.add_argument('--host',
                       default='127.0.0.1',
                       help='API server host (default: 127.0.0.1)')
   parser.add_argument('--port',
                       type=int,
                       default=8000,
                       help='API server port (default: 8000)')
    
   args = parser.parse_args()

   # Load configuration from config.yaml
   db_config = load_config( config_path=args.config, subconfig='database')

   # Launch API server if requested
   if args.api:
      import uvicorn
      import asyncio
      import platform
      from api.dependencies import set_database_credentials
      
      logger.info("Starting FiniA API server on http://%s:%s", args.host, args.port)
      logger.info("API documentation: http://%s:%s/api/docs", args.host, args.port)
      logger.info("Web interface: http://%s:%s/", args.host, args.port)
      logger.info("User authentication via login form - memory-only sessions")
      
      # Windows: use SelectorEventLoop to avoid Proactor connection_lost errors (WinError 10054)
      if platform.system() == "Windows":
         try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
         except Exception:
            # If setting the policy fails, continue with default
            pass

      # Set database connection info (no user credentials - they come from login!)
      # Users authenticate via /api/auth/login with their DB credentials
      # Database config is read directly from cfg/config.yaml
      set_database_credentials(
         user=None,  # Not used - credentials from login
         password=None,  # Not used - credentials from login
         host=db_config.get('host', 'localhost'),
         name=None,  # Each user has their own DB: finiaDB_<username>
         port=db_config.get('port', 3306)
      )
      
      uvicorn.run(
         "api.main:app",
         host=args.host,
         port=args.port,
         reload=False,
         log_level="info"
      )
      sys.exit(0)

   # For database operations, user and password are required
   if not args.api and (not args.user or not args.password):
      parser.error("--user and --password are required for database operations")

   db = Database( # finding: It seems that the database is a duplicate.
      host=db_config.get('host', 'localhost'),
      user=args.user,
      password=args.password,
      database_name=db_config.get('name', 'FiniA'),
      port=db_config.get('port', 3306)
   )

   success = True  # No action taken, so consider it successful
   # Create database if --setup is provided
   if args.setup:
      # Determine SQL file path
      sql_path = db_config.get('sql_file', './db/finia_draft.sql')
      sql_file = Path(sql_path)
      if not sql_file.exists():
         raise FileNotFoundError(f"SQL file not found at: {sql_file}")
      else:
         logger.info("Using SQL file: %s", sql_file)
         
         # Create database
         creator = DatabaseCreator(db)
         
         try:
            success = creator.create_from_file(str(sql_file))
         except Exception as e:
            logger.error("Error: %s", e)
            success = False
   else:
      logger.info("No '--setup' argument provided, skipping database creation.")

   # import of the initialization data
   if args.init_database:
      data_path = db_config.get('init_data', './test/data/data.yaml')
      data_file = Path(data_path)
      if not data_file.exists():
         raise FileNotFoundError(f"Data file not found at: {data_file}")
      else:
         logger.info("Using data file: %s", data_file)
         
         # Create importer
         importer = DataImporter(db)

         try:
            importer.import_data(str(data_file))
         except Exception as e:
            logger.error("Error: %s", e)
            success = False
   else:
      logger.info("No '--init-database' argument provided, skipping data import.")

   sys.exit(0 if success else 1)
