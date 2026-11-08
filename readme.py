"""
readme.py - writes README.md, the project's front page on GitHub, from the latest results.

It's rewritten on every run of main.py, so the scores, charts, review and longer-run view on GitHub are always the
latest. The Method, Data challenges and My read sections reuse website.py's text, so the README and the website
never disagree. Don't edit README.md by hand: change this file (or my_read.md) instead.
"""

from pathlib import Path                           # Handles folder and file paths the same way on Windows and Mac

import analysis                                    # Our own analysis.py: the longer-run comparison's headline sentence
import charts                                      # Our own charts.py: finds the latest scored auction
import review                                      # Our own review.py: the fact-check result, worded the same everywhere
import scoring                                     # Our own scoring.py: column names
import website                                     # Our own website.py: the Method, Data challenges and My read text

PROJECT_DIR = Path(__file__).parent                # The folder this script is in
README_FILE = PROJECT_DIR / "README.md"            # GitHub shows this file on the repo's front page
PAGES_URL = "https://tbysmll.github.io/gilt-auction-monitor/"  # The live website, once GitHub Pages is switched on


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


def write_readme(scored, result, chart_list, data_date, comparison):
    """Write README.md: summary, latest auction, charts, Claude-drafted review, longer-run view, method, data
    challenges, my read, and setup instructions.

    scored     -- the scored table from scoring.load_scored()
    result     -- the review step's results, from review.draft_review()
    chart_list -- the charts' titles, subtitles, sources and paths, from charts.make_charts()
    data_date  -- the date the DMO produced the data (a pandas Timestamp)
    comparison -- the longer-run comparison, from analysis.compare_periods()
    Returns the path of README.md.
    """
    latest = charts.latest_scored(scored)          # The auction the README is about
    passed, verdict = review.verification_text(result["checks"])  # e.g. (True, "Numbers verified ...: 8 of 8 facts matched")
    my_read = website.read_my_read()               # Toby's own view, as paragraphs (empty if not written yet)

    lines = [                                      # The README, one line of Markdown per item
        "# Gilt Auction Monitor",                  # Title
        "",                                        # Blank line (Markdown needs these between blocks)
        f"Scores every UK government bond (gilt) auction held by the Debt Management Office (DMO) for demand, and "  # What
        f"drafts a short review of the latest one with Claude. By {website.AUTHOR}.",  # the project does, and who made it
        "",                                        # Blank line
        f"**Live page: [{PAGES_URL}]({PAGES_URL})** · Data as of {data_date:%d %b %Y}",  # Link to the site, and data date
        "",                                        # Blank line
        "Each conventional gilt auction is scored on two measures of demand, compared with auctions of similar "  # The
        "maturity over the previous three years:",  # idea in one sentence
        "",                                        # Blank line
        "- **Cover** (bid-to-cover ratio): amount bid divided by amount sold. Higher means more demand.",  # Measure 1
        "- **Tail**: yield at the lowest accepted price minus yield at the average accepted price, in basis points "  # Measure
        "(1bp = 0.01%). Narrower means bids were bunched together: steadier demand.",  # 2
        "",                                        # Blank line
        f"## Latest auction: {latest['Gilt Name']}, {latest['Auction Date']:%d %b %Y}",  # Section heading
        "",                                        # Blank line
        "| Measure | Value | Compared with peers |",  # The scores table's headings...
        "|---|---|---|",                           # ...and its divider line
        f"| Verdict | **{latest['Label']}** | strong if both percentiles ≥ {scoring.STRONG_CUTOFF}; weak if either "  # Label
        f"≤ {scoring.WEAK_CUTOFF} |",              # and the rule
        f"| Cover | {latest[scoring.COVER]:.2f}x | higher than {latest['Cover Pct']:.0f}% of peers |",  # Cover
        f"| Tail | {latest[scoring.TAIL]:.1f}bp | narrower than {latest['Tail Pct']:.0f}% of peers |",  # Tail
        f"| Yield at average price | {latest['Yield at AAP (%)']:.3f}% | |",  # Yield
        f"| Amount sold | £{latest[scoring.SOLD]:,.0f}m nominal | |",  # Amount sold
        f"| Bucket | {latest['Bucket']} ({latest['Years to Maturity']:.1f} years to maturity) | "  # Bucket, and the peer
        f"{latest['Peers']} peers in the previous {scoring.WINDOW_YEARS} years |",  # group it was compared with
        "",                                        # Blank line
        "## Latest charts",                        # Section heading
    ]                                              # End of the list
    for chart in chart_list:                       # Each chart...
        relative = chart["path"].relative_to(PROJECT_DIR).as_posix()  # ...its path from the README, e.g.
                                                   # docs/charts/cover_history.svg (forward slashes for the web)
        lines += ["", f"**{chart['title']}**", "",  # Its numbered takeaway title in bold
                  f"![{chart['title']}]({relative})", "",  # The image
                  f"{chart['subtitle']} {chart['source']}"]  # Its subtitle and source line underneath

    lines += [                                     # The Claude-drafted review
        "",                                        # Blank line
        "## Claude-drafted review",                # Section heading
        "",                                        # Blank line
        "Drafted by Claude from the latest auction's facts and scores only, with no other data or tools; I check "  # What
        "and rewrite it.",                         # it is
        "",                                        # Blank line
        f"> {result['draft']}",                    # The draft, shown as a quote
        "",                                        # Blank line
        f"**{verdict}.**" if passed else f"**⚠ {verdict}.**",  # The fact check: a plain result, or a marked warning
        "",                                        # Blank line
        "## Longer-run view",                      # Section heading
        "",                                        # Blank line
        analysis.headline(comparison),             # The one-sentence comparison
        "",                                        # Blank line
        markdown_table(analysis.formatted(comparison)),  # The full table, overall and by bucket, decimals lined up
        "",                                        # Blank line
        "Conventional auctions only; each period runs from January of its first year to December of its last. "  # How
        "Medians are the middle value, so a single unusual auction can't move them much.",  # to read it
        "",                                        # Blank line
        "## Method",                               # Section heading
        "",                                        # Blank line
    ]                                              # End of the list
    lines += [f"- {note}" for note in website.method_notes()]  # One bullet per step, the same as the website
    lines += ["", "## Data challenges", ""]        # Next section heading
    lines += [f"- {note}" for note in website.data_challenges(scored)]  # One bullet per challenge, as on the website
    lines += ["", "## My read" if my_read else "## My read: coming soon", ""]  # Heading (says "coming soon" if empty)
    for paragraph in my_read:                      # Each paragraph of my_read.md...
        lines += [paragraph, ""]                   # ...followed by a blank line

    lines += [                                     # How to run it yourself
        "## Setup",                                # Section heading
        "",                                        # Blank line
        "Runs on your own computer: the DMO's website blocks automated downloads, so a cloud job can't fetch the data.",  # Why local
        "",                                        # Blank line
        "1. Install Python 3.12 or later, then in this folder run `python -m venv .venv`, activate it, and run "  # Step 1:
        "`pip install -r requirements.txt`.",      # Python and the libraries
        "2. Install [Claude Code](https://claude.com/claude-code) and log in with a Claude subscription "  # Step 2:
        "(`claude --version` should work in a new terminal). No API key is used.",  # Claude
        "3. Download from the DMO website into `data/`: the outright gilt auction results "  # Step 3: the data
        "([D2.1A](https://www.dmo.gov.uk/data/ExportReport?reportCode=D2.1A)), and into `data/maturities/` the "  # (link
                                                   # to the auction results report)
        "'Gilts in issue' and 'Redemption details' reports "  # (the maturity files)
        "([gilts in issue](https://www.dmo.gov.uk/data/gilt-market/gilts-in-issue/)).",  # link to that page
        "4. Optionally, add amounts bid from DMO result notices to `data/bids_check.csv` to recheck cover.",  # Step 4
        "5. Run `python main.py`. It scores the auctions, asks Claude for a draft, checks it, draws the charts and "  # Step 5:
        "writes `docs/index.html`, `output/summary.md` and this README. `publish.bat` does the same, then pushes "  # run it
        "the results to GitHub.",                  # (and publish)
        "",                                        # Blank line
        "---",                                     # A dividing line
        "",                                        # Blank line
        f"{chart_list[0]['source']} For learning purposes; not investment advice.",  # Source line and disclaimer
    ]                                              # End of the list
    README_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")  # Save it (UTF-8, so "£" and "≥" are kept)
    return README_FILE                             # Tell the caller where it went
