"""
Utilities for loading CSV files into a MySQL database.

MySQL connection parameters are accepted either as keyword arguments or read
from the following environment variables:

    MYSQL_HOST      (default: localhost)
    MYSQL_PORT      (default: 3306)
    MYSQL_USER      (default: root)
    MYSQL_PASSWORD  (default: empty string)
    MYSQL_DATABASE  (required when not passed as an argument)
"""

import csv
import os
from pathlib import Path
from typing import Any

import mysql.connector
from mysql.connector import MySQLConnection


def _get_connection(
    host: str | None = None,
    port: int | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
) -> MySQLConnection:
    """Create and return a MySQL connection.

    Parameters fall back to the corresponding environment variables when not
    supplied.
    """
    return mysql.connector.connect(
        host=host or os.getenv("MYSQL_HOST", "localhost"),
        port=int(port or os.getenv("MYSQL_PORT", 3306)),
        user=user or os.getenv("MYSQL_USER", "root"),
        password=password or os.getenv("MYSQL_PASSWORD", ""),
        database=database or os.environ["MYSQL_DATABASE"],
    )


def execute_sql_file(
    sql_path: str,
    host: str | None = None,
    port: int | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
) -> None:
    """Execute all statements in *sql_path* against a MySQL database.

    This is typically used to apply a schema before loading data.

    Args:
        sql_path: Path to the ``.sql`` file to execute.
        host: MySQL host.
        port: MySQL port.
        user: MySQL user.
        password: MySQL password.
        database: Target database name.
    """
    with open(sql_path, "r", encoding="utf-8") as fh:
        sql_content = fh.read()

    conn = _get_connection(host, port, user, password, database)
    cursor = conn.cursor()
    try:
        for statement in sql_content.split(";"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def insert_csv_into_table(
    csv_path: str,
    table_name: str,
    host: str | None = None,
    port: int | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    batch_size: int = 500,
) -> int:
    """Insert rows from a CSV file into *table_name*.

    The CSV file must have a header row whose column names match the target
    table's columns.  Any columns present in the CSV but absent from the table
    are silently ignored by the ``INSERT`` statement.

    Args:
        csv_path: Path to the CSV file to load.
        table_name: Name of the destination table.
        host: MySQL host.
        port: MySQL port.
        user: MySQL user.
        password: MySQL password.
        database: Target database name.
        batch_size: Number of rows to insert per round-trip.

    Returns:
        Total number of rows inserted.
    """
    conn = _get_connection(host, port, user, password, database)
    cursor = conn.cursor()
    total_inserted = 0

    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            if reader.fieldnames is None:
                raise ValueError(f"CSV file {csv_path!r} has no header row.")
            columns = list(reader.fieldnames)

            placeholders = ", ".join(["%s"] * len(columns))
            col_list = ", ".join(f"`{c}`" for c in columns)
            sql = (
                f"INSERT INTO `{table_name}` ({col_list}) "
                f"VALUES ({placeholders})"
            )

            batch: list[tuple[Any, ...]] = []
            for row in reader:
                values = tuple(
                    None if row[c] == "" else row[c] for c in columns
                )
                batch.append(values)
                if len(batch) >= batch_size:
                    cursor.executemany(sql, batch)
                    total_inserted += len(batch)
                    batch = []

            if batch:
                cursor.executemany(sql, batch)
                total_inserted += len(batch)

        conn.commit()
    finally:
        cursor.close()
        conn.close()

    return total_inserted


def insert_csv_directory(
    csv_dir: str,
    host: str | None = None,
    port: int | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    batch_size: int = 500,
) -> dict[str, int]:
    """Insert all CSV files found in *csv_dir* into MySQL tables.

    Each CSV file ``<table_name>.csv`` is inserted into the table whose name
    matches the file stem.

    Args:
        csv_dir: Directory containing ``.csv`` files.
        host: MySQL host.
        port: MySQL port.
        user: MySQL user.
        password: MySQL password.
        database: Target database name.
        batch_size: Number of rows to insert per round-trip.

    Returns:
        A dict mapping table name → number of rows inserted.
    """
    results: dict[str, int] = {}
    for csv_file in sorted(Path(csv_dir).glob("*.csv")):
        table_name = csv_file.stem
        count = insert_csv_into_table(
            str(csv_file),
            table_name,
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            batch_size=batch_size,
        )
        results[table_name] = count
    return results
