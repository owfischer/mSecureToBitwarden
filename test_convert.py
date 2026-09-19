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


def test_parse_name_id_handles_quotes_in_name():
    row = ["Entry ""Three""|9999", "Login", "FolderC", "Notes"]
    name_id = convert.parse_name_id(row)
    assert name_id == "Entry ""Three"""
    #assert name_id == "Entry \"Three\"" # convert mSecure export format "" to \" for json format

def test_parse_name_id_returns_empty_for_invalid_row():
    name_id = convert.parse_name_id([])
    assert name_id == ""


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


def test_parse_fields_returns_field_definitions(sample_csv_rows):
    row = sample_csv_rows[0]
    fields = convert.parse_fields(row)
    assert isinstance(fields, list)
    assert len(fields) == 4
    assert fields[0] == {"name": "URL", "type": 2, "value": "https://example.com"}
    assert fields[1] == {"name": "Benutzername", "type": 7, "value": "johndoe"}
    assert fields[2] == {"name": "Passwort", "type": 8, "value": "secret"}
    assert fields[3] == {"name": "Note with comma", "type": 0, "value": "hello, world"}


def test_parse_fields_handles_invalid_type(sample_csv_rows):
    row = sample_csv_rows[0]
    # Modify the type of the first field to be a non-integer string
    row[4] = "URL|invalid_type|https://example.com"
    fields = convert.parse_fields(row)
    assert len(fields) == 4
    assert fields[0] == {"name": "URL", "type": 0, "value": "https://example.com"}  # Default to text (0)


def  test_parse_fields_handles_passwords_with_backslashes(sample_csv_rows): 
    row = sample_csv_rows[0]
    # Modify the password field to include backslashes
    row[6] = r"Passwort|8|pa\5s\word"   # r"..." => raw-String
    fields = convert.parse_fields(row)
    assert len(fields) == 4
    assert fields[2] == {"name": "Passwort", "type": 8, "value": "pa\\5s\\word"}  # Value retains backslashes


def test_parse_fields_handles_missing_value(sample_csv_rows):
    row = sample_csv_rows[0]
    # Modify the first field to have a missing value
    row[4] = "URL|2|"
    fields = convert.parse_fields(row)
    assert len(fields) == 4
    assert fields[0] == {"name": "URL", "type": 2, "value": ""}  # Value is empty string


def test_parse_fields_handles_missing_type(sample_csv_rows):
    row = sample_csv_rows[0]
    # Modify the first field to have a missing type
    row[4] = "URL||https://example.com"
    fields = convert.parse_fields(row)
    assert len(fields) == 4
    assert fields[0] == {"name": "URL", "type": 0, "value": "https://example.com"}  # Default to text (0)


def test_parse_fields_handles_missing_name(sample_csv_rows):
    row = sample_csv_rows[0]
    # Modify the first field to have a missing name
    row[4] = "|2|https://example.com"
    fields = convert.parse_fields(row)
    assert len(fields) == 4
    assert fields[0] == {"name": "", "type": 2, "value": "https://example.com"}  # Name is empty string


def test_parse_fields_handles_invalid_format(sample_csv_rows):
    row = sample_csv_rows[0]
    # Modify the first field to have an invalid format (missing type and value)
    row[4] = "URL|2"
    fields = convert.parse_fields(row)
    assert len(fields) == 3  # Only 3 valid fields should be parsed


def test_parse_fields_handles_empty_row():
    row = []
    fields = convert.parse_fields(row)
    assert fields == []  # No fields should be parsed from an empty row


def test_parse_fields_handles_no_field_definitions(sample_csv_rows):
    row = sample_csv_rows[1]  # This row has only 2 field definitions
    fields = convert.parse_fields(row)
    assert len(fields) == 2
    assert fields[0] == {"name": "Website", "type": 2, "value": "https://two.example.com"}
    assert fields[1] == {"name": "Kennwort", "type": 8, "value": "secret2"}


def test_parse_row_returns_record_dict(sample_csv_rows):
    row = sample_csv_rows[0]
    record = convert.parse_row(row)
    assert isinstance(record, dict)
    assert record["raw"] == row
    assert record["name"] == "Entry One"
    assert record["type"] == "Login"
    assert record["folder"] == "FolderA"
    assert record["notes"] == "First line\nSecond line"
    assert record["fields"][1]["value"] == "johndoe"


def test_parse_row_handles_missing_columns():
    row = ["Entry Three|9999", "Login"]
    record = convert.parse_row(row)
    assert isinstance(record, dict)
    assert record["raw"] == row
    assert record["name"] == "Entry Three"
    assert record["type"] == "Login"
    assert record["folder"] == ""
    assert record["notes"] == ""
    assert record["fields"] == []


def test_parse_row_handles_empty_row():
    row = []
    record = convert.parse_row(row)
    assert isinstance(record, dict)
    assert record["raw"] == row
    assert record["name"] == ""
    assert record["type"] == ""
    assert record["folder"] == ""
    assert record["notes"] == ""
    assert record["fields"] == []


def test_parse_row_handles_missing_fields():
    row = ["Entry Four|8888", "Login", "FolderC", "Some notes"]
    record = convert.parse_row(row)
    assert isinstance(record, dict)
    assert record["raw"] == row
    assert record["name"] == "Entry Four"
    assert record["type"] == "Login"
    assert record["folder"] == "FolderC"
    assert record["notes"] == "Some notes"
    assert record["fields"] == []


def test_parse_row_handles_invalid_field_format():
    row = ["Entry Five|7777", "Login", "FolderD", "Notes", "InvalidFieldFormat"]
    record = convert.parse_row(row)
    assert isinstance(record, dict)
    assert record["raw"] == row
    assert record["name"] == "Entry Five"
    assert record["type"] == "Login"
    assert record["folder"] == "FolderD"
    assert record["notes"] == "Notes"
    assert record["fields"] == []  # No valid fields parsed


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
    assert first["fields"][0]["name"] == "URL"
    assert first["fields"][1]["name"] == "Benutzername"
    assert first["fields"][2]["type"] == 8
    assert first["fields"][3]["value"] == "hello, world"

    second = records[1]
    assert second["name"] == "Entry Two |with pipe"
    assert second["type"] == "Anmelden"
    assert second["folder"] == "FolderB"
    assert second["notes"] == ""
    assert second["fields"][0]["type"] == 2
    assert second["fields"][1]["name"] == "Kennwort"
    assert second["fields"][1]["value"] == "secret2"


def test_parse_msecure_csv_handles_empty_file(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.touch()  # Create an empty file

    records = convert.parse_msecure_csv(csv_path)

    assert isinstance(records, list)
    assert len(records) == 0  # No records should be returned for an empty file


def test_create_dummy_folderId_from_folder_name():
    folder_name = "Test-Folder 1"
    folder_id = convert.create_dummy_folderId_from_folder_name(folder_name)
    assert isinstance(folder_id, str)
    assert len(folder_id) == 36  # UUID length
    assert folder_id.count("-") == 4  # UUID format