"""
website.py - writes docs/index.html, the one-page website that GitHub Pages publishes.

It deliberately matches the Oil Curve Tracker's page (same layout, fonts, colours and structure), so the two
projects look like a matching pair:
  - a navy masthead with a gold rule: title, author and "Data as of" date,
  - a headline box for the latest auction: six tiles (label, cover, tail, yield, amount sold, bucket),
  - the three charts as cards (FIGURE 1-3, each with its takeaway title, subtitle and source line),
  - a sidebar: the Claude-drafted review with its fact-check badge (only after python main.py --review),
    "My read" (from my_read.md), Method, Data challenges,
  - a sortable table of the last 20 conventional auctions,
  - a footer with the DMO source line and a link to the code on GitHub.

It's one self-contained HTML file. Its only JavaScript is the few lines that sort the table, written out below:
no libraries are loaded.

(It's called website.py, not site.py, because Python already has a built-in module named "site" that it loads on
start-up, so "import site" would never find this file.)
"""

import datetime as dt                              # The time of this run, used to make browsers fetch the new charts
import html                                        # html.escape makes text safe to place inside a web page
from pathlib import Path                           # Handles folder and file paths the same way on Windows and Mac

import pandas as pd                                # Tables of data; here only pd.isna, to spot blank values

import analysis                                    # Our own analysis.py: the longer-run comparison's headline sentence
import chart_style as style                        # The house palette, so the page matches the charts
import config                                      # Our own config.py: the author's name and the GitHub links
import charts                                    # Our own charts.py: finds the latest auction and the stale-bucket note
import review                                      # Our own review.py: counts how many of the draft's numbers matched
import scoring                                     # Our own scoring.py: column names, cut-offs and the cover check

PROJECT_DIR = Path(__file__).parent                # The folder this script is in
SITE_FILE = PROJECT_DIR / "docs" / "index.html"    # The web page; "index.html" is the file a website shows by default
MY_READ_FILE = PROJECT_DIR / "my_read.md"          # Toby's own view of the latest auction, written by hand
AUTHOR = config.AUTHOR                             # Shown in the masthead (set in config.py)
REPO_URL = config.REPO_URL                         # The code on GitHub, linked from the footer (set in config.py)
TABLE_ROWS = 20                                    # How many recent auctions the table shows

# The page's styling (CSS), copied from the Oil Curve Tracker's report.py so the two sites match.
# PALETTE turns chart_style's colours into CSS "variables" (e.g. --navy), so the page and the charts share
# one palette: change a colour in chart_style.py and both follow. {{ and }} are how an f-string writes { and }.
PALETTE = (f":root {{ --navy: {style.NAVY}; --mid-blue: {style.MID_BLUE}; --gold: {style.GOLD}; "  # The five house colours...
           f"--dark-grey: {style.DARK_GREY}; --light-grey: {style.LIGHT_GREY}; --white: {style.WHITE}; }}")  # ...plus white

