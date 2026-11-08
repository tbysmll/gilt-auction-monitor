"""
scoring.py - scores each conventional gilt auction's cover and tail against similar recent auctions.

What it does:
  1. keeps conventional gilts only (index-linked auctions are sold at one price, so they have no tail),
  2. looks up each gilt's exact redemption (maturity) date in two DMO reports saved in data/maturities/
     (dmo.py finds them, in data/ or, with --sample, in sample_data/),
  3. works out years to maturity on each auction day and puts each auction in a DMO maturity bucket:
     short (under 7 years), medium (7 to 15 years) or long (over 15 years),
  4. compares each auction's cover and tail with its "peers" (same bucket, previous 3 years) as percentiles,
  5. labels it with one rule: strong if cover AND tail both beat at least 75% of peers,
     weak if cover OR tail is in the worst 25%, otherwise normal,
  6. recalculates cover (amount bid / amount sold) for the auctions in data/bids_check.csv and flags any mismatch
     with the DMO's stated cover,
  7. prints the full working for the latest auction, so it can be checked by hand.

Run it with:  python scoring.py
"""

import sys                                         # Lets the script stop early with a clear message (sys.exit)

import pandas as pd                                # Tables of data (like Excel in Python)

import dmo                                         # Our own dmo.py: finds and reads the DMO's Excel reports

DAYS_PER_YEAR = 365.25                             # Average length of a year, allowing for leap years
SHORT_LIMIT = 7                                    # Under 7 years to maturity = short (the DMO's own bucket limits)
LONG_LIMIT = 15                                    # Over 15 years = long; 7 to 15 years = medium

COVER = "Bid to Cover Ratio (times)"               # The DMO's column name for cover (higher = stronger demand)
TAIL = "Yield Tail at Auction (bp)"                # The DMO's column name for the tail (narrower = stronger demand)
SOLD = "Nominal Amount Issued via Auction (£ million)"  # Amount sold in the auction itself (not the later PAOF top-up)
COVER_TOLERANCE = 0.005                            # The DMO rounds cover to 2 decimal places, so a true match is
                                                   # always within half of 0.01
WINDOW_YEARS = 3                                   # Peers are auctions from the 3 years before each auction
MIN_PEERS = 10                                     # With fewer peers than this, a percentile means too little to label
STRONG_CUTOFF = 75                                 # Beating at least 75% of peers = in the best quarter
WEAK_CUTOFF = 25                                   # Beating at most 25% of peers = in the worst quarter

# The DMO writes fractions two ways ("1½%" in some files, "1 1/2%" in others), so names are tidied to one form
FRACTIONS = {"½": " 1/2", "¼": " 1/4", "¾": " 3/4",  # Each single-character fraction...
             "⅛": " 1/8", "⅜": " 3/8", "⅝": " 5/8", "⅞": " 7/8"}  # ...and the "x/y" text that replaces it


def tidy_name(name):
    """Turn a gilt name into one standard spelling, so the same gilt matches across different DMO files.

    name -- a gilt name as the DMO wrote it, e.g. "4⅝% Green Gilt 2037" or "4 5/8%  Green Gilt 2037"
    Returns the tidied name, e.g. "4 5/8% green gilt 2037".
    Exists because the auction file and the maturity files don't always write the same gilt identically.
    """
    name = str(name)                               # Make sure it's text (blank cells come through as numbers)
    for symbol, text in FRACTIONS.items():         # For each fraction character...
        name = name.replace(symbol, text)          # ...swap it for "x/y" text, e.g. "½" -> " 1/2"
    return " ".join(name.lower().split())          # Lower case, and every run of spaces/line breaks becomes one space


