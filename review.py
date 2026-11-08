"""
review.py - asks Claude to draft a short sell-side style review of the latest gilt auction, then checks its numbers.

How it works:
  1. takes the latest conventional auction's facts and scores from scoring.py,
  2. fills them into the prompt in prompts/auction_review.txt (a plain text file, so you can read exactly what's sent),
  3. sends that prompt to Claude through the Claude Code command line ("claude -p"), using your logged-in Claude
     subscription (no API key) and with every tool switched off,
  4. saves the draft in output/,
  5. pulls every number out of the draft and checks it against the facts, flagging any that don't match.

The draft is a starting point: you check it and rewrite it yourself.

Run it with:  python review.py
"""

import json                                        # Reads the JSON reply that "claude -p --output-format json" prints
import os                                          # Gives access to environment variables (to remove any API key)
import re                                          # Regular expressions: finds the numbers inside the draft text
import shutil                                      # shutil.which() checks the claude command can be found
import subprocess                                  # Runs another program (claude) from Python and collects its output
import sys                                         # Lets the script stop early with a clear message (sys.exit)
import tempfile                                    # Finds the computer's temporary folder
from pathlib import Path                           # Handles folder and file paths the same way on Windows and Mac

import pandas as pd                                # Tables of data (like Excel in Python)

import scoring                                     # Our own scoring.py: the bucketed and scored auctions

PROJECT_DIR = Path(__file__).parent                # The folder this script is in
PROMPT_FILE = PROJECT_DIR / "prompts" / "auction_review.txt"  # The prompt template, with a {facts} slot
OUTPUT_DIR = PROJECT_DIR / "output"                # Where drafts are saved
CLAUDE_TIMEOUT = 300                               # Give up if Claude hasn't replied within 5 minutes
NUMBER_PATTERN = r"\d+(?:,\d{3})*(?:\.\d+)?"      # A number: digits, optional thousands commas, optional decimals
                                                   # e.g. "3", "3,250", "10.34"; the minus sign is ignored
CHECKED_FACTS = [                                  # The auction facts and scores the verification counts...
    "Amount sold at auction (£ million nominal)",  # ...amount sold, e.g. 3,250
    "Average accepted price (£ per £100 nominal)",  # ...average accepted price, e.g. 94.919
    "Yield at average accepted price (%)",         # ...yield, e.g. 5.268
    "Bid-to-cover ratio",                          # ...cover, e.g. 3.38
    "Tail (basis points)",                         # ...tail, e.g. 0.3
    "Cover percentile",                            # ...cover percentile, e.g. 72.7
    "Tail percentile",                             # ...tail percentile, e.g. 60.0
    "Peer auctions",                               # ...number of peer auctions, e.g. 55
]                                                  # Every other number we give Claude (the date, the gilt's name, the
                                                   # bucket limits, the 3-year window, the 75/25 cut-offs) is context
EXTRA_CONTEXT = [100]                              # Numbers from the wording, not the facts: "£ per £100 nominal"


