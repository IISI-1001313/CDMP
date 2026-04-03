"""Tests for src.csv_generator"""

import csv
import os

import pytest

from src.csv_generator import generate_csv, generate_csv_files
from src.sql_parser import parse_sql_file


SIMPLE_SQL = """
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    age INT
);
"""

MULTI_TABLE_SQL = """
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL
);

CREATE TABLE tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    label VARCHAR(50) NOT NULL
);
"""


class TestGenerateCsv:
    def test_creates_file(self, tmp_path):
        table = parse_sql_file(SIMPLE_SQL)[0]
        path = generate_csv(table, str(tmp_path))
        assert os.path.exists(path)

    def test_file_named_after_table(self, tmp_path):
        table = parse_sql_file(SIMPLE_SQL)[0]
        path = generate_csv(table, str(tmp_path))
        assert os.path.basename(path) == "users.csv"

    def test_header_excludes_auto_increment_by_default(self, tmp_path):
        table = parse_sql_file(SIMPLE_SQL)[0]
        path = generate_csv(table, str(tmp_path))
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == ["username", "email", "age"]

    def test_header_includes_auto_increment_when_requested(self, tmp_path):
        table = parse_sql_file(SIMPLE_SQL)[0]
        path = generate_csv(table, str(tmp_path), include_auto_increment=True)
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == ["id", "username", "email", "age"]

    def test_empty_template_has_only_header(self, tmp_path):
        table = parse_sql_file(SIMPLE_SQL)[0]
        path = generate_csv(table, str(tmp_path))
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 1  # header only

    def test_rows_written_correctly(self, tmp_path):
        table = parse_sql_file(SIMPLE_SQL)[0]
        data = [
            {"username": "alice", "email": "alice@example.com", "age": "30"},
            {"username": "bob", "email": "bob@example.com", "age": "25"},
        ]
        path = generate_csv(table, str(tmp_path), rows=data)
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            written = list(reader)
        assert len(written) == 2
        assert written[0]["username"] == "alice"
        assert written[1]["email"] == "bob@example.com"

    def test_missing_row_values_written_as_empty(self, tmp_path):
        table = parse_sql_file(SIMPLE_SQL)[0]
        data = [{"username": "alice"}]  # missing email and age
        path = generate_csv(table, str(tmp_path), rows=data)
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["email"] == ""
        assert row["age"] == ""

    def test_output_dir_created_if_missing(self, tmp_path):
        new_dir = str(tmp_path / "subdir" / "nested")
        table = parse_sql_file(SIMPLE_SQL)[0]
        generate_csv(table, new_dir)
        assert os.path.isdir(new_dir)

    def test_returns_path_string(self, tmp_path):
        table = parse_sql_file(SIMPLE_SQL)[0]
        path = generate_csv(table, str(tmp_path))
        assert isinstance(path, str)


class TestGenerateCsvFiles:
    def test_generates_one_file_per_table(self, tmp_path):
        tables = parse_sql_file(MULTI_TABLE_SQL)
        paths = generate_csv_files(tables, str(tmp_path))
        assert len(paths) == 2

    def test_filenames_match_table_names(self, tmp_path):
        tables = parse_sql_file(MULTI_TABLE_SQL)
        paths = generate_csv_files(tables, str(tmp_path))
        basenames = {os.path.basename(p) for p in paths}
        assert basenames == {"products.csv", "tags.csv"}

    def test_data_dict_used_per_table(self, tmp_path):
        tables = parse_sql_file(MULTI_TABLE_SQL)
        data = {
            "products": [{"name": "Widget", "price": "9.99"}],
            "tags": [{"label": "sale"}],
        }
        paths = generate_csv_files(tables, str(tmp_path), data=data)
        for path in paths:
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            assert len(rows) == 1

    def test_returns_list_of_paths(self, tmp_path):
        tables = parse_sql_file(MULTI_TABLE_SQL)
        paths = generate_csv_files(tables, str(tmp_path))
        assert isinstance(paths, list)
        for p in paths:
            assert isinstance(p, str)