def load_maturities():
    """Read every gilt's redemption date from the two DMO maturity reports (Gilts in Issue, and Redemption Details).

    Takes no inputs. Returns a table with one row per gilt: "name_key" (the tidied name) and "Redemption Date".
    Exists because the auction file only gives each gilt's maturity year, and the buckets need the exact date.
    """
    files = [dmo.saved_report("in_issue"), dmo.saved_report("redeemed")]  # The newest copy of each (stops clearly if
                                                   # either is missing)
    tables = []                                    # One small table per file; joined together at the end
    for path in files:                             # Each maturity file in turn
        table = dmo.load_report(path, header_text="Redemption Date")  # Reuse dmo.py's reader; its header row has "Redemption Date"
        name_column = "Gilt Name" if "Gilt Name" in table.columns else table.columns[0]  # Redeemed gilts file: "Gilt Name";
                                                   # gilts in issue file: the first column (headed "Conventional Gilts")
        table = table[[name_column, "Redemption Date"]].copy()  # Keep just the name and the date
        table.columns = ["Gilt Name", "Redemption Date"]  # Same column names for both files
        tables.append(table)                       # Add it to the list

    maturities = pd.concat(tables, ignore_index=True)  # Stack both files into one table
    maturities["Redemption Date"] = pd.to_datetime(maturities["Redemption Date"], errors="coerce")  # Real dates; section
                                                   # headings and notes (e.g. "Ultra-Short", "Note:") have no date and become blank
    maturities = maturities.dropna(subset=["Redemption Date"])  # Drop those non-gilt rows
    maturities["name_key"] = maturities["Gilt Name"].map(tidy_name)  # The tidied name, used for matching
    return maturities[["name_key", "Redemption Date"]].drop_duplicates("name_key")  # One row per gilt


def conventional_only(auctions):
    """Keep conventional gilt auctions and drop index-linked ones.

    auctions -- the auction table from dmo.py
    Returns only the conventional auctions.
    Exists because index-linked auctions are sold at a single price that every winning bidder pays, so there's no
    spread of prices and no tail to score.
    """
    is_linker = auctions["Gilt Name"].str.contains("Index-linked", case=False)  # True for index-linked gilts
    return auctions[~is_linker].copy()             # Keep the rest (~ means "not"); copy so changes don't affect the original


def bucket_for(years):
    """Name the DMO maturity bucket for a given number of years to maturity.

    years -- years left until the gilt is repaid, e.g. 10.3
    Returns "short", "medium" or "long".
    """
    if years < SHORT_LIMIT:                        # Under 7 years
        return "short"                             # e.g. a 2030 gilt auctioned in 2026
    if years <= LONG_LIMIT:                        # 7 to 15 years (including exactly 7 and exactly 15)
        return "medium"                            # e.g. a 2037 gilt auctioned in 2026
    return "long"                                  # Over 15 years, e.g. a 2055 gilt


def add_buckets(auctions, maturities):
    """Add each auction's redemption date, years to maturity and maturity bucket.

    auctions   -- conventional auctions, from conventional_only()
    maturities -- every gilt's redemption date, from load_maturities()
    Returns the auctions with three new columns: "Redemption Date", "Years to Maturity" and "Bucket".
    Stops with a list of names if any auction's gilt can't be found in the maturity files.
    """
    auctions["name_key"] = auctions["Gilt Name"].map(tidy_name)  # Tidy the auction file's names the same way
    auctions = auctions.merge(maturities, on="name_key", how="left")  # Look up each gilt's redemption date
                                                   # ("left" keeps every auction, even if no date is found)
    missing = auctions.loc[auctions["Redemption Date"].isna(), "Gilt Name"].unique()  # Gilts with no date found
    if len(missing) > 0:                           # Any at all...
        sys.exit("No redemption date found for: " + ", ".join(missing))  # ...stop and list them, rather than guess

    days_left = (auctions["Redemption Date"] - auctions["Auction Date"]).dt.days  # Days from auction to repayment
    auctions["Years to Maturity"] = days_left / DAYS_PER_YEAR  # Turned into years, e.g. 3,777 days -> 10.34 years
    auctions["Bucket"] = auctions["Years to Maturity"].map(bucket_for)  # short / medium / long
    return auctions.drop(columns="name_key")       # The tidied name was only needed for matching


def percentile_vs_peers(value, peers, higher_is_better):
    """Work out what percentage of peer auctions this auction beat, from 0 (beat none) to 100 (beat all).

    value            -- this auction's figure, e.g. a cover of 3.38
    peers            -- the same figure for each peer auction (a pandas column)
    higher_is_better -- True for cover (a higher cover beats a lower one); False for tail (a narrower tail wins)
    Returns the percentile, e.g. 81.3.
    Ties count as half a win: tails are quoted to 0.1bp, so many auctions have exactly the same tail, and counting
    ties as half keeps an "ordinary" tail near 50 rather than pushing it to either end.
    """
    if higher_is_better:                           # Cover: beating a peer means having a higher figure
        beaten = (peers < value).sum()             # How many peers had a lower cover
    else:                                          # Tail: beating a peer means having a lower (narrower) figure
        beaten = (peers > value).sum()             # How many peers had a wider tail
    tied = (peers == value).sum()                  # How many peers had exactly the same figure
    return (beaten + 0.5 * tied) / len(peers) * 100  # Share beaten, with ties as half, as a percentage


