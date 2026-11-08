"""
dmo.py - gets the three UK Debt Management Office (DMO) reports the tool needs, and reads them into pandas.

  Outright Gilt Auctions (D2.1A)                -> data/            every gilt auction's results
  Gilts in Issue (D1A)                          -> data/maturities/ redemption dates of gilts still in issue
  Redemption Details of Redeemed Gilts (D1C)    -> data/maturities/ redemption dates of gilts already repaid

It tries to download each report from the DMO website. The site has bot protection, so a download is often answered
with an HTML "are you a robot?" page instead of the Excel file. That doesn't crash anything: it prints one message
listing exactly which files to download by hand, where from, and which folder to save them in, then uses the newest
copy already saved in that folder.

Files are recognised by the title line inside them (e.g. "RESULTS OF OUTRIGHT GILT AUCTIONS"), not by their file
name, so whatever a downloaded file is called, the right one is used.

Every path is built from the project folder (the folder this file is in), so the tool runs wherever it's copied to.

Run it with:  python dmo.py
"""

import sys                                         # Lets the script stop early with a clear message (sys.exit)
from datetime import date                          # Today's date, used to name downloaded files
from pathlib import Path                           # Handles folder and file paths the same way on Windows and Mac

import pandas as pd                                # Tables of data (like Excel in Python)
import requests                                    # Downloads files from the web

# ---------------------------------------------------------------------------
# Where the data comes from and where it's kept (all relative to the project folder)
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent      # The project folder: the folder this file is in (resolve() gives its
                                                   # full form, so other paths can be shown relative to it)
DATA_DIR = PROJECT_DIR / "data"                    # Where downloaded (or hand-saved) DMO reports live
SAMPLE_DIR = PROJECT_DIR / "sample_data"           # A copy of the three reports, so the tool works straight after cloning
EXPORT_URL = ("https://www.dmo.gov.uk/umbraco/surface/DataExport/GetDataExport"  # The DMO's direct export link,
              "?reportCode={code}&exportFormatValue=xls")  # with {code} filled in, e.g. D2.1A; asks for Excel (.xls)
PAGE_URL = "https://www.dmo.gov.uk/data/ExportReport?reportCode={code}"  # The page a person downloads a report from
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "  # Tells the website we're a normal
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")  # Chrome browser, not a Python script

REPORTS = {                                        # The three reports: a short key for each, used throughout the code
    "auctions": {"name": "Outright Gilt Auctions", "code": "D2.1A",  # Every gilt auction's results...
                 "folder": ".", "title": "OUTRIGHT GILT AUCTIONS"},  # ...saved in data/ itself; its title line says this
    "in_issue": {"name": "Gilts in Issue", "code": "D1A",  # Gilts still in issue, with redemption dates...
                 "folder": "maturities", "title": "GILTS IN ISSUE"},  # ...saved in data/maturities/
    "redeemed": {"name": "Redemption Details of Redeemed Gilts", "code": "D1C",  # Gilts already repaid...
                 "folder": "maturities", "title": "GILT REDEMPTIONS"},  # ...saved in data/maturities/
}                                                  # End of the dictionary

# Every Excel file starts with one of these "signatures" (its first few bytes), whatever its name says it is
XLS_SIGNATURE = b"\xd0\xcf\x11\xe0"                # Old-style Excel (.xls) files always start with these 4 bytes
XLSX_SIGNATURE = b"PK"                             # New-style Excel (.xlsx) files are zip files, which start with "PK"

# Which folder this run reads from: data/ normally, sample_data/ with --sample (set by use_folder())
active_dir = DATA_DIR                              # Starts as data/


def use_folder(folder):
    """Choose which folder this run reads the reports from (data/ normally, sample_data/ for --sample).

    folder -- DATA_DIR or SAMPLE_DIR
    Returns nothing.
    Exists so the choice is made once, here, and every other file (scoring.py, charts.py...) follows it.
    """
    global active_dir                              # "global": change the active_dir defined above, not a new local one
    active_dir = folder                            # From now on, find_report() looks in this folder


def short_path(path):
    """Write a path relative to the project folder, e.g. "data/maturities/", for messages.

    path -- any path inside the project folder
    Returns it as short text with forward slashes, so messages look the same on every computer.
    """
    return path.relative_to(PROJECT_DIR).as_posix() + ("/" if path.is_dir() or not path.suffix else "")  # e.g. "data/"


def report_folder(key, base=None):
    """The folder one report belongs in.

    key  -- "auctions", "in_issue" or "redeemed"
    base -- the data folder to use (default: this run's active folder)
    Returns e.g. data/maturities/ for "in_issue".
    """
    return ((base or active_dir) / REPORTS[key]["folder"]).resolve()  # e.g. data/ + "maturities"; resolve() tidies "/."


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