def latest_auction_facts(scored=None):
    """Collect the facts and scores of the latest scored conventional auction, ready to give to Claude.

    scored -- the scored table from scoring.load_scored(); worked out here if not given
    Returns a dictionary of {description: value as text}, e.g. {"Bid-to-cover ratio": "3.38"}.
    Exists so the prompt only ever contains numbers we have checked, written the way we want them quoted.
    """
    if scored is None:                             # Not given...
        scored = scoring.load_scored()             # ...so score every conventional auction now
    usable = scored[scored["Label"].isin(["strong", "normal", "weak"])]  # Only auctions that got a real label
    auction = usable.iloc[-1]                      # The most recent of those
    date = auction["Auction Date"]                 # Its auction day
    paof = auction["Nominal Amount Issued via PAOF (£ million)"]  # The post-auction top-up (blank if none was sold)
    low, high = scoring.SHORT_LIMIT, scoring.LONG_LIMIT  # Bucket limits (7 and 15 years), for describing the bucket
    bucket_ranges = {"short": f"under {low} years", "medium": f"{low} to {high} years", "long": f"over {high} years"}  # Each
                                                   # bucket in words
    return {                                       # Each fact as text, written exactly as Claude should quote it
        "Auction date": f"{date.day} {date.strftime('%B %Y')}",  # e.g. "3 November 2026"
        "Gilt": auction["Gilt Name"],              # e.g. "4 5/8% Green Gilt 2037"
        "Years to maturity": f"{auction['Years to Maturity']:.2f}",  # e.g. "10.34"
        "Maturity bucket": f"{auction['Bucket']} ({bucket_ranges[auction['Bucket']]})",  # e.g. "medium (7 to 15 years)"
        "Amount sold at auction (£ million nominal)": f"{auction[scoring.SOLD]:,.0f}",  # e.g. "3,250"
        "Post-auction option facility (PAOF) take-up (£ million nominal)":  # The extra amount sold just after the auction
            "none" if pd.isna(paof) else f"{paof:,.3f}",  # "none" if blank, otherwise e.g. "1,062.500"
        "Bid-to-cover ratio": f"{auction[scoring.COVER]:.2f}",  # e.g. "3.38"
        "Average accepted price (£ per £100 nominal)": f"{auction['Average Accepted Price (AAP) (£)']:.3f}",  # e.g. "94.919"
        "Yield at average accepted price (%)": f"{auction['Yield at AAP (%)']:.3f}",  # e.g. "5.268"
        "Tail (basis points)": f"{auction[scoring.TAIL]:.1f}",  # e.g. "0.3"
        "Peer auctions": f"{auction['Peers']}",    # How many auctions it was compared with, e.g. "55"
        "Peer group": (f"{auction['Bucket']}-bucket conventional auctions "  # Which auctions those are, e.g. "medium-bucket
                       f"in the previous {scoring.WINDOW_YEARS} years"),  # conventional auctions in the previous 3 years"
        "Cover percentile": f"{auction['Cover Pct']:.1f}",  # e.g. "72.7" (share of peers with a lower cover)
        "Tail percentile": f"{auction['Tail Pct']:.1f}",  # e.g. "60.0" (share of peers with a wider tail)
        "Label": auction["Label"],                 # strong / normal / weak
        "Label rule": (f"strong if both percentiles are at least {scoring.STRONG_CUTOFF}; "  # The rule, in one line,
                       f"weak if either is {scoring.WEAK_CUTOFF} or lower; otherwise normal"),  # so Claude uses it correctly
    }                                              # End of the dictionary


def facts_block(facts):
    """Write the facts as a simple list, one per line, for the prompt.

    facts -- the dictionary from latest_auction_facts()
    Returns text like "- Bid-to-cover ratio: 3.38" on each line.
    """
    return "\n".join(f"- {name}: {value}" for name, value in facts.items())  # One "- name: value" line per fact


def build_prompt(facts_text):
    """Put the facts into the prompt template from prompts/auction_review.txt.

    facts_text -- the list of facts from facts_block()
    Returns the full prompt that will be sent to Claude.
    Exists so the wording of the instructions lives in a file you can read and edit, not inside the code.
    """
    template = PROMPT_FILE.read_text(encoding="utf-8")  # The instructions, with a {facts} slot at the end
    return template.replace("{facts}", facts_text)  # Swap the slot for the real facts


def claude_available():
    """Check whether the Claude Code command line ("claude") can be found on this computer.

    Takes no inputs. Returns True if it can, False if not.
    Exists so main.py can skip the review politely when Claude Code isn't installed.
    """
    return shutil.which("claude") is not None      # shutil.which searches the PATH, as typing "claude" in a terminal does