def peers_for(auctions, auction):
    """Pick the auctions that one auction is compared with.

    auctions -- every scored conventional auction (with "Bucket" and "Data Check" columns)
    auction  -- one row of that table: the auction being scored
    Returns the peer rows: same bucket, auction date in the 3 years before this one, excluding auctions held on the
    same day and auctions with a data problem.
    Exists because demand is only comparable between gilts of similar maturity at a similar time.
    """
    start = auction["Auction Date"] - pd.DateOffset(years=WINDOW_YEARS)  # 3 years earlier, e.g. 3 Nov 2023
    in_window = (auctions["Auction Date"] >= start) & (auctions["Auction Date"] < auction["Auction Date"])  # From that
                                                   # date up to (but not including) the day of this auction
    same_bucket = auctions["Bucket"] == auction["Bucket"]  # Same maturity bucket (short / medium / long)
    usable = ~auctions["Data Check"]               # Leave out auctions whose figures look wrong
    return auctions[in_window & same_bucket & usable]  # Rows meeting all three conditions


def label(cover_pct, tail_pct):
    """Turn the two percentiles into one label, using a rule that fits in one sentence.

    cover_pct -- the percentage of peers this auction's cover beat (100 = highest cover of all)
    tail_pct  -- the percentage of peers this auction's tail beat (100 = narrowest tail of all)
    Returns "strong", "weak" or "normal".
    The rule: strong needs BOTH measures in the best quarter; ONE measure in the worst quarter is enough for weak.
    """
    if cover_pct <= WEAK_CUTOFF or tail_pct <= WEAK_CUTOFF:  # Either measure in the worst quarter of peers...
        return "weak"                              # ...is a warning sign on its own
    if cover_pct >= STRONG_CUTOFF and tail_pct >= STRONG_CUTOFF:  # Both measures in the best quarter of peers
        return "strong"                            # Clearly better demand than usual
    return "normal"                                # Anything in between


def score_auctions(auctions):
    """Give every conventional auction a cover percentile, a tail percentile and a label.

    auctions -- conventional auctions with buckets, from add_buckets()
    Returns the same table with five new columns: "Data Check" (True if its tail is impossible), "Peers" (how many
    auctions it was compared with), "Cover Pct", "Tail Pct" and "Label".
    """
    auctions = auctions.copy()                     # Work on a copy so the input table isn't changed
    auctions["Data Check"] = auctions[TAIL] < 0    # A tail can't be negative (the lowest accepted price always has a
                                                   # yield at least as high as the average price), so a negative one is a data error

    peer_counts, cover_pcts, tail_pcts, labels = [], [], [], []  # Results for each auction, filled in one by one
    for _, auction in auctions.iterrows():         # Each auction in turn (iterrows gives its row number and its row)
        peers = peers_for(auctions, auction)       # The auctions it's compared with
        peer_counts.append(len(peers))             # Remember how many there were

        if auction["Data Check"]:                  # This auction's own figures look wrong...
            cover_pcts.append(None)                # ...so don't score it
            tail_pcts.append(None)                 # (None shows as a blank)
            labels.append("data check")            # Label it so it stands out
            continue                               # Move on to the next auction

        if len(peers) < MIN_PEERS:                 # Too few peers to say what's normal (mostly 1998-2003)
            cover_pcts.append(None)                # Don't score it
            tail_pcts.append(None)                 # Blank
            labels.append("not enough history")    # Say why
            continue                               # Move on to the next auction

        cover_pct = percentile_vs_peers(auction[COVER], peers[COVER], higher_is_better=True)  # Higher cover wins
        tail_pct = percentile_vs_peers(auction[TAIL], peers[TAIL], higher_is_better=False)  # Narrower tail wins
        cover_pcts.append(cover_pct)               # Save the cover percentile
        tail_pcts.append(tail_pct)                 # Save the tail percentile
        labels.append(label(cover_pct, tail_pct))  # Save the label

    auctions["Peers"] = peer_counts                # Add each list as a new column (same order as the rows)
    auctions["Cover Pct"] = cover_pcts             # 0-100: share of peers with a lower cover
    auctions["Tail Pct"] = tail_pcts               # 0-100: share of peers with a wider tail
    auctions["Label"] = labels                     # strong / normal / weak (or why it wasn't scored)
    return auctions                                # The scored table


