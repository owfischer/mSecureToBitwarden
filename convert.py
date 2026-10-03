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

import argparse
import copy
import csv
import json
from pathlib import Path
from typing import Any


#=============================================================================
# CUSTOMISE THIS SECTION TO YOUR NEEDS:

# Mapping of Bitwarden item types to mSecure item types. This is a Dictonary 
# of Sets. Add aliases that occur in your mSecure export file to the set {} 
# on the right of ":" to map them to the correct Bitwarden item type on the 
# left of ":". Currently, there are only 4 Bitwarden item types.
BITWARDEN_FOR_MSECURE_TYPES = {
    "login": {"login", "anmelden", "email-account", "email account",
        "bankkonto", "bank account", 
        "betriebssystem", "operating system",
        "drahtlos-netzwerk", "wireless network",
        "software-lizenz", "software license",
        "sim-karten", "sim card", "sim cards", "telefonkarte", "telefonkarten",
        "mitgliedschaft", "membership", "mitgliedschaften", "memberships",
        "registrierungscode", "registration code", "registrierungscodes", "registration codes",
        },
    "card": {"card", "credit card", "kreditkarte"},
    "identity": {"identity", "passport", "personalausweis", "identität"},
    "secureNote": {"note", "secure note", "sichere notiz", "geheime notizen",
        "kombination", "kombinationen", "combination" ,"combinations",
        },
}

# Mapping of the Bitwarden types to type codes.
# Usually, you should not need to change this Dictionary.
BITWARDEN_TYPE_STR_TO_TYPE_CODE = {
    "login": 1,
    "secureNote": 2,
    "card" : 3,
    "identity" : 4
}

# For Bitwarden item type "login" (type 1): 
# mSecure field names that map to the Bitwarden login and uri fields.
LOGIN_FIELD_ALIASES = {
    "username": {"username", "user", "login", "benutzername", "anmeldename", 
                 "email", "e-mail", "e-mail-account", "email account", 
                 "email address", "e-mail-adresse"},
    "password": {"password", "passwort", "kennwort"},
}
URI_ALIASES = {"url", "website", "webseite", "anmelde-url", "login-url"}

# For Bitwarden item type "secureNote" (type 2):
# -- not needed --

# For Bitwarden item type "card" (type 3):
# mSecure field names that map to the Bitwarden card fields.
CARD_FIELD_ALIASES = {
    "cardholderName": {"cardholder name", "inhabername", "karteninhaber"},
    "brand": {"brand", "marke", "kartenmarke"},
    "number": {"number", "nummer", "kartennummer"},
    "expMonth": {"exp month", "ablaufmonat", "verfallsmonat"},
    "expYear": {"exp year", "ablaufjahr", "verfallsjahr"},
    "code": {"code", "cvv", "cvc", "sicherheitscode", "kartensicherheitscode"},
}

# For Bitwarden item type "identity" (type 4): 
# mSecure field names that map to the Bitwarden identity fields.
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
# TEMPLATES

# Template for the empty JSON structure of the Bitwarden export file
EMPTY_EXPORT_JSON = {
    "folders": [],
    "items": [],
    #"organizations": [],   # not implemented yet 
    #"version": 2
}

# Template for the empty JSON structure of all Bitwarden folder records
EMPTY_FOLDER_JSON = {
    "name": "",
    "folderId": ""
}

# Template for the empty JSON structure of a single field record in a Bitwarden item
EMPTY_FIELD_JSON = {
    "name": "",
    "type": 0,
    "value": ""
}

# Template for the empty JSON structure of all Bitwarden item records
EMPTY_ITEM_JSON = {
    "name": "",
    "type": "",
    "folderId": "",
    "notes": "",
    "fields": []
}

# Template for the empty JSON substructure of a Bitwarden login item
EMPTY_LOGIN_JSON = {
    "uris": [],
    "username": "",
    "password": "",
}

# Template for the empty JSON substructure of a Bitwarden secureNote item
EMPTY_SECURENOTE_JSON = {
    "type": 0
    }

# Template for the empty JSON substructure of a Bitwarden card item
EMPTY_CARD_JSON = {
    "cardholderName": "",
    "brand": "",
    "number": "",
    "expMonth": "",
    "expYear": "",
    "code": "",
}

