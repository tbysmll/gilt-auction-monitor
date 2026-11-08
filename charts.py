"""
charts.py - draws the three dashboard charts, in the house style from chart_style.py.

  1. Cover history: the bid-to-cover ratio at each conventional auction over the past 3 years, one panel per bucket.
  2. Tail history: the tail at each conventional auction over the past 3 years, one panel per bucket.
  3. Scorecard: a table of the last 10 auctions with their percentiles and strong/normal/weak labels.

Each image is just the plot, saved as SVG in docs/charts/. Its numbered takeaway title, subtitle and source line are
returned as text, so main.py can write them around the chart in the README and on the web page (the same "card chart"
approach as chart_style.py describes). The titles are written from the data, so they stay true after every update.

Run it with:  python charts.py
"""

from pathlib import Path                           # Handles folder and file paths the same way on Windows and Mac

import matplotlib                                  # The charting library
matplotlib.use("Agg")                              # Draw straight to files, without opening a window on screen
import matplotlib.dates as mdates                  # Places and formats dates along an axis
import matplotlib.pyplot as plt                    # pyplot creates figures and chart areas
import pandas as pd                                # Tables of data (like Excel in Python)

import chart_style as cs                           # Our house style: colours, sizes, fonts and helper functions
import dmo                                         # Our own dmo.py: finds the saved auction file and its data date
import scoring                                     # Our own scoring.py: the bucketed and scored auctions

CHART_DIR = Path(__file__).parent / "docs" / "charts"  # Where the chart images are saved (docs/ is what GitHub Pages serves)
BUCKETS = ["short", "medium", "long"]              # The three maturity buckets, in the order the panels appear
HISTORY_YEARS = 3                                  # How far back the history charts go (matches the scoring window)
STALE_DAYS = 182                                   # A bucket with no auction for about 6 months gets a note under the
                                                   # chart, so its last value isn't mistaken for a recent one


def source_line():
    """The source line printed under every chart.

    Takes no inputs. Returns text like "Source: UK Debt Management Office (D2.1A). Data as of 03 Nov 2026."
    """
    date = dmo.data_date(dmo.saved_report("auctions"))  # The date the DMO produced the auction file this run uses
    return f"Source: UK Debt Management Office (D2.1A). Data as of {date:%d %b %Y}."  # e.g. "03 Nov 2026"


def latest_scored(scored):
    """Find the most recent auction that got a real label (strong, normal or weak).

    scored -- the scored table from scoring.load_scored()
    Returns that auction's row.
    """
    usable = scored[scored["Label"].isin(["strong", "normal", "weak"])]  # Leave out "data check" / "not enough history"
    return usable.iloc[-1]                         # The last row is the most recent (the table is oldest first)


def recent_auctions(scored):
    """Keep the auctions from the past 3 years, for the history charts.

    scored -- the scored table from scoring.load_scored()
    Returns the auctions held in the 3 years up to and including the latest one, excluding any flagged for a data check.
    """
    end = scored["Auction Date"].max()             # The latest auction day
    start = end - pd.DateOffset(years=HISTORY_YEARS)  # 3 years earlier
    in_window = scored["Auction Date"] > start     # Held after that date
    return scored[in_window & ~scored["Data Check"]]  # ...and with no data problem


def stale_note(scored):
    """Say which buckets, if any, have had no auction for about 6 months.

    scored -- the scored table from scoring.load_scored()
    Returns text like " No long-bucket auctions since 21 Oct 2025." (starting with a space), or "" if none.
    Exists because each panel's value tag shows that bucket's LAST auction, which may be months old.
    """
    latest_day = scored["Auction Date"].max()      # The latest auction day of all
    notes = []                                     # One sentence per stale bucket
    for bucket in BUCKETS:                         # Each bucket in turn
        last_day = scored.loc[scored["Bucket"] == bucket, "Auction Date"].max()  # Its most recent auction
        if (latest_day - last_day).days >= STALE_DAYS:  # Nothing for about 6 months or more
            notes.append(f"No {bucket}-bucket auctions since {last_day:%d %b %Y}.")  # e.g. "...since 21 Oct 2025."
    return "".join(" " + note for note in notes)   # Each note with a space in front, joined together