def check_cover(auctions):
    """Recalculate cover from amount bid / amount sold for the auctions in bids_check.csv, and compare.

    auctions -- the auction table (scored or not; it needs "Auction Date", "Gilt Name", SOLD and COVER)
    Returns a small table: one row per checked auction, with the DMO's cover, our recalculated cover and a result
    (an empty table if there's no bids_check.csv, since the check is optional).
    Exists as a data-quality check: if our own sum doesn't give the DMO's figure, either the file or our
    understanding of "cover" is wrong, and we'd want to know before scoring on it.
    """
    if not dmo.bids_file().exists():               # No hand-copied bids in this run's data folder...
        return pd.DataFrame()                      # ...so nothing to check (an empty table)
    bids = pd.read_csv(dmo.bids_file(), parse_dates=["auction_date"])  # The hand-copied figures, dates read as dates
    bids = bids.dropna(subset=["amount_bid_mn"])   # Ignore rows where the amount bid hasn't been filled in yet
    rows = []                                      # One result per checked auction
    for _, bid in bids.iterrows():                 # Each hand-copied auction in turn
        match = auctions[(auctions["Auction Date"] == bid["auction_date"])  # Same auction day...
                         & (auctions["Gilt Name"].map(tidy_name) == tidy_name(bid["gilt_name"]))]  # ...and same gilt
        if match.empty:                            # Not found in the auction file (e.g. a typo in the CSV)
            rows.append({"Auction Date": bid["auction_date"].date(), "Gilt Name": bid["gilt_name"],  # Show which row...
                         "Result": "not found in auction file"})  # ...and why it couldn't be checked
            continue                               # Move on to the next row
        auction = match.iloc[0]                    # The matching auction (there's only one)
        recalculated = bid["amount_bid_mn"] / auction[SOLD]  # Cover = amount bid / amount sold, e.g. 10,980.5 / 3,250
        difference = recalculated - auction[COVER]  # How far our figure is from the DMO's
        rows.append({"Auction Date": bid["auction_date"].date(),  # The auction day
                     "Gilt Name": auction["Gilt Name"],  # The gilt
                     "Amount Bid (£m)": bid["amount_bid_mn"],  # From the DMO's result notice
                     "Amount Sold (£m)": auction[SOLD],  # From the auction file
                     "Recalculated Cover": round(recalculated, 4),  # Our figure, to 4 decimal places
                     "DMO Cover": auction[COVER],  # The DMO's figure, to 2 decimal places
                     "Result": "matches" if abs(difference) <= COVER_TOLERANCE else "MISMATCH"})  # Within rounding?
    return pd.DataFrame(rows)                      # Turn the list of results into a table


