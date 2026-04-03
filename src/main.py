"""
CDMP – Command-line interface

Usage examples
--------------
Generate CSV templates from a SQL schema file::

    python -m src.main generate-csv sql/schema.sql --output-dir csv/

Apply the SQL schema to a MySQL database::

    python -m src.main apply-schema sql/schema.sql --database mydb

Insert CSV files into MySQL::

    python -m src.main insert-csv csv/ --database mydb

Do all three steps in one command::

    python -m src.main run sql/schema.sql --output-dir csv/ --database mydb
"""

import argparse
import os
import sys

from src.csv_generator import generate_csv_files
from src.mysql_loader import execute_sql_file, insert_csv_directory
from src.sql_parser import parse_sql_file_from_path


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------


def cmd_generate_csv(args: argparse.Namespace) -> None:
    """Parse *args.sql_file* and write CSV templates to *args.output_dir*."""
    tables = parse_sql_file_from_path(args.sql_file)
    if not tables:
        print(f"No CREATE TABLE statements found in {args.sql_file!r}.", file=sys.stderr)
        sys.exit(1)

    paths = generate_csv_files(
        tables,
        args.output_dir,
        include_auto_increment=args.include_auto_increment,
    )
    for path in paths:
        print(f"  Created: {path}")
    print(f"\n{len(paths)} CSV file(s) generated in {args.output_dir!r}.")


def cmd_apply_schema(args: argparse.Namespace) -> None:
    """Apply *args.sql_file* schema to MySQL."""
    print(f"Applying schema from {args.sql_file!r} to database {args.database!r} …")
    execute_sql_file(
        args.sql_file,
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
    )
    print("Schema applied successfully.")


def cmd_insert_csv(args: argparse.Namespace) -> None:
    """Insert all CSV files from *args.csv_dir* into MySQL."""
    print(f"Inserting CSV files from {args.csv_dir!r} into database {args.database!r} …")
    results = insert_csv_directory(
        args.csv_dir,
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        batch_size=args.batch_size,
    )
    total = sum(results.values())
    for table, count in results.items():
        print(f"  {table}: {count} row(s) inserted")
    print(f"\nTotal: {total} row(s) inserted across {len(results)} table(s).")


def cmd_run(args: argparse.Namespace) -> None:
    """Generate CSVs, apply schema, and insert data in one step."""
    # Step 1: Generate CSVs
    print("Step 1: Generating CSV files …")
    tables = parse_sql_file_from_path(args.sql_file)
    if not tables:
        print(f"No CREATE TABLE statements found in {args.sql_file!r}.", file=sys.stderr)
        sys.exit(1)
    paths = generate_csv_files(
        tables,
        args.output_dir,
        include_auto_increment=args.include_auto_increment,
    )
    for path in paths:
        print(f"  Created: {path}")

    # Step 2: Apply schema
    print("\nStep 2: Applying schema …")
    execute_sql_file(
        args.sql_file,
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
    )
    print("  Schema applied.")

    # Step 3: Insert CSVs
    print("\nStep 3: Inserting CSV data …")
    results = insert_csv_directory(
        args.output_dir,
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        batch_size=args.batch_size,
    )
    for table, count in results.items():
        print(f"  {table}: {count} row(s) inserted")

    total = sum(results.values())
    print(f"\nDone. {total} row(s) inserted across {len(results)} table(s).")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _db_args(parser: argparse.ArgumentParser) -> None:
    """Add shared MySQL connection arguments to *parser*."""
    parser.add_argument(
        "--host",
        default=os.getenv("MYSQL_HOST", "localhost"),
        help="MySQL host (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MYSQL_PORT", 3306)),
        help="MySQL port (default: %(default)s)",
    )
    parser.add_argument(
        "--user",
        default=os.getenv("MYSQL_USER", "root"),
        help="MySQL user (default: %(default)s)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("MYSQL_PASSWORD", ""),
        help="MySQL password (default: env MYSQL_PASSWORD)",
    )
    parser.add_argument(
        "--database",
        required=True,
        default=os.getenv("MYSQL_DATABASE"),
        help="Target MySQL database name",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="cdmp",
        description="CDMP – CSV/MySQL data migration helper",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- generate-csv ----
    p_gen = sub.add_parser(
        "generate-csv",
        help="Generate CSV template files from a SQL schema",
    )
    p_gen.add_argument("sql_file", help="Path to the SQL schema file")
    p_gen.add_argument(
        "--output-dir",
        default="csv",
        help="Directory for output CSV files (default: csv/)",
    )
    p_gen.add_argument(
        "--include-auto-increment",
        action="store_true",
        default=False,
        help="Include auto-increment columns in the CSV header",
    )
    p_gen.set_defaults(func=cmd_generate_csv)

    # ---- apply-schema ----
    p_schema = sub.add_parser(
        "apply-schema",
        help="Apply a SQL schema file to MySQL",
    )
    p_schema.add_argument("sql_file", help="Path to the SQL schema file")
    _db_args(p_schema)
    p_schema.set_defaults(func=cmd_apply_schema)

    # ---- insert-csv ----
    p_ins = sub.add_parser(
        "insert-csv",
        help="Insert CSV files from a directory into MySQL",
    )
    p_ins.add_argument("csv_dir", help="Directory containing .csv files")
    p_ins.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Rows per INSERT batch (default: 500)",
    )
    _db_args(p_ins)
    p_ins.set_defaults(func=cmd_insert_csv)

    # ---- run (all-in-one) ----
    p_run = sub.add_parser(
        "run",
        help="Generate CSVs, apply schema, and insert data in one step",
    )
    p_run.add_argument("sql_file", help="Path to the SQL schema file")
    p_run.add_argument(
        "--output-dir",
        default="csv",
        help="Directory for CSV files (default: csv/)",
    )
    p_run.add_argument(
        "--include-auto-increment",
        action="store_true",
        default=False,
        help="Include auto-increment columns in the CSV header",
    )
    p_run.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Rows per INSERT batch (default: 500)",
    )
    _db_args(p_run)
    p_run.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