# Each line below sets how one kind of element looks; var(--navy) means "the navy from the palette above".
# Lines marked "(new)" aren't on the oil page; everything else is identical to it.
STYLE = PALETTE + """
* { box-sizing: border-box; }                                          /* Widths include padding, which keeps the grid maths simple */
body { margin: 0; font-family: Arial, Helvetica, "Liberation Sans", sans-serif; color: var(--dark-grey); background: var(--white); line-height: 1.45; font-size: 14px; } /* Same font and text colour as the charts */
.wrap { max-width: 1280px; margin: 0 auto; padding: 0 24px; }          /* One centred page width, used by every band */
.masthead { background: var(--navy); border-bottom: 3px solid var(--gold); }  /* Navy band across the top, with a gold rule under it */
.masthead .wrap { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; padding-top: 18px; padding-bottom: 16px; }  /* Title on the left, data date on the right */
.label { margin: 0; color: var(--gold); font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }  /* Small gold label above the title */
h1 { margin: 2px 0; font-size: 26px; color: var(--white); }            /* Page title, white on navy */
.masthead .subtitle { margin: 0; color: var(--light-grey); font-size: 13px; }  /* Subtitle, light grey on navy */
.stamp { color: var(--light-grey); font-size: 12px; text-align: right; white-space: nowrap; }  /* "Data as of ..." on the right of the band */
.stamp strong { display: block; color: var(--white); font-size: 15px; }  /* The date itself, larger and white */
.headline { margin: 20px 0; }                                          /* (new) Space around the latest-auction box */
.headline h2 { margin: 0 0 4px; font-size: 18px; color: var(--navy); } /* (new) "Latest auction: ..." heading */
.headline .sub { margin: 0 0 12px; }                                   /* (new) The peer-group line under it */
.tiles { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin: 0; }  /* Six headline tiles in a row */
.tile { border: 1px solid var(--light-grey); border-top: 3px solid var(--navy); padding: 10px 12px; }  /* Each tile: hairline frame, navy top edge */
.tile.gold { border-top-color: var(--gold); }                          /* (new) The label tile gets a gold top edge: it's the verdict */
.tile-label { margin: 0; font-size: 11px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; }  /* What the tile shows */
.tile-value { margin: 4px 0 0; font-size: 26px; font-weight: 700; color: var(--navy); font-variant-numeric: tabular-nums; }  /* The headline number */
.tile-unit { font-size: 12px; font-weight: 400; color: var(--dark-grey); margin-left: 3px; }  /* The unit after the number, small */
.tile-detail { margin: 2px 0 0; font-size: 12px; font-weight: 700; }   /* The reading, e.g. "higher than 73% of peers" */
.tile-date { margin: 2px 0 0; font-size: 11px; }                       /* The auction date, smallest */
.tile-info { margin: 8px 0 0; padding-top: 7px; border-top: 1px solid var(--light-grey); font-size: 11.5px; line-height: 1.4; }  /* The plain-English explanation, under a hairline */
.asof-note { margin: 0 0 10px; font-size: 12px; font-style: italic; } /* Small italic note at the top of a sidebar card */
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 20px; align-items: start; }  /* Charts on the left, sidebar on the right */
.charts { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }  /* Charts in two columns */
.card { border: 1px solid var(--light-grey); padding: 14px 16px 12px; background: var(--white); }  /* Every chart and panel sits in a card */
.card.wide { grid-column: 1 / -1; }                                    /* A wide chart spans both columns */
.fig { margin: 0; font-size: 11px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--mid-blue); }  /* "FIGURE 1" */
.card h3 { margin: 3px 0 2px; font-size: 15px; line-height: 1.3; color: var(--navy); }  /* The takeaway title */
.sub { margin: 0 0 8px; font-size: 12px; }                             /* What's plotted and the units */
.card img { display: block; width: 100%; height: auto; }               /* The chart fills its card */
.card > a { display: block; cursor: zoom-in; }                         /* A static chart is clickable, with a magnifier cursor */
.foot { margin: 6px 0 0; font-size: 11px; }                            /* Note and source lines under the chart */
.side h2, .numbers h2 { margin: 0 0 8px; font-size: 15px; color: var(--navy); padding-bottom: 6px; border-bottom: 2px solid var(--navy); }  /* Panel headings */
.side .card + .card { margin-top: 20px; }                              /* Space between the sidebar's cards */
.side p { margin: 0 0 10px; }                                          /* Space between paragraphs */
.side ul { margin: 0; padding-left: 18px; font-size: 12px; }           /* The method and data-challenge lists */
.side li { margin-bottom: 6px; }                                       /* Space between list items */
.badge { display: inline-block; margin: 0 0 10px; padding: 3px 8px; background: var(--navy); color: var(--white); font-size: 12px; font-weight: 700; }  /* (new) "Numbers verified: X of X matched" */
.warn { margin: 0 0 10px; padding: 8px 10px; border: 2px solid var(--gold); color: var(--navy); font-size: 12px; font-weight: 700; }  /* (new) The warning shown instead if any number failed */
.numbers { margin-top: 20px; }                                         /* Space above the auctions table */
.table-wrap { overflow-x: auto; }                                      /* On a phone the table scrolls sideways instead of squashing */
table { width: 100%; border-collapse: collapse; font-size: 13px; }     /* Full-width table with single-line borders */
th, td { padding: 6px 10px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--light-grey); }  /* Cell spacing and light grey row lines */
th { background: var(--navy); color: var(--white); font-weight: 700; } /* Navy header row with white text */
th[data-type] { cursor: pointer; white-space: nowrap; }                /* (new) Headings you can click to sort show a pointer */
th[aria-sort="ascending"]::after { content: " \\25B2"; }               /* (new) An up arrow on the column sorted low-to-high */
th[aria-sort="descending"]::after { content: " \\25BC"; }              /* (new) A down arrow on the column sorted high-to-low */
.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }  /* Numbers right-aligned so the decimals line up */
footer { margin: 28px auto 40px; font-size: 12px; }                    /* Small footer */
a { color: var(--mid-blue); }                                          /* Links in the mid blue */
@media (max-width: 1100px) { .tiles { grid-template-columns: repeat(3, 1fr); } .layout { grid-template-columns: 1fr; } }  /* Tablet: 3 tiles a row, sidebar moves below */
@media (max-width: 700px) { .tiles { grid-template-columns: repeat(2, 1fr); } .charts { grid-template-columns: 1fr; } .masthead .wrap { display: block; } .stamp { text-align: left; margin-top: 8px; } }  /* Phone: one column */
"""                                                # End of the styling

