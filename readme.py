"""
readme.py - writes README.md, the project's front page on GitHub, for someone who has never seen the project.

It's rewritten on every run of main.py, so the longer-run table and the "data as of" date are always current. Most of
the text is fixed, but the numbers in it (the bucket limits, cut-offs, report codes and download links) are read from
scoring.py, analysis.py and dmo.py, so the README can't drift out of step with the code.
Don't edit README.md by hand: change this file (or config.py) instead.
"""

from pathlib import Path                           # Handles folder and file paths the same way on Windows and Mac

import analysis                                    # Our own analysis.py: the longer-run comparison's headline and table
import config                                      # Our own config.py: the author's name, LinkedIn and GitHub links
import dmo                                         # Our own dmo.py: the three DMO reports, their codes and folders
import scoring                                     # Our own scoring.py: the bucket limits, peer window and cut-offs

PROJECT_DIR = Path(__file__).parent                # The folder this script is in
README_FILE = PROJECT_DIR / "README.md"            # GitHub shows this file on the repo's front page
SCREENSHOT = "docs/screenshot.png"                 # A picture of the website, shown at the top of the README
CLONE_URL = config.REPO_URL + ".git"               # The address "git clone" needs, e.g. https://github.com/.../x.git
FOLDER_NAME = config.REPO_URL.rstrip("/").split("/")[-1]  # The folder "git clone" creates, e.g. "gilt-auction-monitor"


def markdown_table(table):
    """Write a pandas table as a Markdown table (the |-separated format GitHub displays as a grid).

    table -- any pandas DataFrame
    Returns the table as Markdown text.
    Exists to avoid needing an extra library ("tabulate") just for this.
    """
    header = "| " + " | ".join(str(name) for name in table.columns) + " |"  # e.g. "| Number in draft | Check |"
    divider = "|" + "---|" * len(table.columns)    # The line under the headings that makes it a table
    rows = ["| " + " | ".join(str(value) for value in row) + " |" for row in table.itertuples(index=False)]  # One line
                                                   # per row of the table
    return "\n".join([header, divider] + rows)     # All lines, one after another


def download_table():
    """The table of the three DMO reports to download by hand: name, code, link and folder.

    Takes no inputs. Returns Markdown lines, built from dmo.REPORTS so they always match what main.py asks for.
    """
    lines = ["| Report | Code | Download page | Save in |", "|---|---|---|---|"]  # The headings and divider
    for key, report in dmo.REPORTS.items():        # Each of the three reports
        page = dmo.PAGE_URL.format(code=report["code"])  # Its DMO download page
        folder = dmo.short_path(dmo.report_folder(key, dmo.DATA_DIR))  # Where it goes, e.g. "data/maturities/"
        lines.append(f"| {report['name']} | {report['code']} | [{page}]({page}) | `{folder}` |")  # One row
    return lines                                   # The table's lines


