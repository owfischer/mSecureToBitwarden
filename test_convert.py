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


def test_extract_folder_name_from_record():
    record = {"folder": "FolderX"}
    folder_name = convert.extract_folder_name_from_record(record)
    assert folder_name == "FolderX"


def test_extract_folder_names_from_records(sample_csv_rows):
    records = [convert.parse_row(row) for row in sample_csv_rows]
    folder_names = convert.extract_folder_names_from_records(records)
    assert isinstance(folder_names, set)
    assert "FolderA" in folder_names
    assert "FolderB" in folder_names


def test_extract_folder_names_from_records_handles_empty_folder_names():
    records = [
        {"folder": "FolderA"},
        {"folder": ""},
        {"folder": "FolderB"},
        {"folder": ""},
    ]
    folder_names = convert.extract_folder_names_from_records(records)
    assert isinstance(folder_names, set)
    assert "FolderA" in folder_names
    assert "FolderB" in folder_names
    assert "" not in folder_names  # Empty folder names should not be included


def test_extract_folder_names_from_records_handles_duplicates():
    records = [
        {"folder": "FolderA"},
        {"folder": "FolderB"},
        {"folder": "FolderA"},  # Duplicate
        {"folder": "FolderC"},
    ]
    folder_names = convert.extract_folder_names_from_records(records)
    assert isinstance(folder_names, set)
    assert "FolderA" in folder_names
    assert "FolderB" in folder_names
    assert "FolderC" in folder_names
    assert len(folder_names) == 3  # Duplicates should not increase the count


def test_extract_folder_names_from_records_handles_empty_list():
    records = []
    folder_names = convert.extract_folder_names_from_records(records)
    assert isinstance(folder_names, set)
    assert len(folder_names) == 0  # No folder names should be returned for an empty list


def test_extract_folder_names_from_records_handles_missing_folder_key():
    records = [
        {"folder": "FolderA"},
        {"name": "Record without folder"},
        {"folder": "FolderB"},
    ]
    folder_names = convert.extract_folder_names_from_records(records)
    assert isinstance(folder_names, set)
    assert "FolderA" in folder_names
    assert "FolderB" in folder_names
    assert len(folder_names) == 2  # Only valid folder names should be included


def test_extract_folder_names_from_records_handles_none_folder_value():
    records = [
        {"folder": "FolderA"},
        {"folder": None},
        {"folder": "FolderB"},
    ]
    folder_names = convert.extract_folder_names_from_records(records)
    assert isinstance(folder_names, set)
    assert "FolderA" in folder_names
    assert "FolderB" in folder_names
    assert len(folder_names) == 2  # None values should not be included


def test_extract_folder_names_from_records_handles_mixed_cases():
    records = [
        {"folder": "FolderA"},
        {"folder": ""},
        {"folder": "FolderB"},
        {"folder": "FolderA"},  # Duplicate
        {"name": "Record without folder"},
        {"folder": None},
    ]
    folder_names = convert.extract_folder_names_from_records(records)
    assert isinstance(folder_names, set)
    assert "FolderA" in folder_names
    assert "FolderB" in folder_names
    assert "" not in folder_names  # Empty folder names should not be included
    assert len(folder_names) == 2  # Only valid unique folder names should be included


def test_extract_folder_names_from_records_handles_all_empty_or_invalid():
    records = [
        {"folder": ""},
        {"name": "Record without folder"},
        {"folder": None},
    ]
    folder_names = convert.extract_folder_names_from_records(records)
    assert isinstance(folder_names, set)
    assert len(folder_names) == 0  # No valid folder names should be returned


def test_create_folder_json_structure_returns_correct_structure():
    folder_names = set(["FolderA", "FolderB"])
    folders=convert.create_folder_json_structure(folder_names)
    assert isinstance(folders, list)
    assert len(folders) == 2
    assert {folder["name"] for folder in folders} == {"FolderA", "FolderB"}
    assert all("folderId" in folder for folder in folders)  # Each folder should have a folderId => all TRUE