def ask_claude(prompt):
    """Send the prompt to Claude through the Claude Code command line and return Claude's reply as text.

    prompt -- the full prompt from build_prompt()
    Returns the draft review text (the "result" field of Claude's JSON reply).
    Stops with a clear message if the claude command is missing, fails, times out or returns an error.
    """
    if not claude_available():                     # Windows can't find the claude command at all
        sys.exit("Couldn't find the 'claude' command. Check that 'claude --version' works in a new terminal "  # Stop
                 "(Claude Code must be installed and on your PATH), then run this again.")  # and say how to fix it

    command = ["claude",                           # The Claude Code command line...
               "-p",                               # ...in non-interactive "print" mode: answer once, then exit
               "--output-format", "json",          # Reply as JSON, so the text can be read reliably from "result"
               "--tools", "",                      # An empty list of tools: Claude can't read files, run code or browse
               "--no-session-persistence"]         # Don't save this as a conversation that could be resumed later
                                                   # (No --bare: that would skip your logged-in subscription.)

    environment = os.environ.copy()                # A copy of this program's settings, to hand to claude...
    environment.pop("ANTHROPIC_API_KEY", None)     # ...minus any API key, so only your subscription login can be used

    try:                                           # Running another program can fail in several ways; catch them
        finished = subprocess.run(command,         # Run claude...
                                  input=prompt,    # ...sending it the prompt on standard input (avoids limits on the
                                                   # length of a Windows command line)
                                  capture_output=True,  # Collect what it prints instead of showing it
                                  text=True, encoding="utf-8",  # Treat that as text, in UTF-8 (so "£" survives)
                                  env=environment,  # Use the settings without an API key
                                  cwd=tempfile.gettempdir(),  # Run it from the temp folder, so Claude Code doesn't load
                                                   # this project's CLAUDE.md (coding rules) into the review prompt
                                  timeout=CLAUDE_TIMEOUT)  # Give up after 5 minutes
    except subprocess.TimeoutExpired:              # No reply in time
        sys.exit(f"Claude didn't reply within {CLAUDE_TIMEOUT} seconds. Try again later.")  # Stop with a clear message
    except OSError as error:                       # The program couldn't be started at all
        sys.exit(f"Couldn't start the claude command ({error}).")  # Stop and say why

    if finished.returncode != 0:                   # claude reports success with exit code 0; anything else is a failure
        sys.exit(f"The claude command failed (exit code {finished.returncode}):\n"  # Stop, showing the code...
                 f"{finished.stderr.strip() or finished.stdout.strip()}")  # ...and its error message

    try:                                           # The reply should be JSON...
        reply = json.loads(finished.stdout)        # ...so turn it into a Python dictionary
    except json.JSONDecodeError:                   # It wasn't (e.g. a login prompt or a warning instead)
        sys.exit(f"Claude's reply wasn't valid JSON:\n{finished.stdout[:500]}")  # Stop and show the start of it

    if reply.get("is_error") or not reply.get("result"):  # Claude itself reported a problem, or the reply was empty
        sys.exit(f"Claude returned an error: {reply.get('result') or reply.get('subtype')}")  # Stop and show it
    return reply["result"].strip()                 # The draft review text


def to_number(text):
    """Turn a number written as text into a decimal, e.g. "3,250" -> 3250.0.

    text -- the number as written, with or without thousands commas
    Returns it as a float.
    """
    return float(text.replace(",", ""))           # Remove the commas, then read it as a decimal


def find_match(number_text, candidates, rounded):
    """Look for a number among some candidates, either exactly or after rounding.

    number_text -- the number as written in the draft, e.g. "73"
    candidates  -- {name: value} pairs to compare it with, e.g. {"Cover percentile": 72.7}
    rounded     -- False: only an exact match counts; True: a candidate rounded to the draft's decimal places counts
    Returns the (name, value) that matched, or None.
    """
    value = to_number(number_text)                 # The draft's number as a decimal, e.g. 73.0
    decimals = len(number_text.split(".")[1]) if "." in number_text else 0  # How many decimal places the draft used
    for name, candidate in candidates.items():     # Each candidate in turn
        if candidate == value or (rounded and round(candidate, decimals) == value):  # Exact, or (if allowed) rounded
            return name, candidate                 # e.g. ("Cover percentile", 72.7)
    return None                                    # No candidate matched