def write_readme(comparison, data_date):
    """Write README.md.

    comparison -- the standard longer-run comparison (2015-21 vs 2023-25), from analysis.compare_periods()
    data_date  -- the date the DMO produced the data (a pandas Timestamp)
    Returns the path of README.md.
    """
    low, high = scoring.SHORT_LIMIT, scoring.LONG_LIMIT  # The bucket limits: 7 and 15 years
    early, late = (analysis.period_label(p) for p in analysis.PERIODS)  # e.g. "2015-21" and "2023-25"
    built_by = (f"**[{config.AUTHOR}]({config.LINKEDIN_URL})** on LinkedIn" if config.LINKEDIN_URL  # A link if there
                else f"**{config.AUTHOR}**")       # is one, otherwise just the name

    lines = [                                      # The README, one line of Markdown per item
        "# Gilt Auction Monitor",                  # Title
        "",                                        # Blank line (Markdown needs these between blocks)
        "Scores every UK government bond (gilt) auction since 1998 for investor demand: how much was bid (cover) "  # Line 1
        "and how tightly the bids were priced (tail), compared with similar auctions over the previous three years.",  # of 2
        "It builds a one-page website with charts, a longer-run comparison and an optional Claude-drafted review "  # Line 2
        "of the latest auction.",                  # of 2
        "",                                        # Blank line
        f"[![The Gilt Auction Monitor website]({SCREENSHOT})]({config.PAGES_URL})",  # The screenshot, linking to the site
        "",                                        # Blank line
        f"**Live site:** [{config.PAGES_URL}]({config.PAGES_URL}) · data as of {data_date:%d %b %Y}",  # Link and date
        "",                                        # Blank line
        "## Quick start",                          # Section heading
        "",                                        # Blank line
        "You need [Python](https://www.python.org/downloads/) 3.12 or later and [Git](https://git-scm.com/). "  # What's
        "On a Mac or Linux, type `python3` where it says `python`.",  # needed
        "",                                        # Blank line
        "```",                                     # Start of a code block (shown in a monospaced box)
        f"git clone {CLONE_URL}",                  # 1. Copy the project to your computer
        f"cd {FOLDER_NAME}",                       # 2. Go into its folder
        "python -m venv .venv",                    # 3. Create a virtual environment (a private set of libraries)
        ".venv\\Scripts\\activate            # Windows",  # 4a. Switch it on (Windows; "\\" writes one backslash)
        "source .venv/bin/activate         # Mac or Linux",  # 4b. Switch it on (Mac or Linux)
        "pip install -r requirements.txt",         # 5. Install the exact library versions it was tested with
        "python main.py --sample           # try it with the bundled data: nothing is downloaded",  # 6. Sample run
        "python main.py                    # live data: downloads the latest DMO reports",  # 7. Live run
        "```",                                     # End of the code block
        "",                                        # Blank line
        "Then open `docs/index.html` in your browser. Each run also writes `output/summary.md` (a record of the "  # Where
        "run) and `output/comparison.md` (the longer-run table).",  # the results are
        "",                                        # Blank line
        "## If the download is blocked",           # Section heading
        "",                                        # Blank line
        "The DMO's website has bot protection, so it often refuses automatic downloads. When that happens, "  # What
        "`python main.py` lists exactly which files to download by hand and carries on with the newest copies "  # happens
        "already saved. The tool needs these three reports:",  # and what's needed
        "",                                        # Blank line
    ]                                              # End of the list
    lines += download_table()                      # The three reports, with links and folders
    lines += [                                     # What to do with them
        "",                                        # Blank line
        "Open each page, export the report as Excel, and save the file in the folder shown. The file name doesn't "  # How
        "matter: each file is recognised by the title inside it. Then run `python main.py --offline` to use them "  # to do
        "without trying the download again.",      # it
        "",                                        # Blank line
        "## Command-line options",                 # Section heading
        "",                                        # Blank line
        "| Option | What it does | Example |",     # The options table's headings...
        "|---|---|---|",                           # ...and its divider line
        "| *(none)* | Downloads the data, scores every auction, draws the charts and writes the website, summary "  # No
        "and README. No Claude needed. | `python main.py` |",  # options
        "| `--sample` | Uses the copies of the three reports in `sample_data/` (data as of 03 Nov 2026) instead of "  # --sample
        "downloading. | `python main.py --sample` |",  # and its example
        "| `--offline` | Skips the download and uses the reports already saved in `data/`. | "  # --offline...
        "`python main.py --offline` |",            # ...and its example
        "| `--review` | Also asks Claude to draft a short review of the latest auction, then checks every auction "  # --review
        "fact it quotes against the data. Needs [Claude Code](https://claude.com/claude-code) installed and logged "  # and
        "in; without it, the run carries on with no review. | `python main.py --review` |",  # what it needs
        f"| `--compare` | Compares any two periods (default {analysis.PERIODS[0][0]}-{analysis.PERIODS[0][1]} and "  # --compare
        f"{analysis.PERIODS[1][0]}-{analysis.PERIODS[1][1]}). Each period needs at least {analysis.MIN_AUCTIONS} "  # and its
        "auctions. | `python main.py --compare 2010-2014 2023-2025` |",  # rule and example
        "| `--bucket` | Limits the comparison to one maturity bucket: `short`, `medium`, `long` or `all` "  # --bucket
        "(default). | `python main.py --compare 2010-2014 2023-2025 --bucket long` |",  # and its example
        "",                                        # Blank line
        "Options can be combined, e.g. `python main.py --offline --review`. `python main.py --help` lists them all. "  # How to
        "`--compare` and `--bucket` change the printed table and `output/comparison.md`; the website always shows "  # combine
        "the standard comparison below.",          # them
        "",                                        # Blank line
        "## How the scoring works",                # Section heading
        "",                                        # Blank line
        "When the government borrows, the DMO auctions gilts to investors. Two numbers from each auction show how "  # Why
        "keen investors were:",                    # these two numbers
        "",                                        # Blank line
        "- **Cover** (the bid-to-cover ratio) is the amount bid divided by the amount sold. A cover of 3 means £3 "  # Cover
        "was bid for every £1 of gilts on offer. Higher means more demand.",  # in plain English
        "- **Tail** is how far the weakest accepted bid was from the average one, measured in yield: the yield at "  # Tail
        "the lowest accepted price minus the yield at the average accepted price, in basis points (1bp = 0.01%). "  # in plain
        "A narrow tail means bidders agreed on the price; a wide one means some only bought at a discount.",  # English
        "",                                        # Blank line
        "Each auction is then compared with others like it:",  # The method, step by step
        "",                                        # Blank line
        f"1. **Same maturity.** Gilts are grouped by years left until they're repaid, using the DMO's buckets: "  # Step 1
        f"short (under {low} years), medium ({low} to {high}) and long (over {high}). Index-linked gilts are left "  # buckets
        "out: every winning bidder pays the same price, so there's no tail.",  # (and why linkers are excluded)
        f"2. **Same recent period.** An auction's peers are the auctions in its bucket over the previous "  # Step 2
        f"{scoring.WINDOW_YEARS} years (at least {scoring.MIN_PEERS} are needed to score it).",  # peers
        "3. **Percentiles.** The cover percentile is the share of peers with a lower cover; the tail percentile is "  # Step 3
        "the share with a wider tail. Ties count as half. For both, higher is better.",  # percentiles
        f"4. **One rule for the label.** *Strong* if both percentiles are at least {scoring.STRONG_CUTOFF}; *weak* "  # Step 4
        f"if either is {scoring.WEAK_CUTOFF} or lower; otherwise *normal*. One bad measure is enough to call an "  # the
        "auction weak.",                           # label
        "",                                        # Blank line
        "## Longer-run view",                      # Section heading
        "",                                        # Blank line
        f"Conventional auctions in {early} compared with {late}:",  # What the table compares
        "",                                        # Blank line
        markdown_table(analysis.formatted(comparison)),  # The table, overall and by bucket, decimals lined up
        "",                                        # Blank line
        analysis.headline(comparison),             # The one-sentence comparison
        "",                                        # Blank line
        "Each period runs from January of its first year to December of its last. Medians are the middle value, so "  # How
        "a single unusual auction can't move them much. Try other periods with `--compare`.",  # to read it
        "",                                        # Blank line
        "## Data source",                          # Section heading
        "",                                        # Blank line
        "All data comes from the [UK Debt Management Office (DMO)](https://www.dmo.gov.uk/data/): the auction "  # Credit
        "results are series **D2.1A**, [Outright Gilt Auctions](https://www.dmo.gov.uk/data/ExportReport?reportCode=D2.1A), "  # D2.1A
        "and the redemption dates come from **D1A** (Gilts in Issue) and **D1C** (Redemption Details of Redeemed "  # and the
        "Gilts). `sample_data/` holds unchanged copies of the three reports as of 03 Nov 2026. The code is MIT "  # others
        "licensed (see `LICENSE`); that licence covers the code only, not the DMO's data.",  # licence scope
        "",                                        # Blank line
        f"## Built by {config.AUTHOR}",            # Section heading
        "",                                        # Blank line
        f"Built by {built_by}. Suggestions and bug reports are welcome as "  # Who made it (with LinkedIn, if set)...
        f"[GitHub issues]({config.REPO_URL}/issues).",  # ...and where to send feedback
        "",                                        # Blank line
        "**Make your own copy:** click **Use this template** at the top of the GitHub page, then put your own "  # How to
        "name and links in `config.py`.",          # reuse it
        "",                                        # Blank line
        "*For learning purposes; not investment advice.*",  # The disclaimer
    ]                                              # End of the list
    README_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")  # Save it (UTF-8, so "£" and "·" are kept)
    return README_FILE                             # Tell the caller where it went
