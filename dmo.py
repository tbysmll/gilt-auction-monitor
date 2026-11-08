"""
dmo.py - gets the UK Debt Management Office's (DMO) outright gilt auction results (report D2.1A) into pandas.

It first tries to download the report straight from the DMO website. The site has bot protection, so the download
is sometimes answered with an HTML "are you a robot?" page instead of the Excel file. When that happens it says so,
tells you how to download the file by hand into data/, and reads the newest file already saved in data/ instead.

Run it with:  python dmo.py
"""

import sys                                         # Lets the script stop early with a clear message (sys.exit)
from datetime import date                          # Today's date, used to name the saved file
from pathlib import Path                           # Handles folder and file paths the same way on Windows and Mac

import pandas as pd                                # Tables of data (like Excel in Python)
import requests                                    # Downloads files from the web

# ---------------------------------------------------------------------------
# Where the data comes from and where it's kept
# ---------------------------------------------------------------------------
DOWNLOAD_URL = ("https://www.dmo.gov.uk/umbraco/surface/DataExport/GetDataExport"  # The DMO's direct export link...
                "?reportCode=D2.1A&exportFormatValue=xls")  # ...for report D2.1A, as an Excel (.xls) file
MANUAL_URL = "https://www.dmo.gov.uk/data/ExportReport?reportCode=D2.1A"  # The page a person can download it from by hand
DATA_DIR = Path(__file__).parent / "data"          # The data/ folder next to this script
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "  # Tells the website we're a normal
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")  # Chrome browser, not a Python script

# Every Excel file starts with one of these "signatures" (its first few bytes), whatever its name says it is
XLS_SIGNATURE = b"\xd0\xcf\x11\xe0"                # Old-style Excel (.xls) files always start with these 4 bytes
XLSX_SIGNATURE = b"PK"                             # New-style Excel (.xlsx) files are zip files, which start with "PK"


def excel_engine(content):
    """Work out whether some bytes are a real Excel file, and if so which reader pandas needs for it.

    content -- the raw bytes of a file (or of a web download)
    Returns "xlrd" for an old-style .xls file, "openpyxl" for a new-style .xlsx file, or None if it isn't Excel at all
    (for example, the DMO's HTML captcha page).
    Exists because a file's name can't be trusted: the captcha page arrives with the same link as the real file.
    """
    if content.startswith(XLS_SIGNATURE):          # Starts like an old-style .xls file...
        return "xlrd"                              # ...so pandas should read it with xlrd
    if content.startswith(XLSX_SIGNATURE):         # Starts like a new-style .xlsx file...
        return "openpyxl"                          # ...so pandas should read it with openpyxl
    return None                                    # Neither: not an Excel file


def download_report():
    """Try to download report D2.1A from the DMO and save it into data/.

    Takes no inputs. Returns the path of the saved file, or None if the download failed or was blocked.
    Exists so the rest of the project always has an up-to-date copy of the auction results when the site allows it.
    """
    try:                                           # Network problems raise errors, so catch them rather than crash
        response = requests.get(DOWNLOAD_URL, headers={"User-Agent": USER_AGENT}, timeout=30)  # Ask for the file;
                                                   # give up after 30 seconds rather than wait forever
    except requests.RequestException as error:     # No internet, site down, timed out, etc.
        print(f"Could not reach the DMO website ({error}).")  # Say what went wrong
        return None                                # Tell the caller the download didn't work

    engine = excel_engine(response.content)        # Is what came back really an Excel file?
    if response.status_code != 200 or engine is None:  # Not "200 OK", or not Excel (e.g. the captcha page)
        print("The DMO website blocked the automatic download (its bot protection sent back a web page,")  # Explain...
        print("not the Excel file). Please download it by hand:")  # ...and say what to do instead
        print(f"  1. Open {MANUAL_URL} in your browser")  # Step 1: the manual download page
        print(f"  2. Save the Excel file into this folder: {DATA_DIR}")  # Step 2: where to put it
        print("  3. Run the script again (until then, the newest saved copy is used)")  # Step 3: try again
        return None                                # Tell the caller the download didn't work

    DATA_DIR.mkdir(exist_ok=True)                  # Create data/ if it doesn't exist yet
    suffix = ".xls" if engine == "xlrd" else ".xlsx"  # Give the file the ending that matches what it really is
    path = DATA_DIR / f"D2.1A_{date.today().isoformat()}{suffix}"  # e.g. data/D2.1A_2026-11-03.xls
    path.write_bytes(response.content)             # Save the downloaded bytes to that file
    print(f"Downloaded the latest auction results to {path}")  # Confirm it worked
    return path                                    # Tell the caller where the file is


def newest_saved_file():
    """Find the most recently saved Excel file in data/.

    Takes no inputs. Returns the path of the newest .xls or .xlsx file in data/, or None if there isn't one.
    Exists as the fallback when the website blocks the download: it uses a copy you downloaded by hand.
    """
    if not DATA_DIR.exists():                      # No data/ folder at all...
        return None                                # ...so there's nothing to fall back on
    files = list(DATA_DIR.glob("*.xls")) + list(DATA_DIR.glob("*.xlsx"))  # Every Excel file in data/
    if not files:                                  # The folder is empty (of Excel files)...
        return None                                # ...so there's nothing to fall back on
    return max(files, key=lambda file: file.stat().st_mtime)  # The one saved most recently (largest modified time)