def history_chart(scored, column, file_name, value_format):
    """Draw one history chart (cover or tail): three side-by-side panels, one per maturity bucket.

    scored       -- the scored table from scoring.load_scored()
    column       -- which figure to plot: scoring.COVER or scoring.TAIL
    file_name    -- what to call the image, without its ending, e.g. "cover_history"
    value_format -- how to write the numbers in the value tags, e.g. "{:.2f}" for cover (3.38)
    Returns the path of the saved image.
    Each panel shows one bucket in navy; only the latest auction overall gets the gold dot, so gold always means
    "the latest auction". The panel title names the bucket, so colour isn't needed to tell them apart.
    """
    recent = recent_auctions(scored)               # The past 3 years of auctions
    latest = latest_scored(scored)                 # The auction to highlight in gold
    with plt.rc_context(cs.rc_params()):           # Apply the house style just while this chart is drawn
        fig, axes = cs.new_figure(1, 3, size=cs.WIDE_SIZE, sharex=True, sharey=True)  # Three panels, same scales
        fig.subplots_adjust(wspace=0.22)           # A little more space between panels, for the value tags
        for ax, bucket in zip(axes, BUCKETS):      # Each panel with its bucket
            data = recent[recent["Bucket"] == bucket]  # That bucket's auctions
            ax.plot(data["Auction Date"], data[column], color=cs.NAVY, linewidth=1.0,  # A thin navy line...
                    marker="o", markersize=2.5)    # ...with a small dot on each auction, since each is a separate event
            ax.set_title(bucket.capitalize(), loc="left", fontsize=9, fontweight="bold", color=cs.DARK_GREY)  # e.g. "Medium"
            last = data.iloc[-1]                   # This bucket's most recent auction
            cs.value_tag(ax, last[column], value_format.format(last[column]), cs.NAVY)  # Its value on the right axis
            if last["Auction Date"] == latest["Auction Date"] and bucket == latest["Bucket"]:  # The latest auction of all
                cs.mark_last(ax, last["Auction Date"], last[column])  # ...gets the gold dot
            ax.xaxis.set_major_locator(mdates.YearLocator())  # One date label per year (panels are narrow)
            cs.format_dates(ax)                    # Dates written like "Jan-25"
        for ax in axes[:-1]:                       # The first two panels...
            ax.tick_params(labelright=False)       # ...don't repeat the axis numbers (the scale is shared)
        last_values = [recent.loc[recent["Bucket"] == "long", column].iloc[-1]]  # The tag on the right-hand panel
        cs.hide_numbers_under_tags(axes[-1], last_values)  # Hide any axis number that tag would cover
        return cs.save(fig, CHART_DIR / file_name)  # Save as SVG and close the figure


