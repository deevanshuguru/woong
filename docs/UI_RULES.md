# UI rules — accumulated decisions (append only)

- Rank displays as "#N", quiet, beside the basket name. No "Rank N of M" noise.
- Baskets show counts as "X stocks · Y ETFs".
- Light theme default; dark mode supported per page via [data-theme] tokens;
  user choice persists (localStorage: woong-theme); system preference is fallback.
- Font: Poppins (Groww), system fallback stack. Tabular numerals on all numbers.
- Colors: accent #2456d6 (light) / #5b83ff (dark); good green for outperformance,
  red for underperformance — applied to return numbers AND basket chart lines.
- Nifty comparison line on charts is dotted grey; basket line is solid.
- Chart interaction: hover crosshair + tooltip (date, basket, Nifty). Inline SVG only.
- Minimum investment = whole shares only: smallest amount where every stock
  receives ≥1 full share at target weight. No fractional buying, ever.
- Time display: relative ("3M ago", "2w ago"), not raw dates, in cards.
- Chips and labels: Title Case. Sort control always labeled "Sort by".
- Strategy/tag filter: removed. Risk filter rows are colored (green/amber/red).
- 1M return comparator chips: Any / Negative / Positive / 0–5% / Above 5%.
- Card click opens a right slide-over quick view; full page at /basket/{id}.
  ESC, scrim, and ✕ close the slide-over.
- Border radius tokens: cards 12px, controls 8px, pills 999px — nothing else.
- Dummy data pages carry the yellow pill "Dummy data · design preview".
- Footer on baskets pages: "Baskets are rule outputs, not investment advice."
- No advice words (buy/sell/target/recommend), no tech verbiage, no metric IDs
  in the UI. Ever.