def test_create_folder_json_structure_handles_empty_set():
    folder_names = set()
    folders = convert.create_folder_json_structure(folder_names)
    assert isinstance(folders, list)
    assert len(folders) == 0  # No folders should be created for an empty set


def test_create_folder_json_structure_handles_single_folder():
    folder_names = set(["SingleFolder"])
    folders = convert.create_folder_json_structure(folder_names)
    assert isinstance(folders, list)
    assert len(folders) == 1
    assert folders[0]["name"] == "SingleFolder"
    assert "folderId" in folders[0]  # The single folder should have a folderId


@pytest.fixture
def record_with_fields():
    return {
        "name": "Test Item",
        "type": "Login",
        "folder": "Test Folder",
        "notes": "Some notes",
        "fields": [
            {"name": "Field1", "type": 0, "value": "Value1"},
            {"name": "Field2", "type": 1, "value": "Value2"},
        ],
    }


def test_create_fields_json_structure_returns_correct_structure(record_with_fields):
    folder_id = "dummy-folder-id"
    fields = convert.create_fields_json_structure(record_with_fields)

    assert isinstance(fields, list)
    assert all(isinstance(field, dict) for field in fields)
    assert len(fields) == 2
    assert fields[0]["name"] == "Field1"
    assert fields[0]["type"] == 0
    assert fields[0]["value"] == "Value1"
    assert fields[1]["name"] == "Field2"
    assert fields[1]["type"] == 1
    assert fields[1]["value"] == "Value2"


def test_create_fields_json_structure_handles_empty_fields():
    record = {
        "name": "Test Item",
        "type": "Login",
        "folder": "Test Folder",
        "notes": "Some notes",
        "fields": [],
    }
    fields = convert.create_fields_json_structure(record)

    assert isinstance(fields, list)
    assert len(fields) == 0  # No fields should be created for an empty list


def test_create_fields_json_structure_handles_missing_fields_key():
    record = {
        "name": "Test Item",
        "type": "Login",
        "folder": "Test Folder",
        "notes": "Some notes",
        # No 'fields' key
    }
    fields = convert.create_fields_json_structure(record)

    assert isinstance(fields, list)
    assert len(fields) == 0  # No fields should be created if 'fields' key is missing


def test_create_fields_json_structure_handles_non_list_fields():
    record = {
        "name": "Test Item",
        "type": "Login",
        "folder": "Test Folder",
        "notes": "Some notes",
        "fields": "not-a-list",  # Invalid type for fields
    }
    fields = convert.create_fields_json_structure(record)

    assert isinstance(fields, list)
    assert len(fields) == 0  # No fields should be created if 'fields' is not a list



@pytest.fixture
def record_with_login_fields():
    return {
        "name": "Test Item",
        "type": "Login",
        "folder": "Test Folder",
        "notes": "Some notes",
        "fields": [
            {"name": "Benutzername", "type": 0, "value": "testuser"},
            {"name": "Kennwort", "type": 1, "value": "testpass"},
            {"name": "Anmelde-URL", "type": 2, "value": "https://example.com"},
        ],
    }
def test_create_login_json_structure_returns_correct_structure(record_with_login_fields):
    login = convert.create_login_json_structure(record_with_login_fields)

    assert isinstance(login, dict)
    assert "uris" in login
    assert isinstance(login["uris"], list)
    assert "username" in login
    assert "password" in login
    assert login["username"] == "testuser"
    assert login["password"] == "testpass"
    assert len(login["uris"]) == 1
    assert login["uris"][0]["uri"] == "https://example.com"
    login.clear()

    
def test_create_login_json_structure_handles_missing_fields(record_with_login_fields):
    # record = dict(record_with_login_fields)  # Create a copy of the record to modify it
    record = record_with_login_fields.copy()
    del record["fields"]  # Remove the 'fields' key

    login = convert.create_login_json_structure(record)

    assert isinstance(login, dict)
    assert login["username"] == ""
    assert login["password"] == ""
    assert login["uris"] == []  # No URIs should be created if 'fields' key is missing
    login.clear()


