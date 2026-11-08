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
    result     -- the review step's results, from review.draft_review(), or None if no review was run (the review
                  section is then left out)
    chart_list -- the charts' titles, subtitles, sources and paths, from charts.make_charts()
    data_date  -- the date the DMO produced the data (a pandas Timestamp)
    comparison -- the longer-run comparison, from analysis.compare_periods()
    Returns the path of README.md.
    """
    latest = charts.latest_scored(scored)          # The auction the README is about
    my_read = website.read_my_read()               # Toby's own view, as paragraphs (empty if not written yet)

    lines = [                                      # The README, one line of Markdown per item
        "# Gilt Auction Monitor",                  # Title
        "",                                        # Blank line (Markdown needs these between blocks)
        f"Scores every UK government bond (gilt) auction held by the Debt Management Office (DMO) for demand and, "  # What
        f"optionally, drafts a short review of the latest one with Claude. By {website.AUTHOR}.",  # it does; who made it
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

    if result is not None:                         # Only if this run drafted a review (python main.py --review)...
        passed, verdict = review.verification_text(result["checks"])  # e.g. (True, "Numbers verified ...: 8 of 8 ...")
        lines += [                                 # ...the Claude-drafted review section
            "",                                    # Blank line
            "## Claude-drafted review",            # Section heading
            "",                                    # Blank line
            "Drafted by Claude from the latest auction's facts and scores only, with no other data or tools; I check "  # What
            "and rewrite it.",                     # it is
            "",                                    # Blank line
            f"> {result['draft']}",                # The draft, shown as a quote
            "",                                    # Blank line
            f"**{verdict}.**" if passed else f"**⚠ {verdict}.**",  # The fact check: a plain result, or a marked warning
        ]                                          # End of the review section (with no review, it's simply left out)

    lines += [                                     # The longer-run view and the method
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
    lines += [f"- {note}" for note in website.method_notes(with_review=result is not None)]  # One bullet per step, as
                                                   # on the website (the Claude bullet only when there's a review)
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
        "1. Install Python 3.12 or later and, in this folder, create a virtual environment and install the "  # Step 1:
        "libraries (on a Mac or Linux, type `python3` where it says `python`):",  # Python and the libraries
        "   - `python -m venv .venv`",             # Create the environment (same on every system)
        "   - Activate it: Windows `.venv\\Scripts\\activate`; Mac or Linux `source .venv/bin/activate`",  # The one step
                                                   # that differs between systems ("\\" writes a single backslash)
        "   - `pip install -r requirements.txt` (exact versions, so you get the libraries it was tested with)",  # Install
        "2. **Try it straight away** with the sample data in `sample_data/` (the three DMO reports as of "  # Step 2: the
        "03 Nov 2026): `python main.py --sample`. Nothing is downloaded.",  # sample data, so it works after cloning
        "3. **For current data**, run `python main.py`. It tries to download the three DMO reports it needs. If the "  # Step 3:
        "DMO's bot protection blocks a download, it lists exactly which files to download by hand, with a link "  # live data
        "and the folder for each, and meanwhile uses the newest copies already saved:",  # and what happens if blocked
        "   - Outright Gilt Auctions ([D2.1A](https://www.dmo.gov.uk/data/ExportReport?reportCode=D2.1A)) "  # Report 1
        "→ save in `data/`",                       # and its folder
        "   - Gilts in Issue ([D1A](https://www.dmo.gov.uk/data/ExportReport?reportCode=D1A)) "  # Report 2
        "→ save in `data/maturities/`",            # and its folder
        "   - Redemption Details of Redeemed Gilts ([D1C](https://www.dmo.gov.uk/data/ExportReport?reportCode=D1C)) "  # Report 3
        "→ save in `data/maturities/`",            # and its folder
        "4. Once the files are saved, `python main.py --offline` skips the download attempt and uses them.",  # Step 4
        "   - Compare any two periods, for all auctions or one bucket: "  # The comparison options...
        "`python main.py --compare 2010-2014 2023-2025 --bucket long`. The table is printed and saved to "  # ...with an
        "`output/comparison.md` (each period needs at least 10 auctions; the site keeps the standard view).",  # example
        "5. Optionally, add amounts bid from DMO result notices to `data/bids_check.csv` to recheck cover.",  # Step 5
        "",                                        # Blank line
        "Each run scores the auctions, runs the longer-run view, draws the charts and writes `docs/index.html`, "  # What a
        "`output/summary.md` and this README. No Claude Code or API key is needed.",  # run produces
        "",                                        # Blank line
        "**Optional: the Claude-drafted review.** Install [Claude Code](https://claude.com/claude-code), log in with "  # The
        "a Claude subscription (`claude --version` should work in a new terminal), then run "  # optional review, and
        "`python main.py --review`. It also drafts a review of the latest auction and checks every auction fact it "  # what
        "quotes. If Claude Code isn't found, the run carries on without the review.",  # it needs
        "",                                        # Blank line
        "**Publishing (for the repo owner).** `python publish.py` runs `main.py --review`, then commits only `docs/` "  # How
        "and `output/` as \"Update: auction of <date>\" and pushes them to GitHub, which republishes the site. Add "  # the
        "`--offline` to skip downloading. It works on Windows, Mac and Linux.",  # site is published
        "",                                        # Blank line
        "---",                                     # A dividing line
        "",                                        # Blank line
        f"{chart_list[0]['source']} For learning purposes; not investment advice.",  # Source line and disclaimer
    ]                                              # End of the list
    README_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")  # Save it (UTF-8, so "£" and "≥" are kept)
    return README_FILE                             # Tell the caller where it went
