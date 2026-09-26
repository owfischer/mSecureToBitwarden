#!/usr/bin/env python3
"""Convert an mSecure 7 CSV export into the Bitwarden JSON structure.

The converter is intentionally kept small in this first step. It focuses on the
known field type mapping from the mSecure export to the Bitwarden custom field
model:

  Bitwarden field types:
    0 = Text
    1 = Hidden
    2 = Boolean/Checkbox
    3 = Linked

The mSecure export uses 12 field type numbers in the CSV records, described in
its export format documentation:

  0 = Text
  1 = App Name
  2 = URL
  3 = Alphanumeric
  4 = Phone Number
  5 = E-Mail Address
  6 = Numeric Field
  7 = Username (Text)
  8 = Password (hidden field)
  9 = PIN (hidden field)
  10 = Date (dd/mm/yyyy)
  11 = Date (mm/yyyy)
  12 = Card number (Text)

For the first implementation, only Bitwarden field types 0 (Text) and 1
(Hidden) are relevant.
"""

from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Any


#=============================================================================
# CUSTOMISE THIS SECTION TO YOUR NEEDS:
#
# Mapping of Bitwarden item types to mSecure item types. This is a Dictonary 
# of Sets. Add aliases that occur in your mSecure export file to the set {} 
# on the right of ":" to map them to the correct Bitwarden item type on the 
# left of ":". Currently, there are only 4 Bitwarden item types.
BITWARDEN_FOR_MSECURE_TYPES = {
    "login": {"login", "anmelden"},
    "card": {"card", "credit card", "kreditkarte"},
    "identity": {"identity", "passport", "personalausweis", "identität"},
    "secureNote": {"note", "secure note", "sichere notiz", "geheime notizen"}
}


# For Bitwarden item type "login": mSecure field names that map to the 
# Bitwarden login and uri fields.
LOGIN_FIELD_ALIASES = {
    "username": {"username", "user", "login", "benutzername", "anmeldename"},
    "password": {"password", "passwort", "kennwort"},
}
URI_ALIASES = {"url", "website", "webseite", "anmelde-url", "login-url"}


# For Bitwarden item type "card": mSecure field names that map to the 
# Bitwarden card fields.
CARD_FIELD_ALIASES = {
    "cardholderName": {"cardholder name", "inhabername", "karteninhaber"},
    "brand": {"brand", "marke", "kartenmarke"},
    "number": {"number", "nummer", "kartennummer"},
    "expMonth": {"exp month", "ablaufmonat", "verfallsmonat"},
    "expYear": {"exp year", "ablaufjahr", "verfallsjahr"},
    "code": {"code", "cvv", "cvc", "sicherheitscode", "kartensicherheitscode"},
}

# For Bitwarden item type "identity": mSecure field names that map to the
# Bitwarden identity fields.
IDENTITY_FIELD_ALIASES = {
    "title": {"title", "titel"},
    "firstName": {"first name", "vorname"},
    "middleName": {"middle name", "zweiter vorname"},
    "lastName": {"last name", "nachname"},
    "address1": {"address 1", "adresse 1", "street", "straße"},
    "address2": {"address 2", "adresse 2", "street 2", "straße 2"},
    "address3": {"address 3", "adresse 3", "street 3", "straße 3"},
    "city": {"city", "stadt"},
    "state": {"state", "bundesland"},
    "postalCode": {"postal code", "postleitzahl"},
    "country": {"country", "land"},
    "phone": {"phone", "telefonnummer"},
    "email": {"email", "e-mail"},
    "ssn": {"ssn", "sozialversicherungsnummer"},
    "username": {"username", "benutzername"},
    "passportNumber": {"passport number", "reisepassnummer"},
    "licenseNumber": {"license number", "führerscheinnummer"},
}


# Mapping of the 12 mSecure field types to the 4 Bitwarden custom field types.
# In this first pass, only Text (0) and Hidden (1) are used. Usually, you 
# should not need to change this Dictionary.
MSECURE_TO_BITWARDEN_FIELD_TYPE = {
    0: 0,   # Text field -> Text
    1: 0,   # App name -> Text
    2: 0,   # URL -> Text
    3: 0,   # Alphanumeric -> Text
    4: 0,   # Telephone number -> Text
    5: 0,   # E-mail address -> Text
    6: 0,   # Numeric field -> Text
    7: 0,   # Username -> Text
    8: 1,   # Password -> Hidden
    9: 1,   # PIN -> Hidden
    10: 0,  # Date dd/mm/yyyy -> Text
    11: 0,  # Date mm/yyyy -> Text
    12: 0,  # Card number -> Text
}