def check_numbers(draft, facts):
    """Check the auction facts and scores quoted in the draft against the facts Claude was given.

    draft -- the review text from Claude
    facts -- the facts given to Claude, from latest_auction_facts()
    Returns a table with one row per fact-like number in the draft: the number, which fact it matched, and its verdict
    ("exact", "rounded from 72.7" or "NOT IN FACTS").
    Context numbers (the date, the gilt's name, the bucket limits, "per £100", etc.) are skipped, so only real claims
    about the auction count. Numbers written in words (e.g. "three years") aren't caught, so still read the draft.
    """
    checked = {name: to_number(re.findall(NUMBER_PATTERN, facts[name])[0]) for name in CHECKED_FACTS}  # The 8 facts
                                                   # being checked, as numbers, e.g. {"Bid-to-cover ratio": 3.38, ...}
    context_numbers = [to_number(n) for name, text in facts.items() if name not in CHECKED_FACTS  # Every number in the
                       for n in re.findall(NUMBER_PATTERN, str(text))] + EXTRA_CONTEXT  # other facts, plus "£100"
    context = {f"context {i}": n for i, n in enumerate(context_numbers)  # The context numbers as {label: value}...
               if n not in checked.values()}       # ...minus any that equal a checked fact, so a fact is never skipped
    rows = []                                      # One result per fact-like number found in the draft
    for number_text in re.findall(NUMBER_PATTERN, draft):  # Each number in the draft, in order
        exact_fact = find_match(number_text, checked, rounded=False)  # 1. Exactly one of the checked facts?
        if exact_fact:                             # Yes...
            rows.append({"Number in draft": number_text, "Fact": exact_fact[0], "Check": "exact"})  # ...record it
            continue                               # Next number
        if find_match(number_text, context, rounded=False):  # 2. Exactly a context number (e.g. 2037, 100)?
            continue                               # Not a claim about the auction's results: skip it
        rounded_fact = find_match(number_text, checked, rounded=True)  # 3. A checked fact after rounding (72.7 -> 73)?
        if rounded_fact:                           # Yes...
            rows.append({"Number in draft": number_text, "Fact": rounded_fact[0],  # ...record which fact...
                         "Check": f"rounded from {rounded_fact[1]:g}"})  # ...and show the rounding (":g" drops zeros)
            continue                               # Next number
        if find_match(number_text, context, rounded=True):  # 4. A context number after rounding (10.34 -> 10.3)?
            continue                               # Skip it too
        rows.append({"Number in draft": number_text, "Fact": "-", "Check": "NOT IN FACTS"})  # 5. Matches nothing: flag it
    return pd.DataFrame(rows, columns=["Number in draft", "Fact", "Check"])  # As a table (with headings even if empty)


def verification_summary(checks):
    """Count how many of the auction facts quoted in the draft were correct.

    checks -- the table from check_numbers()
    Returns (matched, total), e.g. (8, 8): "8 of 8 facts matched". Each checked fact counts once, however many times
    the draft repeats it; every number that matches no fact adds one to the total as a failure.
    Exists so main.py and the web page report the check the same way.
    """
    matched = checks.loc[checks["Check"] != "NOT IN FACTS", "Fact"].nunique()  # Different facts quoted correctly
    failed = int((checks["Check"] == "NOT IN FACTS").sum())  # Numbers that match no fact
    return int(matched), int(matched) + failed     # e.g. (8, 8), or (7, 8) if one number was wrong