# The JavaScript that sorts the table when a heading is clicked. It runs in the reader's browser, not in Python.
# Each cell carries a data-value (e.g. 20261103 for a date), so dates and numbers sort as numbers, not as text.
SORT_SCRIPT = """<script>
document.querySelectorAll("th[data-type]").forEach(function (th) {        // Every heading that can be sorted...
  th.addEventListener("click", function () {                             // ...waits for a click
    var table = th.closest("table");                                     // The table this heading belongs to
    var body = table.tBodies[0];                                         // Its rows live in the table body
    var col = th.cellIndex;                                              // Which column was clicked (0 = first)
    var up = th.getAttribute("aria-sort") !== "ascending";               // Sort low-to-high, unless it already is
    table.querySelectorAll("th").forEach(function (h) { h.removeAttribute("aria-sort"); });  // Clear the old arrows
    th.setAttribute("aria-sort", up ? "ascending" : "descending");       // Mark the new direction (CSS draws the arrow)
    var rows = Array.from(body.rows);                                    // The rows as a list that can be sorted
    rows.sort(function (a, b) {                                          // Compare two rows at a time
      var x = a.cells[col].dataset.value, y = b.cells[col].dataset.value;  // Their sort values in this column
      var diff = th.dataset.type === "num" ? parseFloat(x) - parseFloat(y) : x.localeCompare(y);  // Numbers by size, text A-Z
      return up ? diff : -diff;                                          // Reverse it for high-to-low
    });                                                                  // End of the comparison
    rows.forEach(function (row) { body.appendChild(row); });             // Put the rows back in the new order
  });                                                                    // End of what a click does
});                                                                      // End of the loop over headings
</script>"""                                                             # End of the JavaScript


def read_my_read():
    """Read Toby's own view from my_read.md, as a list of paragraphs.

    Takes no inputs. Returns a list of paragraphs (blank lines separate them), or an empty list if there's no file yet.
    Exists so the "My read" section is always written by hand, never by code or by Claude.
    """
    if not MY_READ_FILE.exists():                  # Not written yet...
        return []                                  # ...so nothing to show
    text = MY_READ_FILE.read_text(encoding="utf-8")  # The whole file
    paragraphs = [" ".join(block.split()) for block in text.split("\n\n")]  # Split at blank lines; tidy the spaces
    return [p for p in paragraphs if p and not p.startswith("#")]  # Drop empty blocks and Markdown headings ("# ...")