# END OF CUSTOMISATION SECTION
#=============================================================================


def map_msecure_field_type_to_bitwarden(msecure_type: int) -> int:
    """Return the Bitwarden field type for a parsed mSecure type.

    Unknown mSecure types default to Bitwarden text fields because they are
    still represented as data and therefore safe for the first converter pass.
    """
    return MSECURE_TO_BITWARDEN_FIELD_TYPE.get(msecure_type, 0)


def is_hidden_msecure_type(msecure_type: int) -> bool:
    """Return True if the mSecure field should become a Bitwarden Hidden field."""
    return map_msecure_field_type_to_bitwarden(msecure_type) == 1


def map_msecure_item_type_to_bitwarden_type(msecure_type: str) -> str:
    """Map the mSecure item type to the Bitwarden item type.

    The mapping is based on the known mSecure types and their corresponding
    Bitwarden types. Unknown mSecure types default to "login" in Bitwarden.
    """
    for bitwarden_type, msecure_aliases in BITWARDEN_FOR_MSECURE_TYPES.items():
        if msecure_type.lower() in msecure_aliases:
            return bitwarden_type
    return "login"  # Default to login if unknown


def parse_msecure_csv(path: str | Path) -> list[dict[str, Any]]:
    """Parse the CSV file with the mSecure record layout.

    Expected columns are:
      1. name | id
      2. type
      3. folder
      4. notes
      5+ field definitions in chunks: name|type|value

    Notes are normalized from the serialized escaped spelling ``\\n`` to an
    actual newline character in the returned record dictionary.
    """
    records: list[dict[str, Any]] = []

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for row in reader:

            if not row:
                continue

            record = parse_row(row)
            records.append(record)

    return records


def parse_row(row):
    # The first four columns are present in the source format.
    # The other fields are parsed from the remaining columns. 
    # The record contains the raw row for debugging purposes, 
    # as well as the parsed fields.
    record = {
                "raw": row,
                "name": parse_name_id(row),
                "type": parse_type(row),
                "folder": parse_folder(row),
                "notes": parse_note(row),
                "fields": parse_fields(row),
            }
    return record


def parse_name_id(row):
    # The first column is the name and ID of the record, separated by a pipe.
    name = ""
    prefix, separator, suffix = row[0].rpartition("|") if row else ("", "", "")
    if separator and suffix.isdigit():
        name = prefix
    return name


def parse_type(row):
    # The second column is the type of the record, e.g. "Login" or "Anmelden".
    return row[1] if len(row) > 1 else ""
    

def parse_folder(row):
    # The third column is the folder of the record, e.g. "FolderA" or "FolderB".
    return row[2] if len(row) > 2 else ""


def parse_note(row):
    # The fourth column is the notes of the record, which may contain escaped
    # newlines. We normalize them from the export style into a usable Python 
    # string. That lets a notes field like "First line\\nSecond line"
    # become an actual multi-line text value in the parsed record.
    notes = row[3] if len(row) > 3 else ""
    notes = notes.replace("\\n", "\n")
    notes = notes.replace("\\r\\n", "\n")
    return notes


def parse_fields(row):
    # The remaining columns are field definitions in the form of
    # name|type|value. We parse them into a list of dictionaries.
    # TODO: Handle cases with different field names (Website, URL, 
    # Anmelde-URL, etc.) and map them to the appropriate Bitwarden fields.

    fields = []
    for field in row[4:]:
        parts = field.split("|", 2)
        if len(parts) == 3:
            name, type_str, value = parts
            try:
                type_int = int(type_str)
            except ValueError:
                type_int = 0  # Default to text if type is not an integer
            fields.append({"name": name, "type": type_int, "value": value})
    return fields


def extract_folder_name_from_record(record: dict[str, Any]) -> str:
    """Extract the folder name from a record dictionary.

    If the folder name is empty, return an empty string.
    """
    return record.get("folder", "")


def extract_folder_names_from_records(records: list[dict[str, Any]]) -> set[str]:
    """Extract all unique folder names from a list of records.

    If a folder name is empty, it is not included in the result.\n
    If a folder name is duplicated, it is only included once in the result.
    """
    folder_names = set()
    for record in records:
        folder_name = extract_folder_name_from_record(record)
        if folder_name:
            folder_names.add(folder_name)
    return folder_names


def create_dummy_folderId_from_folder_name(folder_name: str) -> str:
    """Create a dummy folderId from the folder name.

    This is a placeholder implementation that generates a UUID based on the
    folder name. In a real implementation, you would want to ensure that the
    folderId is unique and consistent across runs.
    """
    import uuid
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, folder_name))


