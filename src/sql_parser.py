"""
SQL DDL parser that extracts table definitions and column information
from CREATE TABLE statements.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ColumnDefinition:
    """Represents a single column definition parsed from a SQL CREATE TABLE statement."""

    name: str
    data_type: str
    nullable: bool = True
    default: Optional[str] = None
    primary_key: bool = False
    auto_increment: bool = False


@dataclass
class TableDefinition:
    """Represents a table definition parsed from a SQL CREATE TABLE statement."""

    name: str
    columns: list[ColumnDefinition] = field(default_factory=list)

    def column_names(self) -> list[str]:
        """Return a list of column names, excluding auto-increment primary keys."""
        return [
            col.name
            for col in self.columns
            if not col.auto_increment
        ]

    def all_column_names(self) -> list[str]:
        """Return all column names including auto-increment columns."""
        return [col.name for col in self.columns]


# Regex patterns
_CREATE_TABLE_PATTERN = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)

_COLUMN_PATTERN = re.compile(
    r"^\s*`?(\w+)`?\s+(\w+(?:\s*\([^)]*\))?)"
    r"(.*?)$",
    re.IGNORECASE,
)

# Tokens that indicate a line is a table constraint, not a column definition
_CONSTRAINT_KEYWORDS = re.compile(
    r"^\s*(PRIMARY\s+KEY|UNIQUE|INDEX|KEY|CONSTRAINT|CHECK|FOREIGN\s+KEY)",
    re.IGNORECASE,
)


def _parse_column(line: str) -> Optional[ColumnDefinition]:
    """Parse a single column definition line.

    Returns a :class:`ColumnDefinition` or ``None`` if the line is not a
    column definition (e.g. a table-level constraint).
    """
    line = line.strip().rstrip(",")
    if not line or _CONSTRAINT_KEYWORDS.match(line):
        return None

    match = _COLUMN_PATTERN.match(line)
    if not match:
        return None

    name = match.group(1)
    data_type = match.group(2).strip()
    rest = match.group(3)

    nullable = "NOT NULL" not in rest.upper()
    auto_increment = "AUTO_INCREMENT" in rest.upper()
    primary_key = "PRIMARY KEY" in rest.upper()

    default_value: Optional[str] = None
    default_match = re.search(r"DEFAULT\s+(\S+)", rest, re.IGNORECASE)
    if default_match:
        default_value = default_match.group(1).strip("'\"")

    return ColumnDefinition(
        name=name,
        data_type=data_type,
        nullable=nullable,
        default=default_value,
        primary_key=primary_key,
        auto_increment=auto_increment,
    )


def parse_sql_file(sql_content: str) -> list[TableDefinition]:
    """Parse all CREATE TABLE statements from the given SQL content.

    Args:
        sql_content: The full text of a SQL file.

    Returns:
        A list of :class:`TableDefinition` objects, one per CREATE TABLE
        statement found in the input.
    """
    tables: list[TableDefinition] = []

    for match in _CREATE_TABLE_PATTERN.finditer(sql_content):
        table_name = match.group(1)
        body = match.group(2)

        table = TableDefinition(name=table_name)
        for line in body.splitlines():
            col = _parse_column(line)
            if col is not None:
                table.columns.append(col)

        tables.append(table)

    return tables


def parse_sql_file_from_path(path: str) -> list[TableDefinition]:
    """Parse CREATE TABLE statements from a SQL file at *path*.

    Args:
        path: Path to the ``.sql`` file.

    Returns:
        A list of :class:`TableDefinition` objects.
    """
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    return parse_sql_file(content)