def verification_text(checks):
    """The one-line result of the fact check, worded the same everywhere (terminal, summary, website, README).

    checks -- the table from check_numbers()
    Returns (passed, text): passed is True only if at least one fact was quoted and every fact-like number matched;
    text is e.g. "Numbers verified against DMO data: 8 of 8 facts matched", or a warning listing the failures.
    """
    matched, total = verification_summary(checks)  # e.g. (8, 8)
    if total > 0 and matched == total:             # Every fact quoted in the draft is correct
        return True, f"Numbers verified against DMO data: {matched} of {total} facts matched"  # The badge text
    if total == 0:                                 # The draft quoted none of the facts
        return False, "Warning: the draft quotes none of the auction's facts, so nothing could be verified"  # Say so
    failed = checks.loc[checks["Check"] == "NOT IN FACTS", "Number in draft"]  # The numbers that matched no fact
    return False, (f"Warning: only {matched} of {total} facts matched the DMO data. "  # Say so plainly...
                   f"Not found in the facts: {', '.join(failed)}. Correct the draft before using it")  # ...and list them


def unmentioned_facts(checks):
    """List the checked facts the draft never quotes (for information; leaving a fact out isn't an error).

    checks -- the table from check_numbers()
    Returns a list of fact names, e.g. ["Peer auctions"].
    """
    quoted = set(checks["Fact"])                   # Facts the draft quoted
    return [name for name in CHECKED_FACTS if name not in quoted]  # The rest, in the usual order


def draft_review(scored=None):
    """Do the whole review step: build the prompt, ask Claude, save the draft and check its numbers.

    scored -- the scored table from scoring.load_scored(); worked out here if not given
    Returns a dictionary: "facts" (the facts given to Claude), "facts_text" (the same, as a list), "draft" (Claude's
    text), "path" (where the draft was saved) and "checks" (the number check table).
    Exists so main.py can run this step with one call.
    """
    facts = latest_auction_facts(scored)           # The latest auction's facts and scores, as text
    facts_text = facts_block(facts)                # Written as a list
    prompt = build_prompt(facts_text)              # Put into the prompt template

    print("Facts sent to Claude:")                 # Show exactly what Claude was given
    print(facts_text)                              # One fact per line
    print("\nAsking Claude for a draft (this usually takes 10 to 30 seconds)...")  # So a pause doesn't look like a crash
    draft = ask_claude(prompt)                     # Claude's draft review

    OUTPUT_DIR.mkdir(exist_ok=True)                # Create output/ if it doesn't exist yet
    date = pd.to_datetime(facts["Auction date"], dayfirst=True).date()  # The auction day, for the file name
    path = OUTPUT_DIR / f"review_{date.isoformat()}.txt"  # e.g. output/review_2026-11-03.txt
    path.write_text(draft + "\n", encoding="utf-8")  # Save the draft (UTF-8, so "£" is kept)
    checks = check_numbers(draft, facts)           # Check the facts quoted in the draft
    return {"facts": facts, "facts_text": facts_text, "draft": draft, "path": path, "checks": checks}  # Everything


def main():
    """Draft the latest auction review with Claude, save it, and check its numbers.

    Takes no inputs. Returns nothing; prints to the screen and saves the draft in output/.
    """
    result = draft_review()                        # Prompt, Claude, save, check
    draft, path, checks = result["draft"], result["path"], result["checks"]  # The parts printed below

    print(f"\nDraft (saved to {path}):\n")         # Heading, with where it was saved
    print(draft)                                   # The draft itself

    print("\nFact check (auction facts and scores quoted in the draft):")  # Heading
    print(checks.to_string(index=False) if not checks.empty else "  No facts found in the draft.")  # The results
    print(f"\n{verification_text(checks)[1]}.")   # The headline result, or a warning listing any failures
    missing = unmentioned_facts(checks)            # Facts the draft didn't quote
    if missing:                                    # Any...
        print(f"Not mentioned (not an error): {', '.join(missing)}")  # ...listed for information


if __name__ == "__main__":                         # Only runs when you type "python review.py" (not when imported)
    main()                                         # Do everything above
