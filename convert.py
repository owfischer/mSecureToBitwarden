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
    """
    records: list[dict[str, Any]] = []

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row:
                continue

            # The first four columns are present in the source format.
            # We keep the parser here deliberately simple and later expand it
            # once the row splitting and field extraction are implemented.
            record = {
                "raw": row,
                "name_id": row[0] if row else "",
                "type": row[1] if len(row) > 1 else "",
                "folder": row[2] if len(row) > 2 else "",
                "notes": row[3] if len(row) > 3 else "",
            }
            records.append(record)

    return records


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