def report_title(path):
    """Read the title line at the top of a DMO report, e.g. "Data Date: 03-Nov-2026 GILT MARKET GILTS IN ISSUE ...".

    path -- an Excel file
    Returns the text of its first rows, in capitals, or "" if it isn't a readable Excel file.
    Exists so a file is recognised by what it contains, not by what it's called.
    """
    engine = excel_engine(path.read_bytes())       # Is it really Excel, and which reader does it need?
    if engine is None:                             # Not Excel (e.g. a captcha page saved by mistake)...
        return ""                                  # ...so it has no title we can use
    try:                                           # A damaged file can fail to open...
        top = pd.read_excel(path, header=None, nrows=3, engine=engine)  # The first three rows, as they are
    except Exception:                              # ...in which case...
        return ""                                  # ...treat it as having no title, so it's skipped
    return " ".join(str(cell) for cell in top.to_numpy().ravel() if pd.notna(cell)).upper()  # All non-blank cells as one
                                                   # line of capitals, e.g. "... RESULTS OF OUTRIGHT GILT AUCTIONS"


def find_report(key, base=None):
    """Find the newest saved copy of one report.

    key  -- "auctions", "in_issue" or "redeemed"
    base -- the data folder to look in (default: this run's active folder)
    Returns the path of the newest Excel file in the report's folder whose title line matches it, or None if there
    isn't one.
    """
    folder = report_folder(key, base)              # e.g. data/maturities/
    if not folder.exists():                        # No such folder yet...
        return None                                # ...so no saved copy
    files = list(folder.glob("*.xls")) + list(folder.glob("*.xlsx"))  # Every Excel file directly in that folder
    matching = [f for f in files if REPORTS[key]["title"] in report_title(f)]  # Only those that are this report
    if not matching:                               # None of them is this report...
        return None                                # ...so no saved copy
    return max(matching, key=lambda file: file.stat().st_mtime)  # The one saved most recently (largest modified time)


def saved_report(key):
    """Like find_report(), but stops with a clear message if the report has no saved copy.

    key -- "auctions", "in_issue" or "redeemed"
    Returns the path of the newest saved copy in this run's active folder.
    Exists for the files that can be run on their own (python scoring.py, charts.py...), which don't download.
    """
    path = find_report(key)                        # The newest saved copy, if any
    if path is None:                               # None at all...
        report = REPORTS[key]                      # ...this report's details
        sys.exit(f"No saved copy of {report['name']} ({report['code']}) in {short_path(report_folder(key))}. "  # Say
                 f"Run python main.py to download it (or python main.py --sample to use the sample data).")  # what to do
    return path                                    # The file to read


def download_report(key, session):
    """Try to download one report from the DMO and save it into its folder under data/.

    key     -- "auctions", "in_issue" or "redeemed"
    session -- a requests.Session, so the three downloads share one connection and set of headers
    Returns True if a real Excel file was downloaded and saved, False if the DMO blocked it or couldn't be reached.
    Never crashes: every problem just means False, and the caller explains what to do.
    """
    report = REPORTS[key]                          # This report's name, code, folder and title
    try:                                           # Network problems raise errors, so catch them rather than crash
        response = session.get(EXPORT_URL.format(code=report["code"]), timeout=30)  # Ask for the file; give up after 30s
    except requests.RequestException:              # No internet, site down, timed out, etc.
        return False                               # Didn't work: the caller will list it for downloading by hand
    engine = excel_engine(response.content)        # Is what came back really an Excel file?
    if response.status_code != 200 or engine is None:  # Not "200 OK", or not Excel (e.g. the captcha page)...
        return False                               # ...didn't work either
    folder = report_folder(key, DATA_DIR)          # Downloads always go into data/ (never into sample_data/)
    folder.mkdir(parents=True, exist_ok=True)      # Create the folder if it doesn't exist yet
    suffix = ".xls" if engine == "xlrd" else ".xlsx"  # Give the file the ending that matches what it really is
    path = folder / f"{date.today():%Y%m%d} - {report['name']}{suffix}"  # e.g. data/20261108 - Outright Gilt Auctions.xls
    path.write_bytes(response.content)             # Save the downloaded bytes to that file
    if report["title"] not in report_title(path):  # It's Excel, but not the report we asked for (unlikely)...
        path.unlink()                              # ...so delete it rather than leave a misleading file
        return False                               # ...and treat it as a failed download
    print(f"Downloaded {report['name']} ({report['code']}) to {short_path(path)}")  # Confirm it worked
    return True                                    # Success