def tiles(latest):
    """The six headline tiles for the latest auction.

    latest -- the latest scored auction's row (from charts.latest_scored())
    Returns a list of dictionaries, one per tile: label, value, unit, detail, info, and whether it's the gold tile.
    """
    years = latest["Years to Maturity"]            # e.g. 10.34
    low, high = scoring.SHORT_LIMIT, scoring.LONG_LIMIT  # The bucket limits, 7 and 15 years
    ranges = {"short": f"under {low} years", "medium": f"{low} to {high} years", "long": f"over {high} years"}  # In words
    paof = latest["Nominal Amount Issued via PAOF (£ million)"]  # The post-auction top-up (blank if none)
    return [                                       # One dictionary per tile, left to right
        {"label": "Verdict", "value": latest["Label"], "unit": "",  # The strong / normal / weak label
         "detail": f"cover pct {latest['Cover Pct']:.0f} · tail pct {latest['Tail Pct']:.0f}",  # Its two percentiles
         "info": (f"Strong if both percentiles are at least {scoring.STRONG_CUTOFF}; weak if either is "  # The rule in
                  f"{scoring.WEAK_CUTOFF} or lower; otherwise normal."),  # one sentence
         "gold": True},                            # The verdict tile gets the gold top edge
        {"label": "Cover", "value": f"{latest[scoring.COVER]:.2f}", "unit": "x",  # e.g. "3.38 x"
         "detail": f"higher than {latest['Cover Pct']:.0f}% of peers",  # Its percentile, in words
         "info": "Amount bid divided by amount sold. Higher means more demand for the gilts on offer.",  # What it means
         "gold": False},                           # Normal navy top edge
        {"label": "Tail", "value": f"{latest[scoring.TAIL]:.1f}", "unit": "bp",  # e.g. "0.3 bp"
         "detail": f"narrower than {latest['Tail Pct']:.0f}% of peers",  # Its percentile, in words
         "info": ("Yield at the lowest accepted price minus yield at the average price. Narrower means bids "  # What it
                  "were bunched together: steadier demand."),  # means (1bp = 0.01%)
         "gold": False},                           # Normal navy top edge
        {"label": "Yield", "value": f"{latest['Yield at AAP (%)']:.3f}", "unit": "%",  # e.g. "5.268 %"
         "detail": f"price £{latest['Average Accepted Price (AAP) (£)']:.3f}",  # The average accepted price
         "info": "Yield at the average accepted price: the return a buyer locks in by holding the gilt to maturity.",  # Meaning
         "gold": False},                           # Normal navy top edge
        {"label": "Amount sold", "value": f"{latest[scoring.SOLD]:,.0f}", "unit": "£m",  # e.g. "3,250 £m"
         "detail": "PAOF: none" if pd.isna(paof) else f"PAOF: £{paof:,.0f}m",  # Post-auction top-up, if any
         "info": "Nominal (face value) sold at the auction, before any post-auction option facility (PAOF) top-up.",  # Meaning
         "gold": False},                           # Normal navy top edge
        {"label": "Bucket", "value": latest["Bucket"], "unit": f"{years:.1f} yrs",  # e.g. "medium 10.3 yrs"
         "detail": ranges[latest["Bucket"]],       # e.g. "7 to 15 years"
         "info": "The DMO's maturity bucket on the auction day. Each auction is compared only with its own bucket.",  # Meaning
         "gold": False},                           # Normal navy top edge
    ]                                              # End of the tiles


def verification_lines(result):
    """The badge (or warning) shown above the Claude-drafted review.

    result -- the review step's results, from review.draft_review()
    Returns one line of HTML: a navy badge ("X of X facts matched") if every auction fact quoted in the draft was
    correct, otherwise a gold-bordered warning listing the numbers that failed. A failure is never hidden.
    """
    passed, text = review.verification_text(result["checks"])  # e.g. (True, "Numbers verified ...: 8 of 8 facts matched")
    if passed:                                     # Every auction fact quoted in the draft is correct
        return f'<p class="badge">{html.escape(text)}</p>'  # The navy badge
    return f'<p class="warn">{html.escape(text)}.</p>'  # The gold-bordered warning: shown, never hidden


