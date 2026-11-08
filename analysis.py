"""
analysis.py - the "Longer-run view": compares conventional gilt auctions in two periods of years.

For each period it counts the auctions and takes the median bid-to-cover, median tail and median yield at the average
accepted price, for all conventional auctions together and for each maturity bucket. The median is the middle value
once the auctions are sorted, so one unusual auction (e.g. a failed auction or a data error) can't drag it far.

The site and README always compare 2015-2021 with 2023-2025 (see PERIODS). Any two periods, and a single bucket, can
be compared from the command line:  python main.py --compare 2010-2014 2023-2025 --bucket long

Run it with:  python analysis.py   (prints the standard comparison)
"""

import argparse                                    # Only for ArgumentTypeError: the friendly error argparse shows for a
                                                   # badly written period
import re                                          # Regular expressions: checks a period is written like 2015-2021

import pandas as pd                                # Tables of data (like Excel in Python)

import scoring                                     # Our own scoring.py: the bucketed auctions and their column names

PERIODS = [(2015, 2021), (2023, 2025)]             # The standard two periods: (first year, last year), both included
YIELD = "Yield at AAP (%)"                         # The DMO's column name for the yield at the average accepted price
GROUPS = ["All conventional", "short", "medium", "long"]  # The rows of each period: everything, then each bucket
BUCKET_CHOICES = ["all", "short", "medium", "long"]  # What --bucket accepts ("all" = everything plus each bucket)
MIN_AUCTIONS = 10                                  # A median of fewer auctions than this says too little to compare


def parse_period(text):
    """Turn a period typed on the command line, e.g. "2015-2021", into (2015, 2021), or explain what's wrong.

    text -- what the user typed for one period
    Returns (first year, last year).
    Raises argparse.ArgumentTypeError with a friendly message if it isn't two four-digit years in order; argparse
    then prints that message and stops before anything is downloaded.
    """
    match = re.fullmatch(r"\s*(\d{4})\s*-\s*(\d{4})\s*", text)  # Two four-digit years joined by a hyphen
    if not match:                                  # Written some other way (e.g. "2015-21" or "2015")...
        raise argparse.ArgumentTypeError(f"'{text}' isn't a period. Write it as first year-last year, "  # ...explain
                                         "e.g. 2015-2021 (both years in full).")  # with an example
    first, last = int(match.group(1)), int(match.group(2))  # The two years as numbers
    if first > last:                               # Backwards, e.g. 2021-2015...
        raise argparse.ArgumentTypeError(f"'{text}' runs backwards. Put the earlier year first, e.g. {last}-{first}.")  # ...say how to fix it
    return first, last                             # e.g. (2015, 2021)


def period_label(period):
    """Write a period like (2015, 2021) as "2015-21", or a single year like (2020, 2020) as "2020".

    period -- (first year, last year)
    Returns the label as text.
    """
    first, last = period                           # e.g. 2015 and 2021
    if first == last:                              # Just one year...
        return str(first)                          # ...e.g. "2020"
    if first // 100 != last // 100:                # Crosses into a new century (e.g. 1998 to 2000)...
        return f"{first}-{last}"                   # ...so write both years in full: "1998-2000", not "1998-00"
    return f"{first}-{str(last)[-2:]}"             # e.g. "2015-21" (the last two digits of the end year)


def groups_for(bucket):
    """The table rows to show for a --bucket choice.

    bucket -- "all", "short", "medium" or "long"
    Returns ["All conventional", "short", "medium", "long"] for "all", otherwise just that bucket, e.g. ["long"].
    """
    return GROUPS if bucket == "all" else [bucket]  # Everything plus each bucket, or one bucket


