# CDMP – CSV / MySQL Data Migration Pipeline

CDMP is a lightweight Python command-line tool that lets you:

1. **Parse** a SQL schema file (`CREATE TABLE` statements).
2. **Generate** CSV template files whose headers match the table columns.
3. **Apply** the SQL schema to a MySQL database.
4. **Insert** CSV data into MySQL in efficient batches.

---

## Requirements

- Python ≥ 3.10
- MySQL server (for the `apply-schema` and `insert-csv` commands)

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## Project layout

```
CDMP/
├── sql/
│   └── schema.sql          # Example SQL schema file
├── csv/                    # Generated CSV files (created at runtime)
├── src/
│   ├── sql_parser.py       # Parse CREATE TABLE statements
│   ├── csv_generator.py    # Generate CSV files from parsed tables
│   ├── mysql_loader.py     # Execute SQL files & bulk-insert CSVs
│   └── main.py             # CLI entry point
├── tests/
│   ├── test_sql_parser.py
│   ├── test_csv_generator.py
│   └── test_main.py
├── requirements.txt
└── README.md
```

---

## Usage

### Generate CSV template files from a SQL schema

```bash
python -m src.main generate-csv sql/schema.sql --output-dir csv/
```

Each `CREATE TABLE` statement produces one CSV file named `<table>.csv` with a
header row derived from the table's non-auto-increment columns.

Options:

| Flag | Default | Description |
|---|---|---|
| `--output-dir` | `csv/` | Directory for generated CSVs |
| `--include-auto-increment` | off | Include auto-increment columns in the header |

---

### Apply a SQL schema to MySQL

```bash
python -m src.main apply-schema sql/schema.sql \
    --host localhost --port 3306 \
    --user root --password secret \
    --database mydb
```

Connection parameters can also be supplied via environment variables:

```
MYSQL_HOST      (default: localhost)
MYSQL_PORT      (default: 3306)
MYSQL_USER      (default: root)
MYSQL_PASSWORD  (default: "")
MYSQL_DATABASE
```

---

### Insert CSV files into MySQL

```bash
python -m src.main insert-csv csv/ --database mydb
```

Every `<table>.csv` file in the directory is inserted into the table whose name
matches the file stem.  The CSV **must** have a header row whose column names
match the target table.

Options:

| Flag | Default | Description |
|---|---|---|
| `--batch-size` | `500` | Rows per `INSERT` batch |

---

### All-in-one: generate CSVs → apply schema → insert data

```bash
python -m src.main run sql/schema.sql \
    --output-dir csv/ \
    --database mydb
```

---

## Running tests

```bash
python -m pytest tests/ -v
```

---

## SQL schema example

```sql
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    age INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

Running `generate-csv` against the above produces `users.csv`:

```csv
username,email,age,created_at
```

Fill in the rows, then run `insert-csv` to load the data into MySQL.