def method_notes(with_review=True):
    """The "Method" section: the scoring rule in plain English, one bullet per step.

    with_review -- True if this run includes a Claude-drafted review, so the method also explains how it's made
    Returns a list of sentences.
    """
    low, high = scoring.SHORT_LIMIT, scoring.LONG_LIMIT  # The bucket limits, 7 and 15 years
    notes = [                                      # One sentence per step
        f"Only conventional gilts are scored. Each auction goes in the DMO's maturity bucket for its years left to "  # Step 1:
        f"maturity on the day: short (under {low}), medium ({low} to {high}) or long (over {high}).",  # buckets
        f"Its peers are the auctions in the same bucket over the previous {scoring.WINDOW_YEARS} years. With fewer "  # Step 2:
        f"than {scoring.MIN_PEERS} peers it isn't scored.",  # peers
        "Cover percentile: the share of peers with a lower cover. Tail percentile: the share of peers with a wider "  # Step 3:
        "tail. Ties count as half. For both, higher is better.",  # percentiles
        f"Strong: both percentiles at least {scoring.STRONG_CUTOFF}. Weak: either {scoring.WEAK_CUTOFF} or lower. "  # Step 4:
        "Otherwise normal. So one bad measure is enough to call an auction weak.",  # the label
    ]                                              # End of the scoring steps
    if with_review:                                # Only when there's a review on the page...
        notes.append("Claude drafts the review from the facts in the headline box only, with no other data or tools. "  # ...Step 5:
                     "Each auction fact it quotes is then checked against those facts automatically, and I check the "  # how the
                     "draft myself.")              # review is made and checked
    return notes                                   # The method, one sentence per step


def data_challenges(scored):
    """The "Data challenges" section: what made the data hard to use, and how each problem is handled.

    scored -- the scored table from scoring.load_scored()
    Returns a list of sentences; the cover check, data errors and stale buckets are worked out from the data.
    """
    notes = [                                      # The challenges that are always true
        "The DMO's website blocks automated downloads with a captcha, so the auction file is downloaded by hand and "  # Bot
        "the site is rebuilt on my own computer. A scheduled cloud job (e.g. GitHub Actions) isn't used, because "  # protection,
        "the captcha would block it too.",         # and why there's no automatic update
        "Index-linked gilt auctions are sold at a single price that every successful bidder pays, so they have no "  # No tail
        f"tail and are left out. {len(scored):,} conventional auctions since 1998 are scored.",  # for index-linked gilts
        "The auction file gives only each gilt's maturity year. Exact redemption dates come from two more DMO "  # Maturity
        "reports (gilts in issue, and redeemed gilts); the year alone would put some gilts in the wrong bucket.",  # dates
        "The DMO file has no 'amount bid' column, so cover can't be recalculated from it. Instead, the amount bid "  # Amount
        "is copied from the DMO's result notice for spot checks.",  # bid missing
    ]                                              # End of the fixed notes
    for _, row in scoring.check_cover(scored).iterrows():  # Each spot check of cover...
        if "Recalculated Cover" in row and not pd.isna(row["Recalculated Cover"]):  # ...that could actually be run
            notes.append(f"Cover check, {row['Auction Date']:%d %b %Y}: £{row['Amount Bid (£m)']:,.1f}m bid / "  # The sum...
                         f"£{row['Amount Sold (£m)']:,.0f}m sold = {row['Recalculated Cover']:.4f}, against the DMO's "  # ...its
                         f"{row['DMO Cover']:.2f}: {row['Result']}.")  # ...result, and whether it matched
    for _, row in scored[scored["Data Check"]].iterrows():  # Each auction with impossible figures
        notes.append(f"Data error: the {row['Gilt Name']} auction on {row['Auction Date']:%d %b %Y} shows a tail of "  # Which
                     f"{row[scoring.TAIL]:.1f}bp. A tail can't be negative, so it is left out of all scoring.")  # Say so
    stale = charts.stale_note(scored).strip()      # e.g. "No long-bucket auctions since 21 Oct 2025."
    if stale:                                      # A bucket has gone quiet...
        notes.append(f"{stale} Its latest values on the charts are therefore not recent.")  # ...so warn the reader
    return notes                                   # All the challenges