def manual_download_message(keys):
    """Print one message listing the reports to download by hand: name, page link and folder for each.

    keys -- the reports whose download failed, e.g. ["auctions", "redeemed"]
    Returns nothing; prints to the screen.
    """
    print(f"\nThe DMO website's bot protection blocked the automatic download of {len(keys)} of the "  # What happened...
          f"{len(REPORTS)} reports.")              # ...in one line
    print("Please download these by hand: open each page, export it as Excel, and save the file in the folder shown.")  # What to do
    for key in keys:                               # Each report that needs downloading by hand...
        report = REPORTS[key]                      # ...its details
        print(f"  - {report['name']} ({report['code']})")  # Its name and code
        print(f"      page:    {PAGE_URL.format(code=report['code'])}")  # Where to download it from
        print(f"      save in: {short_path(report_folder(key, DATA_DIR))}")  # Which folder to save it in
    print("Until then, the newest copy already saved in each folder is used.")  # What happens meanwhile


def get_data(offline=False, sample=False):
    """Get all three reports: download them if the DMO allows, otherwise use the newest saved copies.

    offline -- True to skip downloading and use whatever is already in data/ (the --offline option)
    sample  -- True to use the copies in sample_data/ instead of data/, without downloading (the --sample option)
    Returns {key: path} for the three reports, e.g. {"auctions": data/20261103 - Outright Gilt Auctions.xls, ...}.
    Stops with a clear message if any report has no saved copy at all.
    """
    if sample:                                     # --sample...
        use_folder(SAMPLE_DIR)                     # ...read from sample_data/...
        offline = True                             # ...and never download over it
        print(f"Using the sample data in {short_path(SAMPLE_DIR)} (nothing is downloaded).")  # Say so
    else:                                          # Otherwise...
        use_folder(DATA_DIR)                       # ...read from data/

    if offline and not sample:                     # --offline: no downloading
        print(f"Offline: using the reports already saved in {short_path(DATA_DIR)} (nothing is downloaded).")  # Say so
    if not offline:                                # Try the website
        session = requests.Session()               # One connection for all three downloads
        session.headers["User-Agent"] = USER_AGENT  # Look like a normal browser
        blocked = [key for key in REPORTS if not download_report(key, session)]  # Try each; keep the ones that failed
        if blocked:                                # Any failed...
            manual_download_message(blocked)       # ...print one message saying exactly what to do

    files = {key: find_report(key) for key in REPORTS}  # The newest saved copy of each report
    missing = [key for key, path in files.items() if path is None]  # Reports with no copy at all
    if missing:                                    # Can't run without all three...
        lines = [f"\nNo saved copy of {len(missing)} report(s) in {short_path(active_dir)}, so the tool can't run:"]  # Say so
        for key in missing:                        # Each missing report...
            report = REPORTS[key]                  # ...its details
            lines.append(f"  - {report['name']} ({report['code']}): download from "  # ...its name, where to get it...
                         f"{PAGE_URL.format(code=report['code'])} and save in {short_path(report_folder(key))}")  # ...and where to put it
        lines.append("To try the tool without downloading anything, run:  python main.py --sample")  # The easy way out
        sys.exit("\n".join(lines))                 # Stop, showing the whole message

    for key, path in files.items():                # Each report...
        print(f"Using {REPORTS[key]['name']}: {short_path(path)}")  # ...say which file is being used
    return files                                   # The three files


def bids_file():
    """Where this run's hand-copied amounts bid are kept: bids_check.csv in the active folder.

    Takes no inputs. Returns e.g. data/bids_check.csv (or sample_data/bids_check.csv with --sample).
    """
    return active_dir / "bids_check.csv"           # Next to the auction results


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
        sys.exit(f"{path.name} is not an Excel file. Please download it again from the DMO website.")  # Stop clearly

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


def main():
    """Get the three reports (downloading them if the site allows), then show the auction file's columns and last 10
    auctions.

    Takes no inputs. Returns nothing; prints to the screen.
    """
    files = get_data()                             # Downloaded, or the newest saved copies
    auctions = sort_by_date(load_report(files["auctions"]))  # Read the auction results and put them in date order

    pd.set_option("display.width", 250)            # Let printed tables be wide, so columns don't wrap onto new lines
    pd.set_option("display.max_columns", None)     # Show every column, not "..." in the middle

    print(f"\n{len(auctions)} auctions, with these {len(auctions.columns)} columns:")  # How much data there is
    for number, name in enumerate(auctions.columns, start=1):  # Each column, numbered from 1
        print(f"  {number:>2}. {name}  [{auctions[name].dtype}]")  # Its name and data type (number, text, date...)

    print("\nThe last 10 auctions:")               # Heading for the table below
    print(auctions.tail(10).to_string())           # The 10 most recent auctions, every column


if __name__ == "__main__":                         # Only runs when you type "python dmo.py" (not when imported)
    main()                                         # Do everything above
