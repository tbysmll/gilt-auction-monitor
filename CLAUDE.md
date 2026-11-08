# Gilt Auction Monitor — instructions for Claude Code

Claude Code reads this file at the start of every conversation in this folder.
Anything written here applies to every task, so I don't have to repeat it.

## What this project is
- I'm Toby, a final-year Economics student at Bath. I know some Python (CS50, pandas basics) but I'm not a developer.
  Treat me as a learner. This project goes on my CV, so I must be able to explain every line and every number in an interview.
- The Gilt Auction Monitor collects the UK Debt Management Office's (DMO) gilt auction results and scores each auction on:
  - **Cover**: the bid-to-cover ratio (gilts bid for ÷ gilts sold). Higher = stronger demand.
  - **Tail**: the gap between the average accepted yield and the lowest accepted yield. A wider tail = weaker, less even demand.
- It then uses Claude to draft a short review of each auction from those numbers. I check and rewrite the drafts myself.
- Charts use the house style in `chart_style.py`, copied from my Oil Curve Tracker project.

## Coding rules (always follow these)
1. **Annotate every line of code.** Every line gets a plain-English comment saying what it does and why,
   either at the end of the line or on the line above. No exceptions, including imports and short lines.
   Every function also gets a docstring explaining its inputs, what it returns, and why it exists.
   Match the commenting style already used in `chart_style.py`.
2. **Keep it simple.** Prefer clear pandas over clever one-liners. No new libraries without asking me first.
3. **Small steps.** Build one file or one function at a time, then stop so I can review and run it.
4. **Explain before and after.** Before writing code, tell me in a few sentences what you'll do. After, tell me
   how to run it and what output I should expect to see.
5. **Teach the finance too.** When code calculates something (a spread, a percentile), explain in one or
   two sentences what it means for the gilt market.
6. **Never print, log or hard-code the API key.** It lives in `.env`, which Git ignores.