def test_create_login_json_structure_handles_empty_fields(record_with_login_fields):
    record = dict(record_with_login_fields)  # Create a copy of the record to modify it
    record["fields"] = []  # Empty fields list

    login = convert.create_login_json_structure(record)

    assert isinstance(login, dict)
    assert login["username"] == ""
    assert login["password"] == ""
    assert login["uris"] == []  # No URIs should be created for an empty list of fields
    login.clear()


@pytest.fixture
def record_with_card_fields():
    return {
        "name": "Test Item",
        "type": "Card",
        "folder": "Test Folder",
        "notes": "Some notes",
        "fields": [
            {"name": "Karteninhaber", "type": 0, "value": "testuser"},
            {"name": "Kartenmarke", "type": 1, "value": "testbrand"},
            {"name": "Kartennummer", "type": 2, "value": "1234567890123456"},
            {"name": "Verfallsmonat", "type": 3, "value": "12"},
            {"name": "Verfallsjahr", "type": 4, "value": "2025"},
            {"name": "Sicherheitscode", "type": 5, "value": "123"},
        ],
    }
def test_create_card_json_structure_returns_correct_structure(record_with_card_fields):
    card = convert.create_card_json_structure(record_with_card_fields)
    assert isinstance(card, dict)
    assert "cardholderName" in card
    assert "brand" in card
    assert "number" in card
    assert "expMonth" in card
    assert "expYear" in card
    assert "code" in card


def test_create_card_json_structure_handles_missing_fields(record_with_card_fields):
    record = dict(record_with_card_fields)  # Create a copy of the record to modify it
    del record["fields"]  # Remove the 'fields' key

    card = convert.create_card_json_structure(record)

    assert isinstance(card, dict)
    assert card["cardholderName"] == ""
    assert card["brand"] == ""
    assert card["number"] == ""
    assert card["expMonth"] == ""
    assert card["expYear"] == ""
    assert card["code"] == ""  # All fields should be empty if 'fields' key is missing


def test_create_card_json_structure_handles_empty_fields(record_with_card_fields):
    record = dict(record_with_card_fields)  # Create a copy of the record to modify it
    record["fields"] = []  # Empty fields list

    card = convert.create_card_json_structure(record)

    assert isinstance(card, dict)
    assert card["cardholderName"] == ""
    assert card["brand"] == ""
    assert card["number"] == ""
    assert card["expMonth"] == ""
    assert card["expYear"] == ""
    assert card["code"] == ""  # All fields should be empty for an empty list of fields


def test_create_card_json_structure_handles_partial_fields(record_with_card_fields):
    record = dict(record_with_card_fields)  # Create a copy of the record to modify it
    record["fields"] = [
        {"name": "Karteninhaber", "type": 0, "value": "testuser"},
        {"name": "Kartennummer", "type": 2, "value": "1234567890123456"},
    ]  # Only some fields provided

    card = convert.create_card_json_structure(record)

    assert isinstance(card, dict)
    assert card["cardholderName"] == "testuser"
    assert card["brand"] == ""  # Missing field should be empty
    assert card["number"] == "1234567890123456"
    assert card["expMonth"] == ""  # Missing field should be empty
    assert card["expYear"] == ""  # Missing field should be empty
    assert card["code"] == ""  # Missing field should be empty


def test_create_card_json_structure_handles_non_list_fields(record_with_card_fields):
    record = dict(record_with_card_fields)  # Create a copy of the record to modify it
    record["fields"] = "not-a-list"  # Invalid type for fields

    card = convert.create_card_json_structure(record)

    assert isinstance(card, dict)
    assert card["cardholderName"] == ""
    assert card["brand"] == ""
    assert card["number"] == ""
    assert card["expMonth"] == ""
    assert card["expYear"] == ""
    assert card["code"] == ""  # All fields should be empty if 'fields' is not a list


@pytest.fixture
def record_with_secure_note():
    return {
        "name": "Test Secure Note",
        "type": "Sichere Notiz",
        "folder": "Test Folder",
        "notes": "Some secure note content",
        "fields": [],
    }
def test_create_secureNote_json_structure_returns_correct_structure(record_with_secure_note):
    secure_note = convert.create_secureNote_json_structure(record_with_secure_note)
    assert isinstance(secure_note, dict)
    assert "type" in secure_note
    assert secure_note["type"] == 0  # Secure Note type