def scorecard_chart(scored):
    """Draw the scorecard: a table of the last 10 scored auctions, newest at the top.

    scored -- the scored table from scoring.load_scored()
    Returns the path of the saved image.
    Labels are written in words and boxed: "strong" in a navy box, "weak" in a grey box, "normal" plain, so the label
    never relies on colour alone. A gold dot marks the latest auction, as on the other charts.
    """
    usable = scored[scored["Label"].isin(["strong", "normal", "weak"])]  # Only auctions with a real label
    rows = usable.tail(10).iloc[::-1]              # The last 10, reversed so the newest is at the top
    columns = [                                    # (heading, x position from 0 to 1, alignment, how to write each value)
        ("Date", 0.02, "left", lambda r: f"{r['Auction Date']:%d %b %y}"),  # e.g. "03 Nov 26"
        ("Gilt", 0.13, "left", lambda r: r["Gilt Name"]),  # e.g. "4 5/8% Green Gilt 2037"
        ("Bucket", 0.43, "left", lambda r: r["Bucket"]),  # short / medium / long
        ("Cover (x)", 0.60, "right", lambda r: f"{r[scoring.COVER]:.2f}"),  # e.g. "3.38"
        ("Cover pct", 0.70, "right", lambda r: f"{r['Cover Pct']:.0f}"),  # e.g. "73"
        ("Tail (bp)", 0.80, "right", lambda r: f"{r[scoring.TAIL]:.1f}"),  # e.g. "0.3"
        ("Tail pct", 0.89, "right", lambda r: f"{r['Tail Pct']:.0f}"),  # e.g. "60"
        ("Label", 0.92, "left", None),             # Drawn separately below, as a boxed tag
    ]                                              # End of the list
    row_height = 1 / (len(rows) + 1.3)             # Split the height between the header and the 10 rows
    with plt.rc_context(cs.rc_params()):           # Apply the house style just while this chart is drawn
        fig, ax = cs.new_figure(size=cs.WIDE_SIZE)  # One full-width card
        fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02)  # A table can use the whole image
        ax.axis("off")                             # No axes, ticks or gridlines: this is a table, not a plot
        ax.set_xlim(0, 1)                          # Positions run from 0 (left edge)...
        ax.set_ylim(0, 1)                          # ...to 1 (right edge / top)
        header_y = 1 - row_height * 0.6            # Height of the header row
        for heading, x, align, _ in columns:       # Each column heading...
            ax.text(x, header_y, heading, ha=align, va="center", fontsize=8.5, fontweight="bold", color=cs.DARK_GREY)  # ...in bold
        ax.plot([0, 1], [header_y - row_height / 2] * 2, color=cs.DARK_GREY, linewidth=0.8)  # A line under the headings

        for i, (_, row) in enumerate(rows.iterrows()):  # Each auction, newest first (i = 0, 1, 2...)
            y = header_y - row_height * (i + 1)    # This row's height on the page
            for heading, x, align, write in columns[:-1]:  # Every column except the label
                ax.text(x, y, write(row), ha=align, va="center", fontsize=8.5, color=cs.DARK_GREY)  # The value
            boxed = {"strong": {"facecolor": cs.NAVY, "edgecolor": "none"},  # Strong: white text in a navy box
                     "weak": {"facecolor": cs.LIGHT_GREY, "edgecolor": "none"}}.get(row["Label"])  # Weak: a grey box
            ax.text(0.92, y, row["Label"], ha="left", va="center", fontsize=8.5, fontweight="bold",  # The label...
                    color=cs.WHITE if row["Label"] == "strong" else cs.DARK_GREY,  # ...white on navy, otherwise grey
                    bbox={"boxstyle": "square,pad=0.25", **boxed} if boxed else None)  # ...boxed unless "normal"
            if i == 0:                             # The newest auction...
                ax.scatter([0.008], [y], s=18, color=cs.GOLD, zorder=5)  # ...gets a gold dot at the start of its row
            ax.plot([0, 1], [y - row_height / 2] * 2, color=cs.LIGHT_GREY, linewidth=0.6)  # A light line under each row
        return cs.save(fig, CHART_DIR / "scorecard")  # Save as SVG and close the figure


def describe(number):
    """Format a number without pointless decimals, e.g. 0.40 -> "0.4", 1.00 -> "1".

    number -- any number
    Returns it as text.
    """
    return f"{number:g}"                           # ":g" drops trailing zeros


