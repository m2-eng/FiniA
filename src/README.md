# FiniA Database Setup

This directory contains the database creation script for the FiniA project.

## Installation

Install the required dependencies:

```bash
python3 -m pip install --upgrade pip
pip install -r ./requirements.txt
```

## Usage
### Basic Usage

Create the database on localhost with default settings:

```bash
python create_database.py --user root --password your_password
```

### Using a specific Config File

Specify a different config file:

```bash
python create_database.py \
  --user root \
  --password secret \
  --config /path/to/config.yaml
```

## Command-Line Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--user` | `-u` | Yes | - | MySQL username |
| `--password` | `-p` | Yes | - | MySQL password |
| `--config` | `-c` | No | `../config.yaml` | Path to configuration file |

## Features

- Automatically creates database if it doesn't exist
- Progress indicator for long-running operations
- Detailed logging and error messages
- Handles MySQL-specific comments and commands
- UTF-8 encoding support

## Requirements

- Python 3.6 or higher
- MySQL or MariaDB server
- see also requirements.txt 

## Security Notes

⚠️ **Important**: Never commit passwords or credentials to version control. Consider using:
- Configuration files (added to `.gitignore`)
- Secret management tools