def period_stats(auctions, period, groups=GROUPS):
    """Count the auctions in one period and take their median cover, tail and yield, for each group.

    auctions -- scored conventional auctions, from scoring.load_scored()
    period   -- (first year, last year), both included, e.g. (2015, 2021)
    groups   -- which rows to make, e.g. ["All conventional", "short", "medium", "long"] or ["long"]
    Returns a table with one row per group and columns for the period, the number of auctions and the three medians.
    """
    first, last = period                           # e.g. 2015 and 2021
    years = auctions["Auction Date"].dt.year       # The year of each auction
    in_period = auctions[years.between(first, last) & ~auctions["Data Check"]]  # Auctions in those years, leaving out
                                                   # any with impossible figures (e.g. the negative tail in 2009)
    rows = []                                      # One row per group
    for group in groups:                           # Each group asked for
        data = in_period if group == "All conventional" else in_period[in_period["Bucket"] == group]  # That group's auctions
        rows.append({"Group": group,               # e.g. "medium"
                     "Period": period_label(period),  # e.g. "2015-21"
                     "Auctions": len(data),        # How many auctions
                     "Median cover (x)": round(data[scoring.COVER].median(), 2),  # Middle bid-to-cover, e.g. 2.24
                     "Median tail (bp)": round(data[scoring.TAIL].median(), 1),  # Middle tail, e.g. 0.3
                     "Median yield (%)": round(data[YIELD].median(), 2)})  # Middle yield at the average price, e.g. 0.83
    return pd.DataFrame(rows)                      # The rows as a table


def compare_periods(auctions, first=PERIODS[0], second=PERIODS[1], bucket="all"):
    """Compare two periods side by side: one row per group and period, with each group's two periods next to each other.

    auctions -- scored conventional auctions, from scoring.load_scored()
    first    -- one period, (first year, last year), e.g. (2015, 2021)
    second   -- the other period, e.g. (2023, 2025)
    bucket   -- "all" (everything, then each bucket) or one bucket: "short", "medium" or "long"
    Returns a table with columns Group, Period, Auctions, Median cover (x), Median tail (bp), Median yield (%), the
    earlier period first within each group.
    """
    groups = groups_for(bucket)                    # Which rows to make
    early, late = sorted([first, second])          # Put the earlier period first, whichever order they were typed in
    table = pd.concat([period_stats(auctions, early, groups), period_stats(auctions, late, groups)])  # Both periods
    table["Group"] = pd.Categorical(table["Group"], categories=groups, ordered=True)  # Keep the groups in order...
    table = table.sort_values("Group", kind="stable")  # ...and put each group's two periods together (stable keeps
                                                   # the earlier period above the later one)
    table["Group"] = table["Group"].astype(str)    # Back to plain text for printing
    return table.reset_index(drop=True)            # Renumber the rows 0, 1, 2...


def describe_count(count, group):
    """Write a number of auctions in words, e.g. "1 short-bucket auction" or "171 conventional auctions".

    count -- how many auctions
    group -- "All conventional" or a bucket name
    Returns the phrase, singular or plural as needed.
    """
    kind = "conventional" if group == "All conventional" else f"{group}-bucket"  # e.g. "short-bucket"
    return f"{count} {kind} auction{'' if count == 1 else 's'}"  # "1 ... auction", otherwise "... auctions"


def too_few_auctions(table, auctions, minimum=MIN_AUCTIONS):
    """Check each period has enough auctions, in the group being compared, for its medians to mean something.

    table    -- the comparison from compare_periods()
    auctions -- the scored auctions (used to say which years the data covers)
    minimum  -- the fewest auctions allowed (10)
    Returns a friendly message explaining which period is too thin and what to do, or None if all is well.
    The group checked is the one asked for: all conventional auctions for --bucket all, otherwise the one bucket.
    """
    group = table["Group"].iloc[0]                 # "All conventional", or the single bucket asked for
    thin = table[(table["Group"] == group) & (table["Auctions"] < minimum)]  # Its periods with too few auctions
    if thin.empty:                                 # None...
        return None                                # ...all is well
    years = auctions["Auction Date"].dt.year       # Each auction's year
    lines = [f"Can't compare these periods: a median needs at least {minimum} auctions, and"]  # What's wrong...
    for _, row in thin.iterrows():                 # ...for each thin period...
        lines.append(f"  - {row['Period']} has only {describe_count(row['Auctions'], group)}")  # ...how many it has
    advice = "Try a longer period" + ("." if group == "All conventional" else ", or --bucket all.")  # How to fix it
    lines.append(f"The data covers {years.min()} to {years.max()}. {advice}")  # The data's range, and the advice
    return "\n".join(lines)                        # The whole message


