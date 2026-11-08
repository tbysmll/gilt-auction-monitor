"""
analysis.py - the "Longer-run view": compares conventional gilt auctions in two periods of years.

For each period it counts the auctions and takes the median bid-to-cover, median tail and median yield at the average
accepted price, for all conventional auctions together and for each maturity bucket. The median is the middle value
once the auctions are sorted, so one unusual auction (e.g. a failed auction or a data error) can't drag it far.

The site and README compare 2015-2021 with 2023-2025 (see PERIODS), but compare_periods() takes any two periods.

Run it with:  python analysis.py
"""

import pandas as pd                                # Tables of data (like Excel in Python)

import scoring                                     # Our own scoring.py: the bucketed auctions and their column names

PERIODS = [(2015, 2021), (2023, 2025)]             # The two periods shown on the site: (first year, last year), inclusive
YIELD = "Yield at AAP (%)"                         # The DMO's column name for the yield at the average accepted price
GROUPS = ["All conventional", "short", "medium", "long"]  # The rows of each period: everything, then each bucket


def period_label(period):
    """Write a period like (2015, 2021) as "2015-21".

    period -- (first year, last year)
    Returns the label as text.
    """
    first, last = period                           # e.g. 2015 and 2021
    return f"{first}-{str(last)[-2:]}"             # e.g. "2015-21" (the last two digits of the end year)


def period_stats(auctions, period):
    """Count the auctions in one period and take their median cover, tail and yield, overall and by bucket.

    auctions -- scored conventional auctions, from scoring.load_scored()
    period   -- (first year, last year), both included, e.g. (2015, 2021)
    Returns a table with one row per group (all conventional, short, medium, long) and columns for the period, the
    number of auctions and the three medians.
    """
    first, last = period                           # e.g. 2015 and 2021
    years = auctions["Auction Date"].dt.year       # The year of each auction
    in_period = auctions[years.between(first, last) & ~auctions["Data Check"]]  # Auctions in those years, leaving out
                                                   # any with impossible figures (e.g. the negative tail in 2009)
    rows = []                                      # One row per group
    for group in GROUPS:                           # All conventional, then each bucket
        data = in_period if group == "All conventional" else in_period[in_period["Bucket"] == group]  # That group's auctions
        rows.append({"Group": group,               # e.g. "medium"
                     "Period": period_label(period),  # e.g. "2015-21"
                     "Auctions": len(data),        # How many auctions
                     "Median cover (x)": round(data[scoring.COVER].median(), 2),  # Middle bid-to-cover, e.g. 2.24
                     "Median tail (bp)": round(data[scoring.TAIL].median(), 1),  # Middle tail, e.g. 0.3
                     "Median yield (%)": round(data[YIELD].median(), 2)})  # Middle yield at the average price, e.g. 0.83
    return pd.DataFrame(rows)                      # The rows as a table


def compare_periods(auctions, first=PERIODS[0], second=PERIODS[1]):
    """Compare two periods side by side: one row per group and period, with each group's two periods next to each other.

    auctions -- scored conventional auctions, from scoring.load_scored()
    first    -- the earlier period, (first year, last year), e.g. (2015, 2021)
    second   -- the later period, e.g. (2023, 2025)
    Returns a table with columns Group, Period, Auctions, Median cover (x), Median tail (bp), Median yield (%).
    """
    table = pd.concat([period_stats(auctions, first), period_stats(auctions, second)])  # Both periods, one under the other
    table["Group"] = pd.Categorical(table["Group"], categories=GROUPS, ordered=True)  # Keep the groups in GROUPS order...
    table = table.sort_values(["Group", "Period"], kind="stable")  # ...and put each group's two periods together
    table["Group"] = table["Group"].astype(str)    # Back to plain text for printing
    return table.reset_index(drop=True)            # Renumber the rows 0, 1, 2...


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
    """One sentence comparing the two periods for all conventional auctions.

    table -- the comparison from compare_periods()
    Returns e.g. "Median cover rose from 2.24x in 2015-21 to 2.98x in 2023-25, ...".
    """
    overall = table[table["Group"] == "All conventional"]  # The two "all conventional" rows
    early, late = overall.iloc[0], overall.iloc[1]  # The earlier period, then the later one

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

    return (f"Across all conventional auctions, median cover {change('Median cover (x)', 'x', 2)}; "  # Cover...
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
