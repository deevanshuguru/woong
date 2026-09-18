# Woong design standard

One standard for every screen. A screen that does not follow it is wrong, not
different.

This file is the source of truth for tokens. The stylesheet
[`woong/web/style.css`](../woong/web/style.css) declares these tokens once and
nothing else declares a colour, a size or a radius. If a value is needed and it
is not here, it gets added here first.

Version one is desktop and light surface only. There is no dark mode, no theme
switch and no mobile layout.

---

## 1. What the standard is for

Woong shows numbers a user will act on with their own money. The interface has
one job: make it obvious what a number is, where it came from and when it was
true. Every rule below serves that.

Three consequences that outrank taste:

1. **A number and its provenance travel together.** No figure appears without a
 reachable source tag and as-of date.
2. **A missing value looks different from a zero and different from a failure.**
 It is never blank and never a dash on its own.
3. **Colour never carries a judgement.** Green and red encode the sign of a
 stored number. They never mean good, bad, buy or sell.

---

## 2. Colour

One accent. Everything else is a neutral ladder. The accent appears on the
primary action, the active state marker and the section indicator square. It
does not appear on links inside running text, on hover fills, on chart strokes
or as decoration.

| Token | Value | Use |
|---|---|---|
| `--voltage` | `#5076ee` | Primary button fill, indicator square, focus ring, active border |
| `--voltage-ink` | `#2f49a8` | Accent text and links on a light surface |
| `--canvas` | `#ffffff` | Page floor |
| `--surface` | `#f4f5f6` | Card and panel fill |
| `--surface-warm` | `#e6e4e2` | Second card fill where two cards sit side by side |
| `--ink` | `#001222` | Primary text, table figures, headings |
| `--ink-soft` | `#5c6874` | Secondary text inside a paragraph |
| `--ink-muted` | `#6c7782` | Labels, column headers, captions |
| `--hairline` | `#d1d5d8` | The only border colour |
| `--up` | `#2f7a0e` | The sign of a positive stored number |
| `--down` | `#c0102f` | The sign of a negative stored number |
| `--refused` | `#8a5a00` | A metric that is switched off, and its stored reason |

`--ink` is a navy-leaning near-black, not pure black. Pure black against white
figures reads harder than it needs to on a screen a user stares at for an hour.

`--up` and `--down` are darkened from the usual bright profit and loss pair so
that a figure carrying the colour still clears a 4.5 to 1 contrast ratio against
white. A number the user must read is text, not decoration, and gets held to the
text standard.

### What each colour is not allowed to do

- `--voltage` never fills a table row, a header band or a chart area.
- `--up` and `--down` never appear on anything except a figure whose sign they
  describe, and never on a name, a row background or a button.
- `--refused` is the only colour allowed to mark a switched-off metric. A
  switched-off metric is never shown in `--down`, because it is not a loss.

---

## 3. Type

One sans family for everything spoken. One monospace family for annotation and
for identifiers.

```
--font-sans: Inter, ui-sans-serif, system-ui, "Helvetica Neue", Arial, sans-serif;
--font-mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
```

Weights sit on a variable axis at 436, 452, 484 and 496, not on the 400, 500,
700 ladder. The values look arbitrary and are the point: they hold a single
optical weight across sizes instead of stepping.

| Token | Size | Weight | Use |
|---|---|---|---|
| `--type-display` | 32px | 484 | Instrument name, page title |
| `--type-figure` | 24px | 484 | A headline figure, for example the last close |
| `--type-heading` | 20px | 496 | Section heading, card title |
| `--type-body` | 15px | 452 | Running text |
| `--type-table` | 13px | 452 | Table cell and form control |
| `--type-eyebrow` | 12px | 500 | Uppercase monospace section label |

### Numbers

Every figure carries `font-variant-numeric: tabular-nums` so a column of numbers
aligns on the digit. Figures are set in the sans family, not the monospace
family. Monospace is reserved for the eyebrow, for a symbol code and for a
source tag, so that a monospace run in the interface always means "this is an
identifier or a label", never "this is a number".

### The eyebrow

Every section on every page opens with an eyebrow: an 8 by 8 pixel `--voltage`
square, then the section name in monospace, 12px, uppercase. The eyebrow is the
only device that establishes hierarchy. A section without one is not part of the
system.

The square is a square. It is not a circle and it does not get a radius,
because a round marker reads as a status light and a status light implies a
verdict.

---

