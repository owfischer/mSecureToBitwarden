This tool converts complex mSecure CSV export files to a JSON file format that can be imported by Bitwarden.

## Export CSV file from mSecure
- In mSecure, go to Settings/Backups/Export and and click on "Export to CSV file".
- Select: All entries, Entries in current view, or Selected entries.
- Don't activate the option "Only export field data..."
- Click on Export
- In the Save As dialogue, select the desired folder and file name.
- Click Save.

## File conversion:
Use the tool convert.py in a shell; for this you need to have Python installed. It can be used with options:

```python3 convert.py --help```
- Display this help:
[!TIP]
>usage: convert.py [-h] [-o OUTPUT] [-s SEPARATOR] [-t TESTFOLDER] input_csv
>
>Convert an mSecure CSV export to Bitwarden JSON.
>
>positional arguments:
>  input_csv             Path to the mSecure CSV file
>
>options:
>  -h, --help            show this help message and exit
>  -o, --output OUTPUT   Output JSON path (default: input file with a .json extension)
>  -s, --separator SEPARATOR
>                        Separator used in the CSV file (default: ',')
>  -t, --testfolder TESTFOLDER
>                        Store all items in Bitwarden folder TESTFOLDER (default: no test folder). Use this option for import tests and to avoid messing up your
>                        existing Bitwarden folders with undesired items.

```python3 convert.py your_mSecure_export_file.csv --separator ";"```
- Read "your_mSecure_export_file.csv" expecting ";" as separator. If you omit the -s|--separator option, "," is expected as separator in the CSV file.
- Create "your_mSecure_export_file.json" in the same folder. The filename and path remains the same except
- When imported in Bitwarden (do not select an import folder there), all mSecure Tags will be converted to Bitwarden folders and the items will be stored in those folders durting import.

```python3 convert.py your_mSecure_export_file.csv --output Bitwarden_import_file.json```
- Specify an output file name or path different from the input file name or path.

```python3 convert.py your_mSecure_export_file.csv --testfolder Test -s ";"```
- Read the CSV file with ";" as separator. 
- Create "your_mSecure_export_file.json" in the same folder.
- Ignore the actual tags (folders) given in the CSV file and assign all record items to the folder "Test" only. Recommendable if you already have items in Bitwarden, and you do not want to mess them up with an import trial.

## Import
- In Bitwarden, click File/Import.
- Select the desired vault.
- Do not select a folder, if you want to use the mSecure tags to create the folder names.
- Select the File format Bitwarden (json).
- Select the JSON file you have created in the previous step.
- Click Import.

