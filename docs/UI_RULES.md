# UI rules — Woong web surfaces (append only, newest at bottom)

Any agent working on any Woong page: read this file before writing code.
Violating a rule here is a bug, not a style choice.

## Product voice
- No advice words: buy / sell / target / recommend / pick. Ever.
- No tech verbiage: API, endpoint, data file, JS, engine, pipe, snapshot.
- No raw metric IDs in the UI: "One-year return", never "return_1y".
- Baskets pages footer: "Baskets are rule outputs, not investment advice."
- Scanner results footer: "This is a filter and rank result. Not a buy or sell
  recommendation."

## Data honesty
- Dummy/sample data pages carry the yellow pill: "Dummy data · design preview".
- Every screen shows its data date ("As of 18 Sep 2026" / "Prices through ...").
- Missing values render as "—" (title tooltip: "No value for this date"),
  never zero, never blank.
- Numbers that cannot be computed to their real definition are switched off,
  with the reason. Never approximated.

## Numbers
- INR formatting with en-IN grouping (₹1,00,000). Percent with one decimal.
- Tabular numerals everywhere. Signed returns: green positive, red negative,
  "+" prefix on signed comparisons (alpha).
- Minimum investment = whole shares only: smallest amount at which every
  holding receives at least one full share at target weight. Hover tooltip:
  "Whole shares only — no fractional buying". No fractional buying anywhere.
- Time on cards is relative and whole-unit: "2w ago", "3M ago", "1Y ago".
  Never "1.1Y". Exact date appears on hover (title tooltip).
- Basket windows: 1M and since-launch. Both shown with their own comparison
  vs Nifty 50. Chart window = launch date if younger than 1Y, else 1Y.

## Charts
- Inline SVG only. No chart libraries.
- Basket line: solid, green when it beat Nifty over the window, red when not.
- Comparator (Nifty 50): dotted grey line. Comparison baselines are dotted.
- Hover: crosshair + tooltip showing date, basket return %, Nifty return %
  (percent returns from window start, not index levels).

## Layout and components
- Tokens: bg #f6f7f9, panel #fff, ink #1a1d23, muted #6b7280, line #e5e8ec,
  accent #2456d6, good #0a7d33, bad #c23434 (dark variants under
  html[data-theme="dark"]).
- Border radius tokens only: cards 12px, controls 8px, pills 999px.
- Font: Poppins (Groww), system fallback. Desktop only, min 1100px, light+
  dark themes; theme choice persists (localStorage: woong-theme); system
  preference is the fallback.
- Basket card anatomy, in order: name with rank ("#1 Name"); chip row with
  the volatility chip FIRST then tag chips (multi-colored, Title Case);
  "By provider"; chart; dual-window stats; meta footer (stocks/ETFs with
  correct singular/plural, launched, updated with exact-date hover).
- Card click opens the right slide-over quick view. ESC, scrim click, and ✕
  close it. Cards are focusable; Enter opens.
- Sidebar filters: Risk (colored green/amber/red), 1M return comparator chips,
  Min investment chips, Launched, Last updated. Live counts. Reset. Sort
  control always labeled "Sort by". Filter accent color is GREEN (--faccent),
  not the blue accent.
- Strategy/tag filter group: removed from the sidebar (tags show on cards).

## Process
- One surface per commit. Human visual sign-off before every commit.
- After writing any page: audit for unescaped quotes inside string literals
  (the file-transfer gremlin) and backslashes; then browser-test hard-refresh.
- Every UI decision lands in this file the same day it is made.

## v2 additions — baskets (explorer + detail)

- Rules are structured objects (universe, filters[], rank, top), rendered as
  labeled rows (Universe / Filter / AND / Rank / Size) — never as a dotted
  single string. Same presentation on quick view and detail page.
- Basket stats are dual-window: 1M return, 1M vs Nifty, Since-launch return,
  Since-launch vs Nifty. Chart window = launch date if younger than 1Y,
  else 1Y ("as applicable").
- Detail page holdings table: price, whole-share quantity, value at minimum
  investment, weight bar, 1M, 3M — with totals row and an outlay note.
- Detail page facts sidebar: provider, holdings split, min investment,
  volatility (1Y), positive weeks %, best/worst 1M holding, launched, updated.
- Quantity/holdings math uses whole shares only; outlay may exceed the
  minimum target and is stated honestly.
- Chips are multi-colored: each tag gets a stable color from an 8-color
  palette (hash of the tag name). Risk chip keeps semantic color and carries
  the actual volatility number on hover.
- Filter sidebar primary color is GREEN (--faccent): selected chips,
  checkboxes, reset link.
- Card layout: name first with rank inside ("#1 Name"); chip row after name
  with volatility chip first; provider line after chips.

## v4 additions — basket universe diversity

- 20 baskets follow the smallcase/Windmill Capital taxonomy: asset
  allocation, smart beta / quant trackers, factor models, sector trackers,
  group (House of X) trackers, and themes.
- New rule-condition kinds: Tracker (violet) for index/group/sector
  membership, Allocation (teal) for asset-class splits and defensive tilts.
- Every basket carries: a real universe definition, a rule tree, a
  weighting scheme in the Rank row, and at least one liquidity guard.
- Sector trackers weight by free-float market cap with caps; thematic
  baskets weight by their theme metric; asset-allocation baskets state
  their equity/gold split as an Allocation condition with an IF/THEN
  defensive tilt.
