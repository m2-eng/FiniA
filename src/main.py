#!/usr/bin/env python3
"""
Database creation script for FiniA
Creates the database structure from the SQL dump file on a specified MySQL/MariaDB server.
Can also launch the GUI application.
"""

import sys
import argparse

from Database import Database
from DatabaseCreator import DatabaseCreator
from DataImporter import DataImporter
from services.account_data_importer import AccountDataImporter

from pathlib import Path
from utils import load_config


if __name__ == "__main__":
   """Main function with argument parsing"""
   # Argument parser setup
   parser = argparse.ArgumentParser(
      description='FiniA - Finanzverwaltungssystem (uses config.yaml for defaults)',
      formatter_class=argparse.RawDescriptionHelpFormatter,
      epilog="""
   Examples:
     python main.py --user root --password secret --setup
     python main.py -u dbuser -p dbpass --init-database
     python main.py --user root --password secret --config custom_config.yaml --import-account-data
     python main.py --api --user root --password secret --config cfg/config.yaml
  
   Note: Most parameters are read from config.yaml by default.
      Use command-line arguments to override config values.
      """
   )
   parser.add_argument('--user',
                       required=True,
                       help='MySQL user')
   parser.add_argument('--password',
                       required=True,
                       help='MySQL password')
   parser.add_argument('--config',
                       default='cfg/config.yaml',
                       help='Path to config file (default: cfg/config.yaml)')
   parser.add_argument('--init-database',
                       action="store_true",
                       help='Can be empty, used to initialize the database (see linked folders for each account)')
   parser.add_argument('--setup',
                       action="store_true",
                       help='Can be empty, used to create the database')
   parser.add_argument('--import-account-data',
                       action="store_true",
                       help='Import account transactions from CSV files based on tbl_accountImportPath')
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
   db_config = load_config(args.config)

   # Launch API server if requested
   if args.api:
      import uvicorn
      from api.dependencies import set_database_credentials
      
      print(f"Starting FiniA API server on http://{args.host}:{args.port}")
      print(f"API Documentation: http://{args.host}:{args.port}/api/docs")
      print(f"Web Interface: http://{args.host}:{args.port}/")
      
      # Set database credentials in dependencies module for API startup
      set_database_credentials(
         user=args.user,
         password=args.password,
         host=db_config.get('host', 'localhost'),
         name=db_config.get('name', 'FiniA'),
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

   db = Database(
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
         print(f"Using SQL file: {sql_file}")
         
         # Create database
         creator = DatabaseCreator(db)
         
         try:
            success = creator.create_from_file(str(sql_file))
         except Exception as e:
            print(f"Error: {e}")
            success = False
   else:
      print("No '--setup' argument provided, skipping database creation.")

   # import of the initialization data
   if args.init_database:
      data_path = db_config.get('init_data', './test/data/data.yaml')
      data_file = Path(data_path)
      if not data_file.exists():
         raise FileNotFoundError(f"Data file not found at: {data_file}")
      else:
         print(f"Using data file: {data_file}")
         
         # Create importer
         importer = DataImporter(db)

         try:
            importer.import_data(str(data_file))
         except Exception as e:
            print(f"Error: {e}")
            success = False
   else:
      print("No '--init-database' argument provided, skipping data import.")

   # import of account CSV data
   if args.import_account_data:
      try:
         csv_importer = AccountDataImporter(db)
         csv_importer.import_account_data()
      except Exception as e:
         print(f"Error: {e}")
         success = False
   else:
      print("No '--import-account-data' argument provided, skipping account CSV import.")
      
   sys.exit(0 if success else 1)