def create_folder_json_structure(folder_names: set[str]) -> list[dict[str, Any]]:
    """Create a list of folder dictionaries for the Bitwarden JSON structure.

    Each folder dictionary contains the folder name and a unique ID.
    """
    folders = []
    for folder_name in folder_names:
        folder_id = create_dummy_folderId_from_folder_name(folder_name)
        folders.append({
            "name": folder_name,
            "folderId": folder_id,            
        })
    return folders    


def create_fields_json_structure(record: dict[str, Any]) -> dict[str, Any]:
    """Create a fields dictionary for the Bitwarden JSON structure.

    The fields dictionary contains the field definitions.
    """
    fields = []
    for field in record.get("fields", []):
        if not isinstance(field, dict):
            continue
        fields.append({
            "name": field["name"],
            "type": field["type"],
            "value": field["value"]
        })
    return fields


def create_login_json_structure(record: dict[str, Any]) -> dict[str, Any]:
    """Create a login dictionary for the Bitwarden JSON structure.

    The login dictionary contains the field values for uris, username and
    passsword from the mSecure record.
    """
    login = {
        "uris": [],
        "username": "",
        "password": "",
    }

    for field in record.get("fields", []):
        if not isinstance(field, dict):
            continue

        field_name = field["name"].lower()

        for key, aliases in LOGIN_FIELD_ALIASES.items():
            if field_name in aliases:
                login[key] = field["value"]
                break
        else:
            if field_name in URI_ALIASES:
                login["uris"].append({"uri": field["value"]})

    return login


def create_card_json_structure(record: dict[str, Any]) -> dict[str, Any]:
    """Create a card dictionary for the Bitwarden JSON structure.

    The card dictionary contains the cardholder name, brand, number, 
    expiration date, and security code.
    """
    card = {
        "cardholderName": "",
        "brand": "",
        "number": "",
        "expMonth": "",
        "expYear": "",
        "code": "",
    }

    for field in record.get("fields", []):
        if not isinstance(field, dict):
            continue
        for key, aliases in CARD_FIELD_ALIASES.items():
            if field["name"].lower() in aliases:
                card[key] = field["value"]
                break
    return card


def create_secureNote_json_structure(record: dict[str, Any]) -> dict[str, Any]:
    """Create a secure note dictionary for the Bitwarden JSON structure.

    The secure note dictionary only contains the type field. The mSecure
    record argument is currently not used.
    """
    secureNote = {
        "type": 0
        }
    return secureNote


def create_identity_json_structure(record: dict[str, Any]) -> dict[str, Any]:
    """Create an identity dictionary for the Bitwarden JSON structure.

    The identity dictionary contains various personal information fields
    and their values from the mSecure record.
    """
    # Empty identity structure with default values
    identity = {
        "title": "",
        "firstName": "",
        "middleName": "",
        "lastName": "",
        "address1": "",
        "address2": "",
        "address3": "",
        "city": "",
        "state": "",
        "postalCode": "",
        "country": "",
        "company": "",
        "phone": "",
        "email": "",
        "ssn": "",
        "username": "",
        "passportNumber": "",
        "licenseNumber": "",
    }

    # Populate the identity structure based on the aliases with the values from the record's fields
    for field in record.get("fields", []):      
        if not isinstance(field, dict):
            continue
        for key, aliases in IDENTITY_FIELD_ALIASES.items():
            if field["name"].lower() in aliases:
                identity[key] = field["value"]
                break
    return identity


# TODO: Mapping not directly corresponding mSecure record types to Bitwarden 
# item types.

# TODO: Implement creating JSON fields for those fields that are not part 
# of the login or card structure, etc., such as custom fields.
# Caution: fields must not be repeated in card, login, and custom fields. 
# If a field is already used in one of those structures, it should not be 
# included in the custom fields again.

# TODO: Implement a function to create the complete Bitwarden JSON structure
# from the parsed mSecure records.


# def demo_mapping() -> None:
#     """Small demonstration that the mapping produces the target field types."""
#     examples = {
#         7: "Username from mSecure -> Text field in Bitwarden",
#         8: "Password from mSecure -> Hidden field in Bitwarden",
#         12: "Card number from mSecure -> Text field in Bitwarden",
#     }
#     for key, description in examples.items():
#         print(f"{key}: {map_msecure_field_type_to_bitwarden(key)} // {description}")


# if __name__ == "__main__":
#     demo_mapping()
