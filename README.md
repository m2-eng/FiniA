# FiniA - Financial Assistant

## Overview

FiniA is a modern financial management tool for household and personal finance. It replaces complex Excel ledgers with a database-backed, web-based solution. Data import, visualization, and automation are core features.

## Features

- MariaDB/MySQL database backend
- Web API and browser-based UI
- Automated CSV transaction import
- Duplicate detection for incremental imports
- Grafana dashboard integration

## Installation

**Requirements:**
- Python 3.8+
- MariaDB or MySQL
- Grafana (optional)

**Steps:**
1. Clone the repository:
  ```bash
  git clone https://github.com/m2-eng/FiniA.git
  cd FiniA
  ```
2. Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
3. Configure your database connection in `cfg/config.yaml`.

## Usage

Start the API server and open the web UI:
```bash
python src/main.py --api --user <db_user> --password <db_pass>
```
- Web UI: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- API docs: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)

### Command-line options

```
--api                 Start API server (web UI)
--user <db_user>      Database user
--password <db_pass>  Database password
--setup               Create database schema
--init-database       Import initial configuration data
--config <file>       Path to config file
```

## Security Notice

Keep your database credentials secure. Do not share your config files or passwords.

## Contributing

Contributions are welcome! Please open issues or pull requests on GitHub.

## License

This project is licensed under the MIT License.

#### Combined Setup (All in One)

Run all steps together:

```bash
python main.py \
  --user root \
  --password your_password \
  --setup \
  --init-database
```

### Command-Line Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--user` | Yes | - | MySQL username |
| `--password` | Yes | - | MySQL password |
| `--config` | No | `config.yaml` | Path to configuration file |
| `--setup` | No | - | Create database schema from SQL dump |
| `--init-database` | No | - | Import initial data (account types, planning cycles, accounts) |

## CSV Import Formats

The system supports multiple CSV formats defined in `src/import_formats.yaml`:

### Currently Supported Formats

- **csv-cb**: Consorsbank format (semicolon-delimited, German decimal/date format)
- **csv-spk**: Sparkasse format (semicolon-delimited, German decimal/date format)
- **csv-mintos**: Mintos format (comma-delimited, international format)

Feel free to add more formats by editing `src/import_formats.yaml`.

### Configuring Import Paths

Import paths are configured in `test/data/data.yaml` under the `account_data` section:

```yaml
account_data:
  - account:
      name: 'Account Name'
      iban_accountNumber: 'DE89...'
      type: 'Girokonto'
      importFolder: ./test/data/FolderName
      importFileEnding: csv
      importType: csv-cb  # Format identifier from import_formats.yaml
```

The system will automatically:
1. Look for CSV files in the specified folder
2. Use the mapping from `import_formats.yaml` based on `importType`
3. Parse and import transactions with delta detection (duplicates are skipped)

## Architecture

The project follows a layered architecture for clean separation of concerns:

- **Domain Layer** (`src/domain/`): Business entities and domain models
- **Repository Layer** (`src/repositories/`): Data access and persistence
- **Service Layer** (`src/services/`): Business logic and orchestration
- **Infrastructure** (`src/infrastructure/`): Cross-cutting concerns (Unit of Work, etc.)

### Key Components

- `Database.py`: Database connection management
- `DatabaseCreator.py`: Schema initialization from SQL dump
- `DataImporter.py`: Initial configuration data import from YAML
- `services/account_data_importer.py`: CSV transaction import with format mapping
- `import_formats.yaml`: Centralized CSV format definitions
- `repositories/`: Data access layer with Repository pattern
- `infrastructure/unit_of_work.py`: Transaction management

## Project Structure

```
FiniA/
├── cfg/
│   └── config.yaml          # Database configuration
├── requirements.txt         # Python dependencies
├── db/
│   └── finia_draft.sql     # Database schema
├── src/
│   ├── main.py             # CLI entry point
│   ├── api/                # FastAPI application and routers
│   ├── web/                # Static web UI served by the API
│   ├── config/             # Theme and UI config for web
│   ├── import_formats.yaml # CSV format definitions
│   ├── domain/             # Domain models
│   ├── repositories/       # Data access layer
│   ├── services/           # Business logic
│   └── infrastructure/     # Cross-cutting concerns
└── test/
    └── data/               # Test data and CSV samples
```

## Security Notes

⚠️ **Important**: Never commit passwords or credentials to version control. Consider using:
- Configuration files (added to `.gitignore`)
- Environment variables
- Secret management tools

## Roadmap
See the Issues tab of this repository.

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

## [Licence](./LICENSE)
AGPL-3.0 license