@pytest.fixture
def record_with_identity_fields():
    return {
        "name": "Test Identity",
        "type": "Identität",
        "folder": "Test Folder",
        "notes": "Some identity notes",
        "fields": [{ "name": "Titel", "type": 0, "value": "Dr." }, 
                   { "name": "Vorname", "type": 0, "value": "John" }, 
                   { "name": "Zweiter Vorname", "type": 0, "value": "A." }, 
                   { "name": "Nachname", "type": 0, "value": "Doe" }, 
                   { "name": "Reisepassnummer", "type": 0, "value": "X1234567" }],
    }
def test_create_identity_json_structure_returns_correct_structure(record_with_identity_fields):
    identity = convert.create_identity_json_structure(record_with_identity_fields)
    assert isinstance(identity, dict)
    assert identity["title"] == "Dr."
    assert identity["firstName"] == "John"
    assert identity["middleName"] == "A."
    assert identity["lastName"] == "Doe"
    assert identity["passportNumber"] == "X1234567"  # Check that the passport number is correctly extracted


def test_create_identity_json_structure_handles_missing_fields():
    record = {
        "name": "Test Identity",
        "type": "Identity",
        "folder": "Test Folder",
        "notes": "Some identity notes",
        # No 'fields' key
    }
    identity = convert.create_identity_json_structure(record)
    assert isinstance(identity, dict)
    assert identity["title"] == ""
    assert identity["firstName"] == ""
    assert identity["middleName"] == ""
    assert identity["lastName"] == ""
    assert identity["passportNumber"] == ""  # All fields should be empty if 'fields' key is missing


def test_create_identity_json_structure_handles_empty_fields():
    record = {
        "name": "Test Identity",
        "type": "Identity",
        "folder": "Test Folder",
        "notes": "Some identity notes",
        "fields": [],
    }
    identity = convert.create_identity_json_structure(record)
    assert isinstance(identity, dict)
    assert identity["title"] == ""
    assert identity["firstName"] == ""
    assert identity["middleName"] == ""
    assert identity["lastName"] == ""
    assert identity["passportNumber"] == ""  # All fields should be empty for an empty list of fields


def test_map_msecure_item_type_to_bitwarden_type():
    record = {
            "name": "Test Record",
            "type": "Anmelden",
            "folder": "Test Folder",
            "fields": [],
        }
    assert convert.map_msecure_item_type_to_bitwarden_type(record["type"]) == "login"
    record["type"] = "Kreditkarte"
    assert convert.map_msecure_item_type_to_bitwarden_type(record["type"]) == "card"
    record["type"] = "Sichere Notiz"
    assert convert.map_msecure_item_type_to_bitwarden_type(record["type"]) == "secureNote"
    record["type"] = "Identität"
    assert convert.map_msecure_item_type_to_bitwarden_type(record["type"]) == "identity"


def test_map_msecure_item_type_to_bitwarden_type_handles_unknown_type():
    record = {
            "name": "Test Record",
            "type": "UnknownType",
            "folder": "Test Folder",
            "fields": [],
        }
    assert convert.map_msecure_item_type_to_bitwarden_type(record["type"]) == "login"  # Default to login for unknown types 


def test_map_msecure_item_type_to_bitwarden_type_handles_empty_type():
    record = {
            "name": "Test Record",
            "type": "",
            "folder": "Test Folder",
            "fields": [],
        }
    assert convert.map_msecure_item_type_to_bitwarden_type(record["type"]) == "login"  # Default to login for empty type


