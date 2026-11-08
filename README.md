# Gilt Auction Monitor

Scores every UK government bond (gilt) auction held by the Debt Management Office (DMO) for demand and, optionally, drafts a short review of the latest one with Claude. By Toby Small.

**Live page: [https://tbysmll.github.io/gilt-auction-monitor/](https://tbysmll.github.io/gilt-auction-monitor/)** · Data as of 03 Nov 2026

Each conventional gilt auction is scored on two measures of demand, compared with auctions of similar maturity over the previous three years:

- **Cover** (bid-to-cover ratio): amount bid divided by amount sold. Higher means more demand.
- **Tail**: yield at the lowest accepted price minus yield at the average accepted price, in basis points (1bp = 0.01%). Narrower means bids were bunched together: steadier demand.

## Latest auction: 4 5/8% Green Gilt 2037, 03 Nov 2026

| Measure | Value | Compared with peers |
|---|---|---|
| Verdict | **normal** | strong if both percentiles ≥ 75; weak if either ≤ 25 |
| Cover | 3.38x | higher than 73% of peers |
| Tail | 0.3bp | narrower than 60% of peers |
| Yield at average price | 5.268% | |
| Amount sold | £3,250m nominal | |
| Bucket | medium (10.3 years to maturity) | 55 peers in the previous 3 years |

## Latest charts

**1. Cover at the latest auction was 3.38x, higher than 73% of medium-bucket auctions in the past 3 years**

![1. Cover at the latest auction was 3.38x, higher than 73% of medium-bucket auctions in the past 3 years](docs/charts/cover_history.svg)

Bid-to-cover ratio (amount bid / amount sold) at each conventional gilt auction, by maturity bucket, times. Gold dot: latest auction. No long-bucket auctions since 21 Oct 2025. Source: UK Debt Management Office (D2.1A). Data as of 03 Nov 2026.

**2. The latest tail was 0.3bp, narrower than the medium-bucket median of 0.4bp**

![2. The latest tail was 0.3bp, narrower than the medium-bucket median of 0.4bp](docs/charts/tail_history.svg)

Tail (yield at lowest accepted price minus yield at average accepted price) at each conventional gilt auction, by maturity bucket, basis points. Gold dot: latest auction. No long-bucket auctions since 21 Oct 2025. Source: UK Debt Management Office (D2.1A). Data as of 03 Nov 2026.

**3. Of the last 10 auctions, 4 scored strong, 6 normal and 0 weak**

![3. Of the last 10 auctions, 4 scored strong, 6 normal and 0 weak](docs/charts/scorecard.svg)

Percentiles against auctions in the same bucket over the previous 3 years (higher = better). Strong: both at least 75. Weak: either 25 or lower. Source: UK Debt Management Office (D2.1A). Data as of 03 Nov 2026.

## Claude-drafted review

Drafted by Claude from the latest auction's facts and scores only, with no other data or tools; I check and rewrite it.

> The 3 November 2026 auction of the 4 5/8% Green Gilt 2037 (10.34 years to maturity, in the medium 7 to 15 year bucket) sold £3,250 million nominal, and there was no take-up at the post-auction option facility. The average accepted price was £94.919 per £100 nominal, which is a yield of 5.268%. The bid-to-cover ratio of 3.38 was higher than in 72.7% of the 55 peer auctions, which are medium-bucket conventional auctions held in the previous 3 years. The tail of 0.3 basis points was narrower than in 60.0% of those auctions, so demand was fairly even across accepted bids. Our rule rates an auction strong only if both percentiles are at least 75, and weak if either is 25 or lower; this auction meets neither test, so it is classed as normal.

**Numbers verified against DMO data: 8 of 8 facts matched.**

## Longer-run view

Across all conventional auctions, median cover rose from 2.24x in 2015-21 to 2.98x in 2023-25; the median tail widened from 0.3bp in 2015-21 to 0.5bp in 2023-25; and the median yield at the average accepted price rose from 0.83% in 2015-21 to 4.31% in 2023-25.

| Group | Period | Auctions | Median cover (x) | Median tail (bp) | Median yield (%) |
|---|---|---|---|---|---|
| All conventional | 2015-21 | 337 | 2.24 | 0.3 | 0.83 |
| All conventional | 2023-25 | 171 | 2.98 | 0.5 | 4.31 |
| short | 2015-21 | 115 | 2.28 | 0.3 | 0.37 |
| short | 2023-25 | 68 | 3.04 | 0.5 | 4.10 |
| medium | 2015-21 | 102 | 2.33 | 0.2 | 0.88 |
| medium | 2023-25 | 59 | 2.92 | 0.6 | 4.33 |
| long | 2015-21 | 120 | 2.16 | 0.3 | 1.27 |
| long | 2023-25 | 44 | 3.02 | 0.4 | 4.61 |

Conventional auctions only; each period runs from January of its first year to December of its last. Medians are the middle value, so a single unusual auction can't move them much.

## Method

- Only conventional gilts are scored. Each auction goes in the DMO's maturity bucket for its years left to maturity on the day: short (under 7), medium (7 to 15) or long (over 15).
- Its peers are the auctions in the same bucket over the previous 3 years. With fewer than 10 peers it isn't scored.
- Cover percentile: the share of peers with a lower cover. Tail percentile: the share of peers with a wider tail. Ties count as half. For both, higher is better.
- Strong: both percentiles at least 75. Weak: either 25 or lower. Otherwise normal. So one bad measure is enough to call an auction weak.
- Claude drafts the review from the facts in the headline box only, with no other data or tools. Each auction fact it quotes is then checked against those facts automatically, and I check the draft myself.

## Data challenges

- The DMO's website blocks automated downloads with a captcha, so the auction file is downloaded by hand and the site is rebuilt on my own computer. A scheduled cloud job (e.g. GitHub Actions) isn't used, because the captcha would block it too.
- Index-linked gilt auctions are sold at a single price that every successful bidder pays, so they have no tail and are left out. 918 conventional auctions since 1998 are scored.
- The auction file gives only each gilt's maturity year. Exact redemption dates come from two more DMO reports (gilts in issue, and redeemed gilts); the year alone would put some gilts in the wrong bucket.
- The DMO file has no 'amount bid' column, so cover can't be recalculated from it. Instead, the amount bid is copied from the DMO's result notice for spot checks.
- Cover check, 03 Nov 2026: £10,980.5m bid / £3,250m sold = 3.3786, against the DMO's 3.38: matches.
- Data error: the 4¼% Treasury Gilt 2039 auction on 04 Mar 2009 shows a tail of -5.5bp. A tail can't be negative, so it is left out of all scoring.
- No long-bucket auctions since 21 Oct 2025. Its latest values on the charts are therefore not recent.

## My read: coming soon

## Setup

Runs on your own computer: the DMO's website blocks automated downloads, so a cloud job can't fetch the data.

1. Install Python 3.12 or later, then in this folder run `python -m venv .venv`, activate it, and run `pip install -r requirements.txt`.
2. **Try it straight away** with the sample data in `sample_data/` (the three DMO reports as of 03 Nov 2026): `python main.py --sample`. Nothing is downloaded.
3. **For current data**, run `python main.py`. It tries to download the three DMO reports it needs. If the DMO's bot protection blocks a download, it lists exactly which files to download by hand, with a link and the folder for each, and meanwhile uses the newest copies already saved:
   - Outright Gilt Auctions ([D2.1A](https://www.dmo.gov.uk/data/ExportReport?reportCode=D2.1A)) → save in `data/`
   - Gilts in Issue ([D1A](https://www.dmo.gov.uk/data/ExportReport?reportCode=D1A)) → save in `data/maturities/`
   - Redemption Details of Redeemed Gilts ([D1C](https://www.dmo.gov.uk/data/ExportReport?reportCode=D1C)) → save in `data/maturities/`
4. Once the files are saved, `python main.py --offline` skips the download attempt and uses them.
5. Optionally, add amounts bid from DMO result notices to `data/bids_check.csv` to recheck cover.

Each run scores the auctions, runs the longer-run view, draws the charts and writes `docs/index.html`, `output/summary.md` and this README. No Claude Code or API key is needed.

**Optional: the Claude-drafted review.** Install [Claude Code](https://claude.com/claude-code), log in with a Claude subscription (`claude --version` should work in a new terminal), then run `python main.py --review`. It also drafts a review of the latest auction and checks every auction fact it quotes. If Claude Code isn't found, the run carries on without the review. `publish.bat` runs `main.py --review`, then pushes the results to GitHub.

---

Source: UK Debt Management Office (D2.1A). Data as of 03 Nov 2026. For learning purposes; not investment advice.
