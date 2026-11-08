"""
main.py - runs the whole Gilt Auction Monitor in one go.

  1. Download: get the DMO's auction results (or, if its bot protection blocks us, use the newest copy in data/).
  2. Scoring: bucket and score every conventional auction (scoring.py), and recheck cover where we have the bids.
  3. Review: ask Claude to draft a short review of the latest auction (review.py).
  4. Verification: check the auction facts and scores quoted in the draft against the facts Claude was given.
  5. Charts: draw the three dashboard charts into docs/charts/ (charts.py).
  6. Longer-run view: compare 2015-21 with 2023-25 (analysis.py).
  7. Summary: write output/summary.md, a one-page record of this run.
  8. Website: write docs/index.html, the page GitHub Pages publishes (website.py).
  9. README: write README.md, the project's front page on GitHub (readme.py).

Run it with:  python main.py
"""

from pathlib import Path                           # Handles folder and file paths the same way on Windows and Mac

import analysis                                    # Our own analysis.py: the longer-run comparison of two periods
import charts                                      # Our own charts.py: the three dashboard charts
import dmo                                         # Our own dmo.py: downloads / finds the DMO auction file
import readme                                      # Our own readme.py: writes README.md (and formats Markdown tables)
import review                                      # Our own review.py: the Claude-drafted review and its fact check
import scoring                                     # Our own scoring.py: buckets, percentiles and labels
import website                                     # Our own website.py: writes docs/index.html

PROJECT_DIR = Path(__file__).parent                # The folder this script is in
SUMMARY_FILE = PROJECT_DIR / "output" / "summary.md"  # Where the run summary is written


def step(number, text):
    """Print a clear heading for each stage, so it's obvious how far the run has got.

    number -- the stage number, e.g. 1
    text   -- what the stage does, e.g. "Download"
    Returns nothing.
    """
    print(f"\n=== Step {number}: {text} ===")      # e.g. "=== Step 1: Download ==="


def write_summary(data_date, facts, result, cover_check, chart_list, comparison):
    """Write output/summary.md: the latest auction, its scores, the draft review, its fact check, the charts and
    the longer-run view.

    data_date   -- the date the DMO produced the data (a pandas Timestamp)
    facts       -- the facts given to Claude, from review.latest_auction_facts()
    result      -- the review step's results, from review.draft_review()
    cover_check -- the cover recalculation table, from scoring.check_cover()
    chart_list  -- the charts' titles and paths, from charts.make_charts()
    comparison  -- the longer-run comparison, from analysis.compare_periods()
    Returns the path of the summary file.
    """
    markdown_table = readme.markdown_table         # Short name for the table formatter in readme.py
    passed, verdict = review.verification_text(result["checks"])  # e.g. (True, "Numbers verified ...: 8 of 8 facts matched")
    verdict = f"{verdict}." if passed else f"**{verdict}.**"  # A warning is shown in bold

    lines = [                                      # The summary, one line of Markdown per item
        "# Gilt Auction Monitor: run summary",     # Title
        "",                                        # Blank line (Markdown needs these between blocks)
        f"Data as of {data_date:%d %b %Y}.",       # How up to date the data is
        "",                                        # Blank line
        "## Latest auction",                       # Section heading
        "",                                        # Blank line
        "| Fact | Value |",                        # The facts table's headings...
        "|---|---|",                               # ...and its divider line
    ]                                              # End of the list
    lines += [f"| {name} | {value} |" for name, value in facts.items()]  # One row per fact
    lines += [                                     # Next sections
        "",                                        # Blank line
        "## Claude-drafted review (to be checked and rewritten)",  # Section heading
        "",                                        # Blank line
        "> " + result["draft"],                    # The draft, shown as a quote
        "",                                        # Blank line
        verdict,                                   # The fact check result
        "",                                        # Blank line
        markdown_table(result["checks"]),          # Every fact-like number in the draft, which fact it matched, its verdict
        "",                                        # Blank line
        "## Cover check (amount bid / amount sold, against the DMO's stated cover)",  # Section heading
        "",                                        # Blank line
        markdown_table(cover_check) if not cover_check.empty else "No auctions in data/bids_check.csv yet.",  # Results
        "",                                        # Blank line
        "## Charts",                               # Section heading
    ]                                              # End of the list
    for chart in chart_list:                       # Each chart...
        relative = Path("..") / chart["path"].relative_to(PROJECT_DIR)  # ...its path as seen from output/,
                                                   # e.g. ../docs/charts/cover_history.svg
        lines += ["", f"**{chart['title']}**", "",  # Its numbered title in bold
                  f"![{chart['title']}]({relative.as_posix()})", "",  # The image (as_posix: forward slashes for the web)
                  f"{chart['subtitle']} {chart['source']}"]  # Its subtitle and source line underneath
    lines += ["", "## Longer-run view", "", analysis.headline(comparison), "",  # The
              markdown_table(analysis.formatted(comparison))]  # (table with its decimals lined up)
                                                   # two-period comparison: its headline sentence, then the table

    SUMMARY_FILE.parent.mkdir(exist_ok=True)       # Create output/ if it doesn't exist yet
    SUMMARY_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")  # Save it (UTF-8, so "£" is kept)
    return SUMMARY_FILE                            # Tell the caller where it went