## 4. Shape and space

**One radius.** `--radius: 6px`. Buttons, cards, inputs, chart frames, badges.
There is no second radius and no pill. A full-bleed band and a table rule stay
square.

**One border.** 1px solid `--hairline`. There is no 2px border and no double
rule.

**No shadow.** Depth comes from a `--surface` fill against `--canvas`. A desk
screen with shadows on stacked panels turns into noise at density.

Spacing runs on a 24px base:

| Token | Value |
|---|---|
| `--space-xs` | 6px |
| `--space-sm` | 8px |
| `--space-base` | 12px |
| `--space-md` | 16px |
| `--space-lg` | 24px |
| `--space-xl` | 48px |

There is no tier above 48px. Generous vertical air belongs to a marketing page.
A working desk pays for every pixel of scroll, so the largest gap between two
sections is 48px.

---

## 5. Page templates

Every screen is one of these. A new screen picks a template or the template list
grows first.

### 5.1 Two-pane desk

The scanner. Fixed 24rem operations pane on the left, results on the right, both
scrolling independently, full viewport height with no page scroll. The left pane
is a numbered accordion: the user is always in exactly one step.

### 5.2 Record page

One instrument. Single column, 64rem maximum width, centred. Fixed order:

1. Identity band: name, symbol code, exchange, instrument kind, as-of date.
2. Headline figure and its chart.
3. Metric sections, each opening with an eyebrow.
4. Stored-fact tables.
5. The refusal note: what this page does not show and why.

### 5.3 Result table

Used inside the desk and inside a record page. Left-aligned text columns,
right-aligned figures, monospace symbol code, hairline row rule, no zebra
striping, no vertical rules.

---

## 6. Components

Each of these has exactly one appearance across the product.

- **`button-primary`** `--voltage` fill, white text, `--radius`, 36px high. One
  per screen region. The scanner has exactly one: run the rule.
- **`button-quiet`** transparent fill, `--ink` text, hairline border. Everything
  that is not the one primary action.
- **`button-quiet.active`** hairline border replaced by `--voltage`, fill
  `--surface`. This is how a chosen option states itself. Never a filled pill.
- **`field`** `--canvas` fill, hairline border, `--radius`, 32px high,
  `--type-table`. A focused field gets a 2px `--voltage` outline outside the
  border, never a colour change on the border itself.
- **`eyebrow`** the indicator square plus monospace label from section 3.
- **`card`** `--surface` fill, `--radius`, 24px padding, no border, no shadow.
- **`stat`** a label in `--ink-muted` at `--type-eyebrow` above a figure at
  `--type-figure`. Used for a count and for a headline number.
- **`source-tag`** monospace, 11px, `--ink-muted`, uppercase. Sits with the
  figure it describes and never in a heading.
- **`refusal`** `--refused` text at `--type-body` on `--surface`, with the
  stored reason as the whole content. Never an icon on its own.
- **`chart-frame`** `--surface` fill, `--radius`, the plot inset 12px, a single
  hairline baseline, no gridlines above two, no legend when there is one series.

---

## 7. Charts

Charts are allowed to show a stored series and nothing else. A chart that
implies a future, a target or a level to act on is not a chart Woong draws.

- The browser receives a finished geometry: a list of coordinates already scaled
  in Python. It computes no minimum, no maximum, no scale and no average. This
  is the same rule as every other number.
- Inline scalable vector graphics (SVG) drawn from that geometry. No chart
  library, no canvas, no runtime dependency.
- One series per frame. A second series only when the two are the same unit.
- Stroke is `--ink` at 1.5px for a price line. `--up` and `--down` are allowed
  only on a bar whose sign they describe, for example a monthly seasonality bar.
- The axis states the first and last date and the low and high of the window,
  as figures. No floating tooltip: a value the user cannot read without hovering
  is a value the page failed to present.
- A window with fewer sessions than asked for says how many it had. It never
  stretches what it has across the full width and pretends.

---

## 8. Refusals this standard makes

- No icon carries meaning on its own. Every state is stated in words.
- No animation. Nothing fades, slides or counts up. A number that moves while
  the user reads it is a number they cannot trust.
- No tooltip holds a fact that is not also on the page.
- No empty state that says "nothing found". It says which stage removed
  everything and how many the stage started with.
- No spinner that hides how long a run took. The run reports its own duration.
- No colour-only distinction anywhere, so the interface still works for a user
  who cannot separate red from green.
