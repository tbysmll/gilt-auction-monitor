"""
publish.py - updates the Gilt Auction Monitor and publishes it to GitHub (and so to the live GitHub Pages site).

Works the same on Windows, Mac and Linux:
  1. runs the main pipeline (main.py --review: data, scoring, Claude review if Claude Code is installed, charts,
     longer-run view, summary, website, README),
  2. commits only the generated results in docs/ and output/, with the message "Update: auction of <date>",
  3. pushes the commit to GitHub; GitHub Pages republishes the site a minute or so later.

Before running it: download any reports the DMO's captcha blocked (main.py lists them). That captcha is also why this
runs on your own computer rather than as a scheduled GitHub Action.

Run it with:  python publish.py             (tries to download the latest DMO reports first)
         or:  python publish.py --offline   (uses the reports already saved in data/)
"""

import argparse                                    # Reads options typed after the script's name, e.g. --offline
import shutil                                      # shutil.which() checks that the git command can be found
import subprocess                                  # Runs other programs (main.py, git) and checks how they finished
import sys                                         # sys.executable (this Python) and sys.exit (stop with a message)
from pathlib import Path                           # Handles folder and file paths the same way on every system

PROJECT_DIR = Path(__file__).resolve().parent      # The project folder: the folder this file is in
PUBLISHED = ["docs", "output"]                     # The only folders this script commits: the website and the run results
PAGES_URL = "https://tbysmll.github.io/gilt-auction-monitor/"  # The live website


def read_options():
    """Read the options typed after "python publish.py".

    Takes no inputs (argparse reads them from the command line). Returns the options; options.offline is True only
    if --offline was typed.
    """
    parser = argparse.ArgumentParser(description="Update the Gilt Auction Monitor and publish it to GitHub.")  # Help text
    parser.add_argument("--offline", action="store_true",  # A switch: skip downloading
                        help="don't download from the DMO; use the reports already saved in data/")  # What it does
    return parser.parse_args()                     # Read what was typed and hand it back
                                                   # (There's deliberately no --sample: the sample data is never published.)


def git(*arguments):
    """Run one git command in the project folder.

    *arguments -- the words after "git", e.g. "push"
    Returns the finished command, so the caller can check .returncode (0 = success).
    Exists so every git command runs in the right folder, whichever folder this script was started from.
    """
    return subprocess.run(["git", *arguments], cwd=PROJECT_DIR)  # e.g. git push, run inside the project folder


def check_git():
    """Stop with a clear message if git isn't installed or this folder isn't a git repository.

    Takes no inputs. Returns nothing.
    """
    if shutil.which("git") is None:                # The git command can't be found
        sys.exit("Git isn't installed (the 'git' command wasn't found). Install it from https://git-scm.com, "  # Say so
                 "then run this again.")           # ...and how to fix it
    inside = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=PROJECT_DIR,  # Ask git whether this
                            capture_output=True, text=True)  # folder is a repository (output hidden)
    if inside.returncode != 0:                     # It isn't
        sys.exit("This folder isn't a git repository, so there's nowhere to publish to. "  # Say so
                 "See the Setup section of README.md.")  # ...and where to look


def run_pipeline(offline):
    """Run main.py --review (and --offline, if asked) with this same Python, and stop if it fails.

    offline -- True to skip downloading
    Returns nothing.
    """
    command = [sys.executable, str(PROJECT_DIR / "main.py"), "--review"]  # This Python running main.py, with the review
    if offline:                                    # --offline was typed...
        command.append("--offline")                # ...so pass it on
    finished = subprocess.run(command, cwd=PROJECT_DIR)  # Run it; its output appears on screen as normal
    if finished.returncode != 0:                   # main.py stopped with an error...
        sys.exit("main.py failed, so nothing was published.")  # ...so don't publish half-finished files


def latest_auction_date():
    """The date of the latest scored auction, e.g. 2026-11-03, for the commit message.

    Takes no inputs. Returns the date as text.
    The project's modules are imported here, not at the top, so this script starts (and can report a missing git)
    without loading pandas and matplotlib first.
    """
    import charts                                  # Our own charts.py: finds the latest scored auction
    import scoring                                 # Our own scoring.py: scores the auctions saved in data/
    latest = charts.latest_scored(scoring.load_scored())  # The most recent auction that got a strong/normal/weak label
    return f"{latest['Auction Date']:%Y-%m-%d}"    # e.g. "2026-11-03"


def main():
    """Run the pipeline, commit docs/ and output/, and push.

    Takes no inputs (reads --offline from the command line). Returns nothing; prints to the screen.
    """
    options = read_options()                       # Was --offline typed?
    check_git()                                    # Stop early if git or the repository is missing
    run_pipeline(options.offline)                  # Data, scoring, review, charts, summary, website, README

    git("add", "--", *PUBLISHED)                   # Stage everything new or changed in docs/ and output/
    if git("diff", "--cached", "--quiet", "--", *PUBLISHED).returncode == 0:  # Exit code 0 here means "no differences"
        print("\nNothing has changed in docs/ or output/ since the last publish.")  # ...so there's nothing to commit
        return                                     # Stop politely

    message = f"Update: auction of {latest_auction_date()}"  # e.g. "Update: auction of 2026-11-03"
    if git("commit", "-m", message, "--", *PUBLISHED).returncode != 0:  # Commit ONLY docs/ and output/, even if other
                                                   # files happen to be staged
        sys.exit("The commit failed (see git's message above), so nothing was pushed.")  # Stop and say why
    if git("push").returncode != 0:                # Send it to GitHub
        sys.exit("The commit was saved on this computer, but the push to GitHub failed (see git's message above). "  # Say
                 "Fix that, then run: git push")   # what happened and how to finish the job
    print(f"\nPublished \"{message}\". The live page updates within a few minutes: {PAGES_URL}")  # Done


if __name__ == "__main__":                         # Only runs when you type "python publish.py" (not when imported)
    main()                                         # Do everything above