def main():
    """Run every stage in order and print where the results are.

    Takes no inputs. Returns nothing; prints to the screen and writes files.
    """
    step(1, "Download")                            # Stage 1
    path = dmo.get_auction_file()                  # Downloaded, or the newest saved copy
    data_date = dmo.data_date(path)                # The date the DMO produced it
    print(f"Using {path.name} (data as of {data_date:%d %b %Y})")  # Say which file is being used

    step(2, "Scoring")                             # Stage 2
    scored = scoring.load_scored()                 # Every conventional auction, bucketed and scored
    cover_check = scoring.check_cover(scored)      # Recalculated cover for the auctions in bids_check.csv
    print(f"{len(scored)} conventional auctions scored.")  # How many
    if not cover_check.empty:                      # If any auctions were checked...
        print(cover_check.to_string(index=False))  # ...show the results

    step(3, "Claude-drafted review")               # Stage 3
    result = review.draft_review(scored)           # Prompt, Claude, save the draft, check its numbers
    print(f"\n{result['draft']}\n\nSaved to {result['path']}")  # The draft and where it was saved

    step(4, "Verification")                        # Stage 4
    print(result["checks"].to_string(index=False))  # Each fact-like number in the draft and its verdict
    print(review.verification_text(result["checks"])[1])  # e.g. "Numbers verified ...: 8 of 8 facts matched"
    missing = review.unmentioned_facts(result["checks"])  # Facts the draft didn't quote
    if missing:                                    # Any...
        print(f"Not mentioned (not an error): {', '.join(missing)}")  # ...listed for information

    step(5, "Charts")                              # Stage 5
    chart_list = charts.make_charts(scored)        # Draw all three; get their titles and paths
    for chart in chart_list:                       # Each chart...
        print(f"{chart['title']}\n   -> {chart['path']}")  # ...its title and where it was saved

    step(6, "Longer-run view")                     # Stage 6
    comparison = analysis.compare_periods(scored)  # 2015-21 against 2023-25, overall and by bucket
    print(analysis.formatted(comparison).to_string(index=False))  # The table, decimals lined up
    print(analysis.headline(comparison))           # Its one-sentence summary

    step(7, "Summary")                             # Stage 7
    summary = write_summary(data_date, result["facts"], result, cover_check, chart_list, comparison)  # output/summary.md
    print(f"Written to {summary}")                 # Where it is

    step(8, "Website")                             # Stage 8
    page = website.write_site(scored, result, chart_list, data_date, comparison)  # Write docs/index.html
    print(f"Written to {page}")                    # Where it is (open it in a browser to check it)

    step(9, "README")                              # Stage 9
    front_page = readme.write_readme(scored, result, chart_list, data_date, comparison)  # Write README.md
    print(f"Written to {front_page}")              # Where it is
    print("\nDone.")                               # Finished


if __name__ == "__main__":                         # Only runs when you type "python main.py" (not when imported)
    main()                                         # Do everything above