# Template for the empty JSON substructure of a Bitwarden identity item
EMPTY_IDENTITY_JSON = {
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

#  END OF TEMPLATES SECTION


#=============================================================================
# Functions for parsing the mSecure CSV file
#=============================================================================

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


def parse_row(row: dict[str, Any]) -> dict[str, Any]:
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


def parse_name_id(row: dict[str, Any]) -> str:
    # The first column is the name and ID of the record, separated by a pipe.
    name = ""
    prefix, separator, suffix = row[0].rpartition("|") if row else ("", "", "")
    if separator and suffix.isdigit():
        name = prefix
    return name


def parse_type(row: dict[str, Any]) -> str:
    # The second column is the type of the record, e.g. "Login" or "Anmelden".
    return row[1] if len(row) > 1 else ""
    

def parse_folder(row: dict[str, Any]) -> str:
    # The third column is the folder of the record, e.g. "FolderA" or "FolderB".
    return row[2] if len(row) > 2 else ""


def parse_note(row: dict[str, Any]) -> str:
    # The fourth column is the notes of the record, which may contain escaped
    # newlines. We normalize them from the export style into a usable Python 
    # string. That lets a notes field like "First line\\nSecond line"
    # become an actual multi-line text value in the parsed record.
    notes = row[3] if len(row) > 3 else ""
    notes = notes.replace("\\n", "\n")
    notes = notes.replace("\\r\\n", "\n")
    return notes


def parse_fields(row: dict[str, Any]) -> list[dict[str, Any]]:
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


#=============================================================================
# Functions for creating the Bitwarden JSON file
#=============================================================================

def convert_csv_to_bitwarden_json(input_path: str | Path, output_path: str | Path | None = None,) -> Path:
    """Convert an mSecure CSV export and write the Bitwarden JSON file.
    If output_path is None, the output file will be created in the same directory
    as the input file, with the same name but a .json extension."""
    
    # Convert the input and output paths to Path objects
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.with_suffix(".json")
    else:
        output_path = Path(output_path)

    # Parse the mSecure CSV file and create the Bitwarden JSON structure
    records = parse_msecure_csv(input_path)
    bitwarden_json = create_bitwarden_json_structure(records)

    # Write the Bitwarden JSON structure to the output file with UTF-8 encoding
    output_path.write_text(
        json.dumps(bitwarden_json, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def create_bitwarden_json_structure(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Create the complete Bitwarden JSON structure from the parsed mSecure records.

    This function generates the folders and items sections of the Bitwarden
    JSON structure based on the provided mSecure records.
    """
    bitwarden_json = copy.deepcopy(EMPTY_EXPORT_JSON)
    folder_names = extract_folder_names_from_records(records)
    bitwarden_json["folders"] = create_folder_json_structure(folder_names)
    bitwarden_json["items"] = [create_item_json_structure(record) for record in records]
    return bitwarden_json


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


def extract_folder_name_from_record(record: dict[str, Any]) -> str:
    """Extract the folder name from a record dictionary.

    If the folder name is empty, return an empty string.
    """
    return record.get("folder", "")


def create_folder_json_structure(folder_names: set[str]) -> list[dict[str, Any]]:
    """Create a list of folder dictionaries for the Bitwarden JSON structure.

    Each folder dictionary contains the folder name and a unique ID.
    """
    folders = []
    for folder_name in folder_names:
        folder = copy.deepcopy(EMPTY_FOLDER_JSON)
        folder_id = create_dummy_folderId_from_folder_name(folder_name)
        folder["name"] = folder_name
        folder["folderId"] = folder_id
        folders.append(folder)
    return folders    


def create_dummy_folderId_from_folder_name(folder_name: str) -> str:
    """Create a dummy folderId from the folder name.

    This is a placeholder implementation that generates a UUID based on the
    folder name. In a real implementation, you would want to ensure that the
    folderId is unique and consistent across runs.
    """
    import uuid
    folder_name = folder_name.strip()  # Normalize the folder name
    folderId = ""
    if folder_name:
        folderId = str(uuid.uuid5(uuid.NAMESPACE_DNS, folder_name))
    return folderId


def create_item_json_structure(record: dict[str, Any]) -> dict[str, Any]:
    item_json = copy.deepcopy(EMPTY_ITEM_JSON)
    # The builder must be initialized with copy.deepcopy(...) for the empty 
    # templates so that each record gets its own, independent dict/list pair.
    # Otherwise, side effects have been observed!

    type_json = {}
    item_type_code = 1

    for key, value in record.items():
        if key == "raw":
            # Skip the raw field, as it is not needed in the Bitwarden JSON structure
            continue  
        
        if key == "type":
            # replace the value string with unique type string
            mapped_type = "login"
            for bitwarden_type, aliases in BITWARDEN_FOR_MSECURE_TYPES.items():
                if str(value).lower() in {alias.lower() for alias in aliases}:
                    mapped_type = bitwarden_type
                    break
            # replace the type string by type integer and default to 1 ("login")
            item_type_code = BITWARDEN_TYPE_STR_TO_TYPE_CODE.get(mapped_type, 1)
            value = item_type_code

            # add type-specific dictionaries to item dictionary
            if item_type_code == 1:
                type_json = create_login_json_structure(record)
                item_json["login"] = type_json
            elif item_type_code == 2:
                type_json = create_secureNote_json_structure(record)
                item_json["secureNote"] = type_json
            elif item_type_code == 3:
                type_json = create_card_json_structure(record)
                item_json["card"] = type_json
            elif item_type_code == 4:
                type_json = create_identity_json_structure(record)
                item_json["identity"] = type_json
            else:
                type_json = {}

        if key == "folder":
            # replace folder name with folderId
            key = "folderId"
            value = create_dummy_folderId_from_folder_name(value)

        if key == "fields":
            type_specific_aliases = union_set_of_aliases(item_type_code)
            value = create_fields_json_structure(record, type_specific_aliases)

        item_json[key] = value
 
    return item_json


def create_login_json_structure(record: dict[str, Any]) -> dict[str, Any]:
    """Create a login dictionary for the Bitwarden JSON structure.

    The login dictionary contains the field values for uris, username and
    passsword from the mSecure record.
    """
    login = copy.deepcopy(EMPTY_LOGIN_JSON)
    # The builder must be initialized with copy.deepcopy(...) for the empty 
    # templates so that each record gets its own, independent dict/list pair.
    # Otherwise, side effects have been observed!

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


def create_secureNote_json_structure(record: dict[str, Any]) -> dict[str, Any]:
    """Create a secure note dictionary for the Bitwarden JSON structure.

    The secure note dictionary only contains the type field. The mSecure
    record argument is currently not used.
    """
    secureNote = copy.deepcopy(EMPTY_SECURENOTE_JSON)
    # The builder must be initialized with copy.deepcopy(...) for the empty 
    # templates so that each record gets its own, independent dict/list pair.
    # Otherwise, side effects have been observed!
    return secureNote


def create_card_json_structure(record: dict[str, Any]) -> dict[str, Any]:
    """Create a card dictionary for the Bitwarden JSON structure.

    The card dictionary contains the cardholder name, brand, number, 
    expiration date, and security code.
    """
    card_json = copy.deepcopy(EMPTY_CARD_JSON)
    # The builder must be initialized with copy.deepcopy(...) for the empty 
    # templates so that each record gets its own, independent dict/list pair.
    # Otherwise, side effects have been observed!

    for field in record.get("fields", []):
        if not isinstance(field, dict):
            continue
        card_json = copy_field_to_card_json(card_json, field)
    return card_json


def copy_field_to_card_json(card_json: list[dict[str, Any]], field: dict[str, Any]) -> list[dict[str, Any]]:
    """Copy the field values into the card_json dictionary, if the respective
    field names are found to be valid aliases in the card structure.
    """
    for key, aliases in CARD_FIELD_ALIASES.items():
        if field["name"].lower() in aliases:
            card_json[key] = field["value"]
            break
    return card_json


def create_identity_json_structure(record: dict[str, Any]) -> dict[str, Any]:
    """Create an identity dictionary for the Bitwarden JSON structure.

    The identity dictionary contains various personal information fields
    and their values from the mSecure record.
    """
    identity = copy.deepcopy(EMPTY_IDENTITY_JSON)
    # The builder must be initialized with copy.deepcopy(...) for the empty 
    # templates so that each record gets its own, independent dict/list pair.
    # Otherwise, side effects have been observed!

    # Populate the identity structure based on the aliases with the values from the record's fields
    for field in record.get("fields", []):      
        if not isinstance(field, dict):
            continue
        for key, aliases in IDENTITY_FIELD_ALIASES.items():
            if field["name"].lower() in aliases:
                identity[key] = field["value"]
                break
    return identity


def union_set_of_aliases(item_type_code: int) -> set[str]:
    """Create a flattened set of all alias strings contained  in the 
    ??_FIELD_ALIASES constants associated with the given item_type_code.

    This function goes through the dictionaries of sets that form the 
    ??_FIELD_ALIASES constants and creates a union set of them for the 
    purpose of making them easily iterable.
    """
    type_specific_aliases: set[str] = set()
    if item_type_code == 1:
        # Note: LOGIN_FIELD_ALIASES is a dictionary of sets, so we need 
        # to flatten it to a single set of aliases, while URI_ALIASES is 
        # already a set. We can use set().union() and *unpacking of the 
        # .values()to combine them.
        type_specific_aliases = set().union(*LOGIN_FIELD_ALIASES.values(), URI_ALIASES)
    elif item_type_code == 3:
        type_specific_aliases = set().union(*CARD_FIELD_ALIASES.values())
    elif item_type_code == 4:
        type_specific_aliases = set().union(*IDENTITY_FIELD_ALIASES.values())
    return type_specific_aliases


def create_fields_json_structure(record: dict[str, Any], type_specific_aliases: set[str]) -> list[dict[str, Any]]:
    """Create a fields json structure, filtering out any fields that are 
    already represented in the type-specific substructures
    """
    fields_json = []
    # if type_specific_aliases:
    for field in record.get("fields", []):
        # Remove fields that are represented in the type-specific substructures
        if isinstance(field, dict) and str(field.get("name", "")).strip().lower() not in {alias.lower() for alias in type_specific_aliases}:
            field_json = create_single_field_json_structure(field)
            fields_json.append(field_json)
    return fields_json


def create_single_field_json_structure(field: dict[str, Any]) -> dict[str, Any]:
    if field is None or field == {} or not isinstance(field, dict):
        field_json = None
    else:
        field_json = copy.deepcopy(EMPTY_FIELD_JSON)
        field_json["name"] = field["name"] if "name" in field else ""
        field_json["type"] = map_msecure_field_type_to_bitwarden(int(field["type"])) if "type" in field else 0
        field_json["value"] = field["value"] if "value" in field else ""
    return field_json


def map_msecure_field_type_to_bitwarden(msecure_type: int) -> int:
    """Return the Bitwarden field type for a parsed mSecure type.

    Unknown mSecure types default to Bitwarden text fields because they are
    still represented as data and therefore safe for the first converter pass.
    """
    return MSECURE_TO_BITWARDEN_FIELD_TYPE.get(msecure_type, 0)


def map_msecure_item_type_to_bitwarden_type(msecure_type: str) -> str:
    """Map the mSecure item type to the Bitwarden item type.

    The mapping is based on the known mSecure types and their corresponding
    Bitwarden types. Unknown mSecure types default to "login" in Bitwarden.
    """
    for bitwarden_type, msecure_aliases in BITWARDEN_FOR_MSECURE_TYPES.items():
        if msecure_type.lower() in msecure_aliases:
            return bitwarden_type
    return "login"  # Default to login if unknown


#=============================================================================
# Main program: entry point for command-line execution
#=============================================================================
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert an mSecure CSV export to Bitwarden JSON."
    )
    parser.add_argument(
        "input_csv", 
        type=Path, 
        help="path to the mSecure CSV file"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output JSON path (default: input file with a .json extension)",
    )
    args = parser.parse_args(argv)

    output_path = convert_csv_to_bitwarden_json(args.input_csv, args.output)
    print(f"Bitwarden JSON written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