def explain_auction(auctions, date):
    """Print the full working behind one auction's percentiles and label, so it can be checked by hand.

    auctions -- the scored table from score_auctions()
    date     -- the auction day to explain, e.g. pd.Timestamp("2026-11-03")
    Returns nothing; prints to the screen.
    Exists so every number in the output can be traced back to a count you could do yourself in Excel.
    """
    auction = auctions[auctions["Auction Date"] == date].iloc[0]  # The auction on that day (the first, if several)
    print(f"\nWorked example: {auction['Gilt Name']} auctioned on {date.date()}")  # Heading
    print(f"  Bucket: {auction['Bucket']} ({auction['Years to Maturity']:.2f} years to maturity)")  # Which peer group
    if auction["Label"] in ("data check", "not enough history"):  # Not scored, so there's no working to show
        print(f"  Not scored: {auction['Label']} ({auction['Peers']} peers).")  # Say why
        return                                     # Nothing more to print

    peers = peers_for(auctions, auction)           # The same peers score_auctions() used
    start = date - pd.DateOffset(years=WINDOW_YEARS)  # Start of the 3-year window
    print(f"  Peers: {len(peers)} {auction['Bucket']} auctions from {start.date()} "  # How many peers...
          f"to the day before ({(date - pd.Timedelta(days=1)).date()})")  # ...and the dates they cover
    print(peers[["Auction Date", "Gilt Name", COVER, TAIL]].to_string(index=False))  # Every peer, to check by hand

    cover, tail = auction[COVER], auction[TAIL]    # This auction's two figures
    lower = (peers[COVER] < cover).sum()           # Peers with a lower cover (beaten)
    same_cover = (peers[COVER] == cover).sum()     # Peers with the same cover (half a win each)
    wider = (peers[TAIL] > tail).sum()             # Peers with a wider tail (beaten)
    same_tail = (peers[TAIL] == tail).sum()        # Peers with the same tail (half a win each)
    print(f"\n  Cover {cover:.2f}: {lower} peers lower, {same_cover} equal -> "  # The cover sum, step by step
          f"({lower} + {same_cover} x 0.5) / {len(peers)} x 100 = {auction['Cover Pct']:.1f}")  # ...ending in the percentile
    print(f"  Tail {tail:.1f}bp: {wider} peers wider, {same_tail} equal -> "  # The tail sum, step by step
          f"({wider} + {same_tail} x 0.5) / {len(peers)} x 100 = {auction['Tail Pct']:.1f}")  # ...ending in the percentile

    if auction["Label"] == "weak":                 # Explain which part of the rule decided it
        reason = f"cover or tail beat {WEAK_CUTOFF}% of peers or fewer"  # One measure in the worst quarter
    elif auction["Label"] == "strong":             # Both measures in the best quarter
        reason = f"cover and tail both beat at least {STRONG_CUTOFF}% of peers"  # Both in the best quarter
    else:                                          # Neither of the above
        reason = (f"neither measure is in the worst quarter (<= {WEAK_CUTOFF}), "  # Not weak...
                  f"and they are not both in the best quarter (>= {STRONG_CUTOFF})")  # ...and not strong
    print(f"  Label: {auction['Label']}, because {reason}.")  # The verdict and why


def load_scored():
    """Do the whole scoring process in one call: load the saved auctions, keep conventional gilts, bucket and score them.

    Takes no inputs. Returns the scored table of conventional auctions, oldest first.
    Exists so other files (e.g. review.py) can get the scores without repeating these steps.
    """
    auctions = dmo.sort_by_date(dmo.load_report(dmo.saved_report("auctions")))  # All auctions from the newest saved
                                                   # auction file (in data/, or sample_data/ with --sample), oldest first
    bucketed = add_buckets(conventional_only(auctions), load_maturities())  # Conventional only, with buckets added
    return score_auctions(bucketed)                # Add percentiles and labels


def main():
    """Score the auctions and print a summary to check against.

    Takes no inputs. Returns nothing; prints to the screen.
    """
    scored = load_scored()                         # Every conventional auction, bucketed and scored

    print(f"{len(scored)} conventional auctions scored.")  # How many there are
    print("\nLabels by bucket:")                   # Heading for the counts
    order = ["strong", "normal", "weak", "not enough history", "data check"]  # A sensible order for the rows
    counts = pd.crosstab(scored["Label"], scored["Bucket"], margins=True, margins_name="total")  # Count each label in
                                                   # each bucket, with totals ("margins") along the edges
    print(counts.reindex(order + ["total"])[["short", "medium", "long", "total"]].fillna(0).astype(int).to_string())  # Print
                                                   # in a sensible order; 0 where a label never appears

    print("\nAuctions flagged for a data check (left out of every peer group):")  # Heading
    print(scored.loc[scored["Data Check"], ["Auction Date", "Gilt Name", COVER, TAIL]].to_string())  # The rows themselves

    columns = ["Auction Date", "Gilt Name", "Bucket", COVER, "Cover Pct", TAIL, "Tail Pct", "Peers", "Label"]  # To check
    print("\nThe last 10 conventional auctions:")  # Heading for the table below
    print(scored[columns].tail(10).round({COVER: 2, "Cover Pct": 1, "Tail Pct": 1}).to_string())  # Last 10: cover to 2
                                                   # decimal places (as the DMO quotes it), percentiles to 1

    print("\nCover check (amount bid / amount sold, against the DMO's stated cover):")  # Heading
    print(check_cover(scored).to_string(index=False))  # One row per auction in bids_check.csv

    explain_auction(scored, scored["Auction Date"].iloc[-1])  # Full working for the latest auction


if __name__ == "__main__":                         # Only runs when you type "python scoring.py" (not when imported)
    main()                                         # Do everything above
