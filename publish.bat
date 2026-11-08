@echo off
REM publish.bat - updates the Gilt Auction Monitor and publishes it to GitHub (and so to the live GitHub Pages site).
REM Before running it: download the latest D2.1A file from the DMO into data\ (the DMO's captcha blocks automatic
REM downloads, which is also why this runs on your own computer rather than as a GitHub Action).
REM Double-click it, or type publish.bat in a terminal in this folder.

REM Work in the folder this file is in, wherever it was started from (%~dp0 means "this file's folder")
cd /d "%~dp0"

REM Run the whole project with the Claude-drafted review switched on: scoring, Claude's draft, the fact check,
REM charts, longer-run view, summary, website and README (without Claude Code it carries on with no review)
.venv\Scripts\python.exe main.py --review
REM If main.py stopped with an error, stop here rather than publish half-finished files
if errorlevel 1 (
  REM Say why nothing was published
  echo main.py failed, so nothing was published.
  REM Leave with an error code
  exit /b 1
REM End of the error check
)

REM Ask Python for the latest scored auction's date (e.g. 2026-11-03) and keep it as AUCTION, for the commit message
for /f "delims=" %%d in ('.venv\Scripts\python.exe -W ignore -c "import charts, scoring; print(charts.latest_scored(scoring.load_scored())['Auction Date'].strftime('%%Y-%%m-%%d'))"') do set AUCTION=%%d

REM Stage only the generated results: the website (docs\), the run summary and drafts (output\) and the README
git add docs output README.md
REM If none of them changed since the last publish, there's nothing to commit, so stop politely
git diff --cached --quiet && (
  REM Say so
  echo Nothing has changed since the last publish.
  REM Leave without an error
  exit /b 0
REM End of the no-changes check
)

REM Save the staged files as one commit, named after the auction it covers
git commit -m "Update: auction of %AUCTION%"
REM Send the commit to GitHub; GitHub Pages republishes the site a minute or so later
git push
REM Say where to look
echo Published. The live page updates within a few minutes: https://tbysmll.github.io/gilt-auction-monitor/