def thin_rows_note(table, minimum=MIN_AUCTIONS):
    """A warning about bucket rows with fewer than 10 auctions in a --bucket all table (they're shown, not blocked).

    table   -- the comparison from compare_periods()
    minimum -- the fewest auctions for a reliable median (10)
    Returns e.g. "Note: treat these rows with care, they have fewer than 10 auctions: 1998-99 long (3 auctions).",
    or None if every row has enough.
    """
    thin = table[table["Auctions"] < minimum]      # Rows with too few auctions (only bucket rows can get here, since
                                                   # too_few_auctions() has already stopped the run if the main group is thin)
    if thin.empty:                                 # None...
        return None                                # ...nothing to say
    rows = [f"{row['Period']} {row['Group']} ({describe_count(row['Auctions'], row['Group'])})" for _, row in thin.iterrows()]  # Each thin row
    return f"Note: treat these rows with care, they have fewer than {minimum} auctions: {'; '.join(rows)}."  # The warning


def formatted(table):
    """The comparison with every number written to a fixed number of decimal places, for display.

    table -- the comparison from compare_periods()
    Returns a copy with the medians as text, e.g. 4.1 -> "4.10", so the decimals line up in a table.
    """
    shown = table.copy()                           # Work on a copy; the numbers in the original stay numbers
    for column, decimals in [("Median cover (x)", 2), ("Median tail (bp)", 1), ("Median yield (%)", 2)]:  # Each median...
        shown[column] = shown[column].map(lambda value: f"{value:.{decimals}f}")  # ...e.g. 4.1 -> "4.10"
    return shown                                   # Ready to print or put in a web page


def headline(table):
    """One sentence comparing the two periods for the table's first group (all conventional auctions, or one bucket).

    table -- the comparison from compare_periods()
    Returns e.g. "Across all conventional auctions, median cover rose from 2.24x in 2015-21 to 2.98x in 2023-25, ...".
    """
    group = table["Group"].iloc[0]                 # "All conventional", or the one bucket asked for
    rows = table[table["Group"] == group]          # That group's two rows
    early, late = rows.iloc[0], rows.iloc[1]       # The earlier period, then the later one
    who = "all conventional auctions" if group == "All conventional" else f"{group}-bucket auctions"  # In words

    def change(column, unit, decimals, up="rose", down="fell"):
        """Describe how one median moved between the periods, e.g. "rose from 2.24x in 2015-21 to 2.98x in 2023-25".

        up, down -- the words for a rise and a fall (a tail "widens" or "narrows" rather than rising or falling)
        """
        a, b = early[column], late[column]         # The two medians
        verb = up if b > a else down if b < a else "was unchanged"  # Which way it moved
        if verb == "was unchanged":                # No change...
            return f"{verb} at {a:.{decimals}f}{unit}"  # ...e.g. "was unchanged at 0.3bp"
        return f"{verb} from {a:.{decimals}f}{unit} in {early['Period']} to {b:.{decimals}f}{unit} in {late['Period']}"  # e.g.
                                                   # "rose from 2.24x in 2015-21 to 2.98x in 2023-25"

    return (f"Across {who}, median cover {change('Median cover (x)', 'x', 2)}; "  # Cover...
            f"the median tail {change('Median tail (bp)', 'bp', 1, 'widened', 'narrowed')}; "  # ...tail...
            f"and the median yield at the average accepted price {change('Median yield (%)', '%', 2)}.")  # ...and yield


def main():
    """Print the comparison of the two standard periods and its headline sentence.

    Takes no inputs. Returns nothing; prints to the screen.
    """
    table = compare_periods(scoring.load_scored())  # Score the auctions, then compare 2015-21 with 2023-25
    print(formatted(table).to_string(index=False))  # The table, decimals lined up
    print("\n" + headline(table))                  # The one-sentence summary


if __name__ == "__main__":                         # Only runs when you type "python analysis.py" (not when imported)
    main()                                         # Do everything above