def data_date(path):
    """Read the "Data Date" the DMO prints in the top-left cell of its reports, e.g. "Data Date: 03-Nov-2026".

    path -- a saved DMO Excel report
    Returns that date as a pandas Timestamp.
    Exists so charts and the README can say exactly how up to date the data is ("Data as of 03 Nov 2026").
    """
    engine = excel_engine(path.read_bytes())       # Which reader pandas needs for this file
    top_left = pd.read_excel(path, header=None, nrows=1, engine=engine).iloc[0, 0]  # Just the first cell of the sheet
    date = pd.to_datetime(str(top_left).replace("Data Date:", "").strip(), format="%d-%b-%Y", errors="coerce")  # e.g.
                                                   # "03-Nov-2026" -> 3 Nov 2026; anything else becomes blank (NaT)
    if pd.isna(date):                              # The cell didn't hold a date in the expected form
        sys.exit(f"Couldn't read the 'Data Date' at the top of {path.name} (found: {top_left!r}).")  # Stop and show it
    return date                                    # The date the DMO produced the report


def load_report(path, header_text="Auction Date"):
    """Read a saved DMO Excel report (e.g. D2.1A) into a pandas table with one row per line of the report.

    path        -- the Excel file to read
    header_text -- a column heading that only appears in the header row; "Auction Date" for the auction results,
                   "Redemption Date" for the maturity files that scoring.py reads
    Returns a DataFrame whose column names are the DMO's own column headings.
    Exists because the DMO puts a few title lines above the real table, so the header row has to be found first.
    """
    engine = excel_engine(path.read_bytes())       # Check the file really is Excel, and which reader it needs
    if engine is None:                             # It isn't (e.g. a captcha page saved by mistake)
        sys.exit(f"{path.name} is not an Excel file. Please download it again from {MANUAL_URL}")  # Stop with a clear message

    raw = pd.read_excel(path, header=None, engine=engine)  # Read every cell as-is, without guessing the header row
    is_header = raw.apply(lambda row: row.astype(str).str.contains(header_text, case=False).any(), axis=1)  # True
                                                   # for any row with the header_text heading in it
    if not is_header.any():                        # No such row: the layout isn't what we expected
        print(raw.head(15).to_string())            # Show the top of the sheet so we can see what it looks like...
        sys.exit(f"Couldn't find the header row (no '{header_text}' column) in {path.name}. "  # ...and stop,
                 "Please paste the rows above to Claude.")  # saying which file and heading

    header_row = is_header.idxmax()                # The number of the first row that contains header_text
    table = pd.read_excel(path, header=header_row, engine=engine)  # Read again, using that row as the column names
    table = table.dropna(how="all")                # Drop completely empty rows (e.g. blank lines or notes at the bottom)
    table = table.dropna(axis=1, how="all")        # Drop completely empty columns
    table.columns = [" ".join(str(name).split()) for name in table.columns]  # Tidy the headings: the DMO splits them
                                                   # over several lines, so swap line breaks and double spaces for one space
    return table                                   # One row per auction


def sort_by_date(table):
    """Put the auctions in date order, oldest first.

    table -- the auction table from load_report()
    Returns the same table, sorted by its auction-date column (or unchanged if no date column can be found).
    Exists because the DMO may list the newest auctions first, and we want "the last 10" to mean the 10 most recent.
    """
    date_columns = [name for name in table.columns if "date" in name.lower()]  # Headings with "date" in them
    if not date_columns:                           # No date column found...
        print("No date column found, so the auctions are shown in the file's own order.")  # ...say so
        return table                               # ...and leave the order alone
    date_column = date_columns[0]                  # Use the first one (normally the auction date)
    table[date_column] = pd.to_datetime(table[date_column], dayfirst=True, errors="coerce")  # Make sure it holds real
                                                   # dates (UK order: day first); anything unreadable becomes blank (NaT)
    table = table.dropna(subset=[date_column])     # Drop rows without a date (e.g. footnotes under the table)
    return table.sort_values(date_column).reset_index(drop=True)  # Oldest first; renumber the rows 0, 1, 2...


def get_auction_file():
    """Get the auction results file: download it if the DMO allows, otherwise use the newest copy saved in data/.

    Takes no inputs. Returns the path of the file to use.
    Stops with a clear message if the download is blocked and there's no saved copy either.
    """
    path = download_report()                       # Try the website first
    if path is None:                               # Blocked or failed...
        path = newest_saved_file()                 # ...so use the newest copy saved in data/
        if path is None:                           # Nothing there either...
            sys.exit("\nNo saved copy in data/ yet, so there's nothing to load. Download it by hand (see above).")  # ...stop
        print(f"\nUsing the newest saved copy instead: {path.name}")  # Say which file is being used
    return path                                    # The file to read


def main():
    """Get the auction results (downloading them if the site allows), then show the columns and the last 10 auctions.

    Takes no inputs. Returns nothing; prints to the screen.
    """
    path = get_auction_file()                      # Downloaded, or the newest saved copy
    auctions = sort_by_date(load_report(path))     # Read the file and put the auctions in date order

    pd.set_option("display.width", 250)            # Let printed tables be wide, so columns don't wrap onto new lines
    pd.set_option("display.max_columns", None)     # Show every column, not "..." in the middle

    print(f"\n{len(auctions)} auctions, with these {len(auctions.columns)} columns:")  # How much data there is
    for number, name in enumerate(auctions.columns, start=1):  # Each column, numbered from 1
        print(f"  {number:>2}. {name}  [{auctions[name].dtype}]")  # Its name and data type (number, text, date...)

    print("\nThe last 10 auctions:")               # Heading for the table below
    print(auctions.tail(10).to_string())           # The 10 most recent auctions, every column


if __name__ == "__main__":                         # Only runs when you type "python dmo.py" (not when imported)
    main()                                         # Do everything above
