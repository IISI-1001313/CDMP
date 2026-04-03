"""
Utilities for generating CSV files from SQL table definitions.
"""

import csv
import os
from pathlib import Path

from src.sql_parser import TableDefinition


def generate_csv(
    table: TableDefinition,
    output_dir: str,
    rows: list[dict] | None = None,
    include_auto_increment: bool = False,
) -> str:
    """Generate a CSV file for *table* in *output_dir*.

    The CSV header is derived from the table's column definitions.  If *rows*
    is provided the data is written to the file; otherwise only the header row
    is written (useful for creating an empty template).

    Args:
        table: The :class:`~src.sql_parser.TableDefinition` to generate a CSV
            for.
        output_dir: Directory where the CSV file will be saved.  It will be
            created if it does not exist.
        rows: Optional list of dicts mapping column name → value.  Missing
            columns are written as empty strings.
        include_auto_increment: When *False* (default), auto-increment columns
            are omitted from the CSV header because their values are assigned
            by the database.

    Returns:
        The absolute path to the generated CSV file.
    """
    os.makedirs(output_dir, exist_ok=True)

    if include_auto_increment:
        columns = table.all_column_names()
    else:
        columns = table.column_names()

    output_path = str(Path(output_dir) / f"{table.name}.csv")

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=columns,
            extrasaction="ignore",
        )
        writer.writeheader()

        if rows:
            for row in rows:
                writer.writerow({col: row.get(col, "") for col in columns})

    return output_path


def generate_csv_files(
    tables: list[TableDefinition],
    output_dir: str,
    data: dict[str, list[dict]] | None = None,
    include_auto_increment: bool = False,
) -> list[str]:
    """Generate CSV files for each table in *tables*.

    Args:
        tables: List of :class:`~src.sql_parser.TableDefinition` objects.
        output_dir: Directory where CSV files will be saved.
        data: Optional mapping of table name → list of row dicts.
        include_auto_increment: Passed through to :func:`generate_csv`.

    Returns:
        List of paths to the generated CSV files.
    """
    data = data or {}
    paths: list[str] = []
    for table in tables:
        path = generate_csv(
            table,
            output_dir,
            rows=data.get(table.name),
            include_auto_increment=include_auto_increment,
        )
        paths.append(path)
    return paths
