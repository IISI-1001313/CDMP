"""Tests for src.main (CLI)"""

import csv
import os

import pytest

from src.main import build_parser, cmd_generate_csv


SIMPLE_SQL = """
CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100)
);
"""


class TestBuildParser:
    def test_generate_csv_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["generate-csv", "schema.sql", "--output-dir", "out/"])
        assert args.sql_file == "schema.sql"
        assert args.output_dir == "out/"
        assert args.include_auto_increment is False

    def test_generate_csv_include_auto_increment_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "generate-csv", "schema.sql", "--include-auto-increment"
        ])
        assert args.include_auto_increment is True

    def test_insert_csv_subcommand(self):
        parser = build_parser()
        args = parser.parse_args([
            "insert-csv", "csv/",
            "--database", "mydb",
            "--batch-size", "200",
        ])
        assert args.csv_dir == "csv/"
        assert args.database == "mydb"
        assert args.batch_size == 200

    def test_apply_schema_subcommand(self):
        parser = build_parser()
        args = parser.parse_args([
            "apply-schema", "schema.sql",
            "--database", "mydb",
            "--host", "db.example.com",
        ])
        assert args.sql_file == "schema.sql"
        assert args.host == "db.example.com"

    def test_run_subcommand(self):
        parser = build_parser()
        args = parser.parse_args([
            "run", "schema.sql",
            "--output-dir", "csv/",
            "--database", "mydb",
        ])
        assert args.sql_file == "schema.sql"
        assert args.output_dir == "csv/"
        assert args.database == "mydb"


class TestCmdGenerateCsv:
    def test_generates_csv_files(self, tmp_path):
        sql_file = tmp_path / "schema.sql"
        sql_file.write_text(SIMPLE_SQL, encoding="utf-8")
        output_dir = str(tmp_path / "csv")

        parser = build_parser()
        args = parser.parse_args([
            "generate-csv", str(sql_file), "--output-dir", output_dir
        ])
        cmd_generate_csv(args)

        assert os.path.exists(os.path.join(output_dir, "customers.csv"))

    def test_generated_csv_has_correct_header(self, tmp_path):
        sql_file = tmp_path / "schema.sql"
        sql_file.write_text(SIMPLE_SQL, encoding="utf-8")
        output_dir = str(tmp_path / "csv")

        parser = build_parser()
        args = parser.parse_args([
            "generate-csv", str(sql_file), "--output-dir", output_dir
        ])
        cmd_generate_csv(args)

        csv_path = os.path.join(output_dir, "customers.csv")
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == ["name", "email"]

    def test_exits_on_empty_sql(self, tmp_path):
        sql_file = tmp_path / "empty.sql"
        sql_file.write_text("-- no tables here", encoding="utf-8")
        output_dir = str(tmp_path / "csv")

        parser = build_parser()
        args = parser.parse_args([
            "generate-csv", str(sql_file), "--output-dir", output_dir
        ])
        with pytest.raises(SystemExit):
            cmd_generate_csv(args)