def auction_table(scored):
    """The sortable table of the last 20 scored conventional auctions, newest first.

    scored -- the scored table from scoring.load_scored()
    Returns the table as a list of HTML lines.
    Each cell has a data-value to sort by, so e.g. "03 Nov 2026" sorts as the number 20261103.
    """
    esc = html.escape                              # Short name for the escaping function
    usable = scored[scored["Label"].isin(["strong", "normal", "weak"])]  # Only auctions with a real label
    rows = usable.tail(TABLE_ROWS).iloc[::-1]      # The last 20, newest first
    bucket_order = {"short": 1, "medium": 2, "long": 3}  # Sort buckets by maturity, not alphabetically
    label_order = {"weak": 1, "normal": 2, "strong": 3}  # Sort labels from weakest to strongest
    headings = [("Date", "num", ""), ("Gilt", "text", ""), ("Bucket", "num", ""),  # (heading, sort type, CSS class)
                ("Years to maturity", "num", "num"), ("Sold (£m)", "num", "num"), ("Cover (x)", "num", "num"),  # "num"
                ("Cover pct", "num", "num"), ("Tail (bp)", "num", "num"), ("Tail pct", "num", "num"),  # = right-aligned
                ("Label", "num", "")]              # Every column can be sorted
    lines = ['<div class="table-wrap"><table>',    # Wrapper that lets the table scroll sideways on a phone
             "<thead><tr>" + "".join(f'<th data-type="{kind}" class="{cls}">{esc(name)}</th>'  # One clickable heading
                                     for name, kind, cls in headings) + "</tr></thead>",  # per column
             "<tbody>"]                            # Start of the rows
    for _, r in rows.iterrows():                   # Each auction, newest first
        cells = [                                  # (text shown, value to sort by, CSS class)
            (f"{r['Auction Date']:%d %b %Y}", f"{r['Auction Date']:%Y%m%d}", ""),  # e.g. "03 Nov 2026" / 20261103
            (r["Gilt Name"], r["Gilt Name"], ""),  # Sorted alphabetically
            (r["Bucket"], bucket_order[r["Bucket"]], ""),  # Sorted short, medium, long
            (f"{r['Years to Maturity']:.2f}", r["Years to Maturity"], "num"),  # e.g. 10.34
            (f"{r[scoring.SOLD]:,.0f}", r[scoring.SOLD], "num"),  # e.g. 3,250
            (f"{r[scoring.COVER]:.2f}", r[scoring.COVER], "num"),  # e.g. 3.38
            (f"{r['Cover Pct']:.0f}", r["Cover Pct"], "num"),  # e.g. 73
            (f"{r[scoring.TAIL]:.1f}", r[scoring.TAIL], "num"),  # e.g. 0.3
            (f"{r['Tail Pct']:.0f}", r["Tail Pct"], "num"),  # e.g. 60
            (r["Label"], label_order[r["Label"]], ""),  # Sorted weak, normal, strong
        ]                                          # End of this row's cells
        lines.append("<tr>" + "".join(f'<td class="{cls}" data-value="{esc(str(value))}">{esc(str(text))}</td>'  # One
                                      for text, value, cls in cells) + "</tr>")  # row, every cell escaped
    lines += ["</tbody>", "</table></div>"]        # Close the table
    return lines                                   # The table's HTML


def longer_run_table(comparison):
    """The "Longer-run view" table: two periods compared, overall and by bucket.

    comparison -- the table from analysis.compare_periods()
    Returns the table as a list of HTML lines (numbers right-aligned so the decimals line up).
    """
    esc = html.escape                              # Short name for the escaping function
    numeric = {"Auctions", "Median cover (x)", "Median tail (bp)", "Median yield (%)"}  # Columns to right-align
    lines = ['<div class="table-wrap"><table>',    # Wrapper that lets the table scroll sideways on a phone
             "<thead><tr>" + "".join(f'<th class="{"num" if name in numeric else ""}">{esc(name)}</th>'  # One heading
                                     for name in comparison.columns) + "</tr></thead>",  # per column
             "<tbody>"]                            # Start of the rows
    for row in comparison.itertuples(index=False):  # Each group and period
        cells = [(name, value) for name, value in zip(comparison.columns, row)]  # Pair each value with its column
        lines.append("<tr>" + "".join(f'<td class="{"num" if name in numeric else ""}">{esc(str(value))}</td>'  # One
                                      for name, value in cells) + "</tr>")  # row, every cell escaped
    lines += ["</tbody>", "</table></div>"]        # Close the table
    return lines                                   # The table's HTML