# def record_with_login_fields():
#     return {
#         "name": "Test Item",
#         "type": "Login",
#         "folder": "Test Folder",
#         "notes": "Some notes",
#         "fields": [
#             {"name": "Benutzername", "type": 0, "value": "testuser"},
#             {"name": "Kennwort", "type": 1, "value": "testpass"},
#             {"name": "Anmelde-URL", "type": 2, "value": "https://example.com"},
#         ],
#     }
# record_with_card_fields = {
#         "name": "Test Item",
#         "type": "Card",
#         "folder": "Test Folder",
#         "notes": "Some notes",
#         "fields": [
#             {"name": "Karteninhaber", "type": 0, "value": "testuser"},
#             {"name": "Kartenmarke", "type": 1, "value": "testbrand"},
#             {"name": "Kartennummer", "type": 2, "value": "1234567890123456"},
#             {"name": "Verfallsmonat", "type": 3, "value": "12"},
#             {"name": "Verfallsjahr", "type": 4, "value": "2025"},
#             {"name": "Sicherheitscode", "type": 5, "value": "123"},
#         ],
#     }
#  "card": {
#         "cardholderName": "Oliver Fischer",
#         "brand": "Mastercard",
#         "number": "524375214445279",
#         "expMonth": "6",
#         "expYear": "2028",
#         "code": "126"
#       },

def test_create_item_json_structure_returns_correct_structure_with_fields(record_with_fields):
    item_json = convert.create_item_json_structure(record_with_fields)
    assert item_json["type"] == 1
    assert isinstance(item_json, dict)
    assert item_json["name"] == "Test Item"
    assert item_json["folderId"] == "4481408b-bd5f-54ce-95af-7a675c1511de"  # = str(uuid.uuid5(uuid.NAMESPACE_DNS, "Test Folder"))
    assert item_json["notes"] == "Some notes"
    assert isinstance(item_json["fields"], list)
    assert len(item_json["fields"]) == 2
    assert item_json["fields"][0]["name"] == "Field1"
    assert item_json["fields"][1]["type"] == 1
    assert item_json["fields"][1]["value"] == "Value2"


def test_create_item_json_structure_returns_correct_structure_with_login(record_with_login_fields):
    item_json = convert.create_item_json_structure(record_with_login_fields)
    
    assert item_json["type"] == 1
    assert isinstance(item_json, dict)
    assert item_json["name"] == "Test Item"
    assert item_json["folderId"] == "4481408b-bd5f-54ce-95af-7a675c1511de"  # = str(uuid.uuid5(uuid.NAMESPACE_DNS, "Test Folder"))
    assert item_json["notes"] == "Some notes"
    assert isinstance(item_json["fields"], list)
    assert len(item_json["fields"]) == 0
    assert isinstance(item_json["login"], dict)
    assert item_json["login"]["username"] == "testuser"
    assert item_json["login"]["password"] == "testpass"
    assert len(item_json["login"]["uris"]) == 1
    assert item_json["login"]["uris"][0]["uri"] == "https://example.com"


def test_create_item_json_structure_returns_correct_structure_with_secure_note(record_with_secure_note):
    item_json = convert.create_item_json_structure(record_with_secure_note)

    assert isinstance(item_json, dict)
    assert item_json["type"] == 2
    assert item_json["name"] == "Test Secure Note"
    assert item_json["folderId"] == "4481408b-bd5f-54ce-95af-7a675c1511de"  # = str(uuid.uuid5(uuid.NAMESPACE_DNS, "Test Folder"))
    assert item_json["notes"] == "Some secure note content"
    assert isinstance(item_json["fields"], list)
    assert len(item_json["fields"]) == 0
    assert isinstance(item_json["secureNote"], dict)
    assert item_json["secureNote"]["type"] == 0  # Secure Note type


def test_create_item_json_structure_returns_correct_structure_with_card(record_with_card_fields):
    item_json = convert.create_item_json_structure(record_with_card_fields)

    assert isinstance(item_json, dict)
    assert item_json["type"] == 3
    assert item_json["name"] == "Test Item"
    assert item_json["folderId"] == "4481408b-bd5f-54ce-95af-7a675c1511de"  # = str(uuid.uuid5(uuid.NAMESPACE_DNS, "Test Folder"))
    assert item_json["notes"] == "Some notes"
    assert isinstance(item_json["fields"], list)
    assert item_json["fields"] == []
    assert isinstance(item_json["card"], dict)
    assert item_json["card"]["cardholderName"] == "testuser"
    assert item_json["card"]["brand"] == "testbrand"
    assert item_json["card"]["number"] == "1234567890123456"
    assert item_json["card"]["expMonth"] == "12"
    assert item_json["card"]["expYear"] == "2025"
    assert item_json["card"]["code"] == "123"


