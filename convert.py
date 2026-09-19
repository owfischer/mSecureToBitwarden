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


# Mapping of the 12 mSecure field types to the 4 Bitwarden custom field types.
# In this first pass, only Text (0) and Hidden (1) are used.
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


def map_msecure_field_type_to_bitwarden(msecure_type: int) -> int:
    """Return the Bitwarden field type for a parsed mSecure type.

    Unknown mSecure types default to Bitwarden text fields because they are
    still represented as data and therefore safe for the first converter pass.
    """
    return MSECURE_TO_BITWARDEN_FIELD_TYPE.get(msecure_type, 0)


def is_hidden_msecure_type(msecure_type: int) -> bool:
    """Return True if the mSecure field should become a Bitwarden Hidden field."""
    return map_msecure_field_type_to_bitwarden(msecure_type) == 1


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


def create_dummy_folderId_from_folder_name(folder_name: str) -> str:
    """Create a dummy folderId from the folder name.

    This is a placeholder implementation that generates a UUID based on the
    folder name. In a real implementation, you would want to ensure that the
    folderId is unique and consistent across runs.
    """
    import uuid
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, folder_name))


def demo_mapping() -> None:
    """Small demonstration that the mapping produces the target field types."""
    examples = {
        7: "Username from mSecure -> Text field in Bitwarden",
        8: "Password from mSecure -> Hidden field in Bitwarden",
        12: "Card number from mSecure -> Text field in Bitwarden",
    }
    for key, description in examples.items():
        print(f"{key}: {map_msecure_field_type_to_bitwarden(key)} // {description}")


if __name__ == "__main__":
    demo_mapping()
