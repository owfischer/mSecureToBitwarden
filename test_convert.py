import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

#from convert import map_msecure_field_type_to_bitwarden, parse_msecure_csv
import convert


@pytest.mark.parametrize(
    ("msecure_type", "expected_type"),
    [
        (7, 0),
        (10, 0),
        (12, 0),
        (8, 1),
        (9, 1),
        (999, 0),
    ],
)
def test_map_msecure_field_type_to_bitwarden(msecure_type, expected_type):
    assert convert.map_msecure_field_type_to_bitwarden(msecure_type) == expected_type


@pytest.fixture
def sample_csv_rows():
    return [
        [
            "Entry One|1234",
            "Login",
            "FolderA",
            "First line\\nSecond line",
            "URL|2|https://example.com",
            "Benutzername|7|johndoe",
            "Passwort|8|secret",
            "Note with comma|0|hello, world",
        ],
        [
            "Entry Two |with pipe|5678",
            "Anmelden",
            "FolderB",
            "",
            "Website|2|https://two.example.com",
            "Kennwort|8|secret2",
        ],
    ]


def test_parse_name_id_returns_name_only(sample_csv_rows):
    name_id = convert.parse_name_id(sample_csv_rows[0])
    assert name_id == "Entry One"


def test_parse_name_id_returns_name_only_with_pipe(sample_csv_rows):
    name_id = convert.parse_name_id(sample_csv_rows[1])
    assert name_id == "Entry Two |with pipe"


def test_parse_type_returns_type(sample_csv_rows):
    type_value = convert.parse_type(sample_csv_rows[1])
    assert type_value == "Anmelden"


def test_parse_folder_returns_folder(sample_csv_rows):
    folder = convert.parse_folder(sample_csv_rows[0])
    assert folder == "FolderA"


def test_parse_note_returns_empty_note(sample_csv_rows):
    row = sample_csv_rows[1]
    notes = convert.parse_note(row)
    assert notes == ""


def test_parse_note_returns_multiline_note(sample_csv_rows):
    row = sample_csv_rows[0]
    notes = convert.parse_note(row)
    assert notes == "First line\nSecond line"   


def test_parse_msecure_csv_returns_record_dicts(tmp_path, sample_csv_rows):
    csv_path = tmp_path / "sample.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerows(sample_csv_rows)

    records = convert.parse_msecure_csv(csv_path)

    assert isinstance(records, list)
    assert len(records) == 2

    first = records[0]
    assert first["name"] == "Entry One"
    assert first["type"] == "Login"
    assert first["folder"] == "FolderA"
    assert first["notes"] == "First line\nSecond line"
    assert first["raw"][4] == "URL|2|https://example.com"
    assert first["raw"][5] == "Benutzername|7|johndoe"
    assert first["raw"][6] == "Passwort|8|secret"
    assert first["raw"][7] == "Note with comma|0|hello, world"

    second = records[1]
    assert second["name"] == "Entry Two |with pipe"
    assert second["type"] == "Anmelden"
    assert second["folder"] == "FolderB"
    assert second["notes"] == ""
    assert second["raw"][4] == "Website|2|https://two.example.com"
    assert second["raw"][5] == "Kennwort|8|secret2"


