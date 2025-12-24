# Financial Assistant (FiniA)

## Overview

Financial Assistant (FiniA) replaces an advanced Excel-based household ledger. Built on MariaDB for data storage, uses Grafana for visualization, and Python scripts for automated data import. Future plans include AI integration for smart insights and predictive analytics.

## Features

- **Database**: Built on MariaDB with layered architecture (Domain, Repository, Service layers)
- **Visualization**: Grafana dashboard for financial insights
- **Data Import**: Automated Python scripts for CSV transaction imports from multiple bank formats
- **Flexible Configuration**: Centralized format definitions supporting Consorsbank, Sparkasse, Mintos, and extensible to other formats
- **Delta Imports**: Automatic duplicate detection for incremental data loads
- **Future Roadmap**: AI-powered analytics and recommendations

## Installation

### Prerequisites

- Python 3.8 or higher
- MariaDB or MySQL server
- Grafana (for visualization)
- Required Python packages (see requirements.txt)

### Steps

1. Clone the repository:
```bash
git clone https://github.com/m2-eng/FiniA.git
cd FiniA
```

2. Install dependencies:
```bash
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Configure database connection in `config.yaml`

## Usage

### Database Setup

Navigate to the src directory:
```bash
cd src
```

#### 1. Create Database Schema

Create the database structure from SQL dump file:

```bash
python main.py --user root --password your_password --setup
```

#### 2. Import Initial Configuration Data

Import account types, planning cycles, and account metadata:

```bash
python main.py --user root --password your_password --init-database
```

#### 3. Import Account Transaction Data

Import transactions from CSV files (requires accounts configured with import paths):

```bash
python main.py --user root --password your_password --import-account-data
```

#### Combined Setup (All in One)

Run all steps together:

```bash
python main.py \
  --user root \
  --password your_password \
  --setup \
  --init-database \
  --import-account-data
```

### Command-Line Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--user` | Yes | - | MySQL username |
| `--password` | Yes | - | MySQL password |
| `--config` | No | `config.yaml` | Path to configuration file |
| `--setup` | No | - | Create database schema from SQL dump |
| `--init-database` | No | - | Import initial data (account types, planning cycles, accounts) |
| `--import-account-data` | No | - | Import CSV transaction data for configured accounts |

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
├── config.yaml              # Database configuration
├── requirements.txt         # Python dependencies
├── db/
│   └── finia_draft.sql     # Database schema
├── src/
│   ├── main.py             # CLI entry point
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