def test_create_item_json_structure_returns_correct_structure_with_identity(record_with_identity_fields):
    item_json = convert.create_item_json_structure(record_with_identity_fields)

    assert isinstance(item_json, dict)
    assert item_json["type"] == 4
    assert item_json["name"] == "Test Identity"
    assert item_json["folderId"] == "4481408b-bd5f-54ce-95af-7a675c1511de"  # = str(uuid.uuid5(uuid.NAMESPACE_DNS, "Test Folder"))
    assert item_json["notes"] == "Some identity notes" # Notes should be preserved
    assert isinstance(item_json["fields"], list)
    assert item_json["fields"] == []  # Fields shopuld be transfered to identity structure, so fields list should be empty in this example
    assert isinstance(item_json["identity"], dict)
    assert item_json["identity"]["title"] == "Dr."
    assert item_json["identity"]["firstName"] == "John"
    assert item_json["identity"]["middleName"] == "A."
    assert item_json["identity"]["lastName"] == "Doe"
    assert item_json["identity"]["passportNumber"] == "X1234567"


def test_create_item_json_structure_handles_missing_fields_key():
    record = {
        "name": "Test Item",
        "type": "Login",
        "folder": "Test Folder",
        "notes": "Some notes",
        # No 'fields' key
    }
    item_json = convert.create_item_json_structure(record)

    assert isinstance(item_json, dict)
    assert item_json["type"] == 1
    assert item_json["name"] == "Test Item"
    assert item_json["folderId"] == "4481408b-bd5f-54ce-95af-7a675c1511de"  # = str(uuid.uuid5(uuid.NAMESPACE_DNS, "Test Folder"))
    assert item_json["notes"] == "Some notes"
    assert isinstance(item_json["fields"], list)
    assert len(item_json["fields"]) == 0  # No fields should be created if 'fields' key is missing


def test_create_item_json_structure_handles_empty_fields():
    record = {
        "name": "Test Item",
        "type": "Login",
        "folder": "Test Folder",
        "notes": "Some notes",
        "fields": [],
    }
    item_json = convert.create_item_json_structure(record)

    assert isinstance(item_json, dict)
    assert item_json["type"] == 1
    assert item_json["name"] == "Test Item"
    assert item_json["folderId"] == "4481408b-bd5f-54ce-95af-7a675c1511de"  # = str(uuid.uuid5(uuid.NAMESPACE_DNS, "Test Folder"))
    assert item_json["notes"] == "Some notes"
    assert isinstance(item_json["fields"], list)
    assert len(item_json["fields"]) == 0  # No fields should be created for an empty list of fields


def test_create_item_json_structure_handles_missing_folder_key():
    record = {
        "name": "Test Item",
        "type": "Login",
        # No 'folder' key
        "notes": "Some notes",
        "fields": [],
    }
    item_json = convert.create_item_json_structure(record)

    assert isinstance(item_json, dict)
    assert item_json["type"] == 1
    assert item_json["name"] == "Test Item"
    assert item_json["folderId"] == ""  # Folder ID should be empty if 'folder' key is missing
    assert item_json["notes"] == "Some notes"
    assert isinstance(item_json["fields"], list)
    assert len(item_json["fields"]) == 0  # No fields should be created for an empty list of fields


def test_create_item_json_structure_handles_empty_folder_value():
    record = {
        "name": "Test Item",
        "type": "Login",
        "folder": "",  # Empty folder value
        "notes": "Some notes",
        "fields": [],
    }
    item_json = convert.create_item_json_structure(record)

    assert isinstance(item_json, dict)
    assert item_json["type"] == 1
    assert item_json["name"] == "Test Item"
    assert item_json["folderId"] == ""  # Folder ID should be empty if 'folder' value is empty
    assert item_json["notes"] == "Some notes"
    assert isinstance(item_json["fields"], list)
    assert len(item_json["fields"]) == 0  # No fields should be created for an empty list of fields