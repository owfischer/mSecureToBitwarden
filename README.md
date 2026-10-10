# mSecureToBitwarden
This tool converts complex mSecure CSV export files to a JSON file format that can be imported by Bitwarden. In my case, I was able to import more than 300 records with multiple tags and custom fields from mSecure 7 to Bitwarden 2026.08 in one go.

## Export CSV file from mSecure
- In mSecure, go to Settings/Backups/Export and and click on "Export to CSV file".
- Select: All entries, Entries in current view, or Selected entries.
- Don't activate the option "Only export field data..."
- Click on Export
- In the Save As dialogue, select the desired folder and file name.
- Click Save.

## Preparation
- Open the CSV file you have exported with an editor (best choice is Visual Studio Code with extension Rainbow CSV or similar).
- Check for the separator in your CSV file: is it `,` or `;`? Note what you have.
- If there is a header line on top of the file, delete it and save the file.
- The mSecure CSV export uses a very uncommon and difficult to process CSV structure with multiple data in one field `name|type|value,`. Therefore it is not quite straightforward to parse and convert. Note the tag names in the second column (which will be converted to folder names in Bitwarden) and the field names in the subsequent columns.
- According to your language and to the custom fields you may have created in mSecure, you may need to update the word lists in the customisation section in `convert.py`.
- Open `convert.py` in your favourite editor. The constants in the customisation section should contain the most important words in English and German. If your file has field names in a different language, then you need to add your words to the respective constants, for example append `"anmeldung",` in the first line:
```
BITWARDEN_FOR_MSECURE_TYPES = {
    "login": {"login", "anmelden", **"anmeldung",**
              "email-account", "email account", "email-konto", "e-mail-konto",
              "bankkonto", "bank account", 
              "betriebssystem", "operating system",
              "drahtlos-netzwerk", "wireless network", "router settings", "router-einstellungen", "wifi", "wlan",
              "software license", "softwarelizenz", "software-lizenz",
              "sim-karten", "sim card", "sim cards", "telefonkarte", "telefonkarten", 
              "calling card", "voice mail", "voicemail", "Visitenkarte",
              "mitgliedschaft", "membership", "mitgliedschaften", "memberships",
              "registrierungscode", "registration code", "registrierungscodes", "registration codes",
              },
    "secureNote": {"note", "secure note", "sichere notiz", "geheime notizen",
                   "combination" ,"combinations","kombination", "kombinationen", 
                   "geheimzahl", "geheimzahlen", "pin", "pins",
                   "prescription", "prescriptions", "rezept", "rezepte",
                   "vehicle info", "vehicle information", "fahrzeug", "fahrzeuginfo", "fahrzeuginformationen",
                   },
    "card": {"card", "credit card", "bank card", 
             "kreditkarte", "bankkarte", "debit card",
             },
    "identity": {"identity", "passport", "personalausweis", "reisepass", "identität", 
                 "Führerschein", "drivers license", "driver's license",
                 "frequent flyer", "Vielflieger", "reward program", "belohnungsprogramm",
                 "insurance information", "versicherungsinformation",
                 "social security information", "Informationen zur sozialen Sicherheit",
                 "outdoor license", "outdoor-lizenz",
                 },

```

## File conversion:
Use the tool convert.py in a shell; for this you need to have Python installed. It can be used with options:

```python3 convert.py --help```
- Display this help:
```usage: convert.py [-h] [-o OUTPUT] [-s SEPARATOR] [-t TESTFOLDER] input_csv

Convert an mSecure CSV export to Bitwarden JSON.

positional arguments:
  input_csv             Path to the mSecure CSV file

options:
  -h, --help            show this help message and exit
  -o, --output OUTPUT   Output JSON path (default: input file with a .json extension)
  -s, --separator SEPARATOR
                        Separator used in the CSV file (default: ',')
  -t, --testfolder TESTFOLDER
                        Store all items in Bitwarden folder TESTFOLDER (default: no test folder). Use this option for import tests and to avoid messing up your
                        existing Bitwarden folders with undesired items.
```

### Generic use
```python3 convert.py your_mSecure_export_file.csv --separator ";"```
- Read "your_mSecure_export_file.csv" expecting `;` as separator. If you omit the -s|--separator option, `,` is expected as separator in the CSV file.
- Create "your_mSecure_export_file.json" in the same folder. The filename and path remains the same except
- When imported in Bitwarden (do not select an import folder there), all mSecure Tags will be converted to Bitwarden folders and the items will be stored in those folders durting import.

### Determining the output path
```python3 convert.py your_mSecure_export_file.csv --output Bitwarden_import_file.json```
- Specify an output file name or path different from the input file name or path.

### Using a test folder
```python3 convert.py your_mSecure_export_file.csv --testfolder Test -s ";"```
- Read the CSV file with `;` as separator. 
- Create "your_mSecure_export_file.json" in the same folder.
- Ignore the actual tags (folders) given in the CSV file and assign all record items to the folder "Test" only. Recommendable if you already have items in Bitwarden, and you do not want to mess them up with an import trial.

## Import
- In Bitwarden, click File/Import.
- Select the desired vault.
- Do not select a folder, if you want to use the mSecure tags to create the folder names.
- Select the File format Bitwarden (json).
- Select the JSON file you have created in the previous step.
- Click Import.

## Contribute
If you want to improve the code or add features, I encourage you to install pytest and do it with TDD (test driven development). The unit tests are in `test_convert.py` and cover all functions sufficiently, I think. It helped me a great deal when I was developing this program.