def make_charts(scored=None):
    """Draw all three charts and write their numbered takeaway titles, subtitles and source line.

    scored -- the scored table from scoring.load_scored(); worked out here if not given
    Returns a list of three dictionaries, one per chart: "number", "title", "subtitle", "source" and "path".
    """
    if scored is None:                             # Not given...
        scored = scoring.load_scored()             # ...so score the auctions now
    CHART_DIR.mkdir(parents=True, exist_ok=True)   # Create docs/charts/ if it doesn't exist yet
    source = source_line()                         # The same source line for every chart
    latest = latest_scored(scored)                 # The auction the titles are about
    peers = scoring.peers_for(scored, latest)      # Its peer group (same bucket, previous 3 years)
    median_tail = peers[scoring.TAIL].median()     # The typical tail in that group: half wider, half narrower
    if latest[scoring.TAIL] < median_tail:         # Narrower than usual
        tail_words = "narrower than"               # e.g. "0.2bp, narrower than the median of 0.4bp"
    elif latest[scoring.TAIL] > median_tail:       # Wider than usual
        tail_words = "wider than"                  # e.g. "0.8bp, wider than the median of 0.4bp"
    else:                                          # Exactly typical
        tail_words = "in line with"                # e.g. "0.4bp, in line with the median of 0.4bp"
    last10 = scored[scored["Label"].isin(["strong", "normal", "weak"])].tail(10)  # The auctions on the scorecard
    counts = last10["Label"].value_counts()        # How many of each label among them
    stale = stale_note(scored)                     # e.g. " No long-bucket auctions since 21 Oct 2025." (or "")

    return [                                       # One dictionary per chart, in the order they appear
        {"number": 1,                              # Chart 1: cover history
         "title": (f"1. Cover at the latest auction was {latest[scoring.COVER]:.2f}x, higher than "  # The takeaway,
                   f"{latest['Cover Pct']:.0f}% of {latest['Bucket']}-bucket auctions in the past 3 years"),  # in words
         "subtitle": ("Bid-to-cover ratio (amount bid / amount sold) at each conventional gilt auction, by maturity "  # What
                      "bucket, times. Gold dot: latest auction." + stale),  # the chart shows, plus any stale-bucket note
         "source": source,                         # Where the data comes from
         "path": history_chart(scored, scoring.COVER, "cover_history", "{:.2f}")},  # Draw it; remember where it went
        {"number": 2,                              # Chart 2: tail history
         "title": (f"2. The latest tail was {describe(latest[scoring.TAIL])}bp, {tail_words} the "  # The takeaway
                   f"{latest['Bucket']}-bucket median of {describe(median_tail)}bp"),  # e.g. "...median of 0.4bp"
         "subtitle": ("Tail (yield at lowest accepted price minus yield at average accepted price) at each "  # What the
                      "conventional gilt auction, by maturity bucket, basis points. Gold dot: latest auction."  # chart
                      + stale),                    # shows, plus any stale-bucket note
         "source": source,                         # Where the data comes from
         "path": history_chart(scored, scoring.TAIL, "tail_history", "{:.1f}")},  # Draw it; remember where it went
        {"number": 3,                              # Chart 3: scorecard
         "title": (f"3. Of the last 10 auctions, {counts.get('strong', 0)} scored strong, "  # The takeaway: how many
                   f"{counts.get('normal', 0)} normal and {counts.get('weak', 0)} weak"),  # of each label
         "subtitle": (f"Percentiles against auctions in the same bucket over the previous 3 years (higher = better). "  # How
                      f"Strong: both at least {scoring.STRONG_CUTOFF}. Weak: either {scoring.WEAK_CUTOFF} or lower."),  # to read it
         "source": source,                         # Where the data comes from
         "path": scorecard_chart(scored)},         # Draw it; remember where it went
    ]                                              # End of the list


def main():
    """Draw the charts and print their titles and where they were saved.

    Takes no inputs. Returns nothing; prints to the screen.
    """
    for chart in make_charts():                    # Each chart in turn
        print(chart["title"])                      # Its numbered takeaway title
        print(f"   {chart['subtitle']}")           # What it shows
        print(f"   {chart['source']}")             # The source line
        print(f"   Saved to {chart['path']}\n")    # Where the image is


if __name__ == "__main__":                         # Only runs when you type "python charts.py" (not when imported)
    main()                                         # Do everything above
