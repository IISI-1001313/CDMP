"""Tests for src.sql_parser"""

import pytest

from src.sql_parser import (
    ColumnDefinition,
    TableDefinition,
    parse_sql_file,
    parse_sql_file_from_path,
)


SIMPLE_SQL = """
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    age INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

MULTI_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock INT DEFAULT 0
);

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    status VARCHAR(20) DEFAULT 'pending'
);
"""

BACKTICK_SQL = """
CREATE TABLE `my_table` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `col1` VARCHAR(255) NOT NULL,
    `col2` TEXT
);
"""

CONSTRAINT_SQL = """
CREATE TABLE employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department_id INT,
    UNIQUE (name),
    KEY idx_dept (department_id),
    FOREIGN KEY (department_id) REFERENCES departments(id)
);
"""


class TestParseSqlFile:
    def test_single_table_returns_one_table(self):
        tables = parse_sql_file(SIMPLE_SQL)
        assert len(tables) == 1

    def test_table_name(self):
        tables = parse_sql_file(SIMPLE_SQL)
        assert tables[0].name == "users"

    def test_column_count(self):
        tables = parse_sql_file(SIMPLE_SQL)
        # id, username, email, age, created_at
        assert len(tables[0].columns) == 5

    def test_auto_increment_column(self):
        tables = parse_sql_file(SIMPLE_SQL)
        id_col = tables[0].columns[0]
        assert id_col.name == "id"
        assert id_col.auto_increment is True
        assert id_col.primary_key is True

    def test_not_null_column(self):
        tables = parse_sql_file(SIMPLE_SQL)
        username_col = tables[0].columns[1]
        assert username_col.name == "username"
        assert username_col.nullable is False

    def test_nullable_column(self):
        tables = parse_sql_file(SIMPLE_SQL)
        age_col = tables[0].columns[3]
        assert age_col.name == "age"
        assert age_col.nullable is True

    def test_default_value(self):
        tables = parse_sql_file(SIMPLE_SQL)
        created_col = tables[0].columns[4]
        assert created_col.name == "created_at"
        assert created_col.default == "CURRENT_TIMESTAMP"

    def test_multiple_tables(self):
        tables = parse_sql_file(MULTI_TABLE_SQL)
        assert len(tables) == 2
        assert {t.name for t in tables} == {"products", "orders"}

    def test_if_not_exists(self):
        tables = parse_sql_file(MULTI_TABLE_SQL)
        products = next(t for t in tables if t.name == "products")
        assert len(products.columns) == 4

    def test_backtick_names(self):
        tables = parse_sql_file(BACKTICK_SQL)
        assert len(tables) == 1
        assert tables[0].name == "my_table"
        assert [c.name for c in tables[0].columns] == ["id", "col1", "col2"]

    def test_constraint_lines_ignored(self):
        tables = parse_sql_file(CONSTRAINT_SQL)
        assert len(tables) == 1
        # Only real columns: id, name, department_id
        col_names = [c.name for c in tables[0].columns]
        assert col_names == ["id", "name", "department_id"]

    def test_empty_string_returns_empty_list(self):
        assert parse_sql_file("") == []

    def test_no_create_table_returns_empty_list(self):
        assert parse_sql_file("SELECT 1; INSERT INTO foo VALUES (1);") == []


class TestTableDefinition:
    def setup_method(self):
        self.table = parse_sql_file(SIMPLE_SQL)[0]

    def test_column_names_excludes_auto_increment(self):
        names = self.table.column_names()
        assert "id" not in names
        assert "username" in names

    def test_all_column_names_includes_auto_increment(self):
        names = self.table.all_column_names()
        assert "id" in names

    def test_all_column_names_order(self):
        names = self.table.all_column_names()
        assert names == ["id", "username", "email", "age", "created_at"]


class TestParseSqlFileFromPath:
    def test_reads_file(self, tmp_path):
        sql_file = tmp_path / "test.sql"
        sql_file.write_text(SIMPLE_SQL, encoding="utf-8")
        tables = parse_sql_file_from_path(str(sql_file))
        assert len(tables) == 1
        assert tables[0].name == "users"