def write_site(scored, result, chart_list, data_date, comparison):
    """Write docs/index.html, the one-page website.

    scored     -- the scored table from scoring.load_scored()
    result     -- the review step's results, from review.draft_review(), or None if no review was run (the review
                  card is then left out and the sidebar starts with "My read")
    chart_list -- the charts' titles, subtitles, sources and paths, from charts.make_charts()
    data_date  -- the date the DMO produced the data (a pandas Timestamp)
    comparison -- the longer-run comparison, from analysis.compare_periods()
    Returns the path of the saved page.
    Every piece of text goes through html.escape, so characters like < or & can't break the page.
    """
    esc = html.escape                              # Short name for the escaping function, used many times below
    version = f"{dt.datetime.now():%Y%m%d%H%M}"    # A stamp added to each chart's address, so browsers fetch the new
                                                   # image rather than an old saved copy
    latest = charts.latest_scored(scored)          # The auction the headline box is about
    source = chart_list[0]["source"]               # "Source: UK Debt Management Office (D2.1A). Data as of ..."

    page = [                                       # The page is built up here, one line at a time
        "<!DOCTYPE html>",                         # Tells the browser this is a modern HTML page
        '<html lang="en-GB">',                     # The page is in British English
        "<head>",                                  # The head holds information about the page, not shown directly
        '<meta charset="utf-8">',                  # The text encoding, so symbols like £ and ▲ display correctly
        '<meta name="viewport" content="width=device-width, initial-scale=1">',  # Fit the page to phone screens
        "<title>Gilt Auction Monitor</title>",     # The text on the browser tab
        '<meta name="description" content="UK gilt auction results scored for demand (cover and tail) against '  # Summary
        'comparable auctions.">',                  # for search engines
        f"<style>{STYLE}</style>",                 # The styling defined at the top of this file
        "</head>",                                 # End of the head
        "<body>",                                  # The visible page starts here
        '<header class="masthead"><div class="wrap">',  # The navy band across the top
        "<div>",                                   # Left side of the band
        '<p class="label">UK gilts | Auction monitor</p>',  # Small gold label above the title
        "<h1>Gilt Auction Monitor</h1>",           # Page title
        f'<p class="subtitle">DMO gilt auctions scored for demand: cover and tail against comparable auctions. '  # What
        f"By {esc(AUTHOR)}.</p>",                  # the page is, and who made it
        "</div>",                                  # End of the left side
        f'<div class="stamp">Data as of<strong>{data_date:%d %b %Y}</strong>UK DMO</div>',  # Right side: data date
        "</div></header>",                         # End of the band
        '<main class="wrap">',                     # The main content
        '<section class="headline">',              # The latest-auction headline box
        f"<h2>Latest auction: {esc(latest['Gilt Name'])}, {latest['Auction Date']:%d %b %Y}</h2>",  # Which auction
        f'<p class="sub">Compared with {latest["Peers"]} {esc(latest["Bucket"])}-bucket auctions over the previous '  # Its
        f"{scoring.WINDOW_YEARS} years.</p>",      # peer group
        '<div class="tiles">',                     # The six tiles
    ]                                              # End of the page's opening
    for tile in tiles(latest):                     # One tile per headline figure
        page += [                                  # Each tile: label, value with unit, reading, date, explanation
            f'<div class="tile{" gold" if tile["gold"] else ""}">',  # Start of the tile (gold edge for the verdict)
            f'<p class="tile-label">{esc(tile["label"])}</p>',  # e.g. "COVER"
            f'<p class="tile-value">{esc(tile["value"])}<span class="tile-unit">{esc(tile["unit"])}</span></p>',  # e.g. "3.38 x"
            f'<p class="tile-detail">{esc(tile["detail"])}</p>',  # e.g. "higher than 73% of peers"
            f'<p class="tile-date">{latest["Auction Date"]:%d %b %Y}</p>',  # e.g. "03 Nov 2026"
            f'<p class="tile-info">{esc(tile["info"])}</p>',  # What it measures
            "</div>",                              # End of the tile
        ]                                          # End of this tile's lines
    page += ["</div>", "</section>", '<div class="layout">', '<div class="charts">']  # End the headline; start the charts

    for chart in chart_list:                       # One card per chart (all three are full width)
        alt = f"Figure {chart['number']}: {chart['title']}. {chart['subtitle']}"  # Description read aloud by screen readers
        static = f"charts/{chart['path'].name}?v={version}"  # The chart's address, with the version stamp
        title = chart["title"].split(". ", 1)[1]   # The title without its "1. " number (the card says "FIGURE 1")
        page += [                                  # The card: label, takeaway title, subtitle, chart, source
            '<article class="card wide">',         # Start of the card
            f'<p class="fig">Figure {chart["number"]}</p>',  # "FIGURE 1"
            f"<h3>{esc(title)}</h3>",              # The takeaway title, generated from the data
            f'<p class="sub">{esc(chart["subtitle"])}</p>',  # What's plotted and the units
            f'<a href="{static}" target="_blank" title="Open full size"><img src="{static}" alt="{esc(alt)}" '  # The
            'loading="lazy"></a>',                 # chart, clickable to open full size in a new tab
            f'<p class="foot">{esc(chart["source"])}</p>',  # The source line
            "</article>",                          # End of the card
        ]                                          # End of this card's lines
    page.append("</div>")                          # End of the charts grid

    page.append('<aside class="side">')            # The sidebar
    if result is not None:                         # Only if this run drafted a review (python main.py --review)...
        page += ['<div class="card">', "<h2>Claude-drafted review</h2>",  # ...the sidebar's first card
                 '<p class="asof-note">Drafted by Claude from the headline figures only; I check and rewrite it.</p>',  # What it is
                 verification_lines(result),       # The "X of X facts matched" badge, or a warning
                 f"<p>{esc(result['draft'])}</p>",  # The draft itself
                 "</div>"]                         # End of the card
                                                   # (With no review, nothing is written here: no empty box, no gap.)

    my_read = read_my_read()                       # Toby's own view, if written (an empty list if not)
    if my_read:                                    # Written...
        page += ['<div class="card">', "<h2>My read</h2>"]  # ...its card, with its heading
        page += [f"<p>{esc(p)}</p>" for p in my_read]  # ...one <p> per paragraph
        page += ['<p class="foot">Written by hand, so it changes only when I update it.</p>', "</div>"]  # Make that clear
    else:                                          # Not written yet...
        page += ['<div class="card">', "<h2>My read: coming soon</h2>", "</div>"]  # ...say so, not a blank box

    page += ['<div class="card">', "<h2>Method</h2>", "<ul>"]  # The method card
    page += [f"<li>{esc(note)}</li>" for note in method_notes(with_review=result is not None)]  # One bullet per step
                                                   # (the bullet about Claude's draft only when there is one)
    page += ["</ul>", "</div>"]                    # End of the card

    page += ['<div class="card">', "<h2>Data challenges</h2>", "<ul>"]  # The fourth card
    page += [f"<li>{esc(note)}</li>" for note in data_challenges(scored)]  # One bullet per challenge
    page += ["</ul>", "</div>", "</aside>", "</div>"]  # End the card, the sidebar and the layout

    page += ['<section class="card numbers">',     # The longer-run view, full width under the charts and sidebar
             "<h2>Longer-run view</h2>",           # Its heading
             f'<p class="sub">{esc(analysis.headline(comparison))}</p>']  # The one-sentence comparison
    page += longer_run_table(analysis.formatted(comparison))  # The table: both periods, overall and by bucket
    page += ['<p class="foot">Conventional auctions only; each period runs from January of its first year to December '  # A
             "of its last. Medians are the middle value, so a single unusual auction can't move them much.</p>",  # How
             "</section>"]                         # to read it; end of the card

    page += ['<section class="card numbers">',     # The auctions table, full width at the bottom
             f"<h2>Last {TABLE_ROWS} conventional auctions</h2>",  # Its heading
             '<p class="sub">Click a column heading to sort.</p>']  # How to use it
    page += auction_table(scored)                  # The table itself
    page += ["</section>", "</main>"]              # Close the table card and the main content

    page += [                                      # The footer at the bottom of the page
        '<footer class="wrap">',                   # Start of the footer
        f'<p>{esc(source)} Code: <a href="{REPO_URL}">GitHub</a>. For learning purposes; not investment advice.</p>',  # Source, code link, disclaimer
        "</footer>",                               # End of the footer
        SORT_SCRIPT,                               # The table-sorting JavaScript (runs once the page has loaded)
        "</body>",                                 # End of the visible page
        "</html>",                                 # End of the document
    ]                                              # End of the page's closing lines
    SITE_FILE.parent.mkdir(exist_ok=True)          # Create docs/ if it doesn't exist yet
    SITE_FILE.write_text("\n".join(page) + "\n", encoding="utf-8")  # Save the page, one element per line
    return SITE_FILE                               # Tell the caller where it went
