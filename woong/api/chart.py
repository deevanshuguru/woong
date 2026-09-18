"""Turn a stored series into finished chart geometry.

The browser receives coordinates and labels. It computes no minimum, no maximum,
no scale and no average, for the same reason it computes no metric.

Refuses to draw a line through a gap: a session with no stored close ends the
window rather than being bridged. Refuses to stretch a short window across the
full width and call it the window that was asked for. Refuses to extend a series
past its last stored session.
"""

from __future__ import annotations

from dataclasses import dataclass

WIDTH = 720
HEIGHT = 180
PAD = 8

# Window lengths are stated in sessions, not months, because a session is what
# the warehouse stores. Naming them "one month" would be a claim about the
# calendar that the row count cannot support.
LINE_WINDOWS: tuple[tuple[str, int], ...] = (
    ("21 sessions", 21),
    ("63 sessions", 63),
    ("252 sessions", 252),
    ("1260 sessions", 1260),
    ("All stored sessions", 0),
)


@dataclass(frozen=True)
class Point:
    date: str
    value: float


def _scale(values: list[float], height: int, pad: int) -> tuple[float, float, float]:
    low = min(values)
    high = max(values)
    span = high - low
    if span == 0:
        # A flat window is drawn flat down the middle. Spreading it to fill the
        # frame would invent movement that is not in the data.
        return low, high, 0.0
    return low, high, (height - 2 * pad) / span


def line_geometry(
    points: list[Point],
    width: int = WIDTH,
    height: int = HEIGHT,
    pad: int = PAD,
) -> dict:
    """Scale a series into a polyline. Raises when there is nothing to draw."""
    if len(points) < 2:
        raise ValueError("A line needs at least two stored sessions.")
    values = [point.value for point in points]
    low, high, factor = _scale(values, height, pad)
    step = (width - 2 * pad) / (len(points) - 1)
    coords: list[str] = []
    for index, value in enumerate(values):
        x = pad + step * index
        y = height / 2 if factor == 0.0 else pad + (high - value) * factor
        coords.append(f"{x:.2f},{y:.2f}")
    low_index = values.index(low)
    high_index = values.index(high)
    return {
        "width": width,
        "height": height,
        "points": " ".join(coords),
        "session_count": len(points),
        "first_date": points[0].date,
        "last_date": points[-1].date,
        "first_value": values[0],
        "last_value": values[-1],
        "low": low,
        "high": high,
        "low_date": points[low_index].date,
        "high_date": points[high_index].date,
        "flat": factor == 0.0,
    }


def line_windows(
    points: list[Point],
    windows: tuple[tuple[str, int], ...] = LINE_WINDOWS,
) -> list[dict]:
    """Build one geometry per window that has enough stored sessions.

    A window shorter than it asked for is reported with the count it actually
    had, under its own label. A window with fewer than two sessions is dropped.
    """
    built: list[dict] = []
    seen: set[int] = set()
    for label, length in windows:
        tail = points if length == 0 else points[-length:]
        if len(tail) < 2 or len(tail) in seen:
            continue
        seen.add(len(tail))
        geometry = line_geometry(tail)
        short = length != 0 and len(tail) < length
        # A window that ran out of history is the whole series. Keeping the asked
        # for label on it would put "1260 sessions" over 777 of them.
        geometry["label"] = "All stored sessions" if short and len(tail) == len(points) else label
        geometry["short"] = short
        geometry["asked_for"] = length
        built.append(geometry)
    if not built:
        raise ValueError("No window has two stored sessions.")
    return built


def bar_geometry(
    labels: list[str],
    values: list[float | None],
    width: int = WIDTH,
    height: int = HEIGHT,
    pad: int = PAD,
) -> dict:
    """Scale signed values into bars around a zero line.

    A slot with no stored value gets no bar. It is returned with `missing` set so
    the page can say it had no value instead of drawing it as zero.
    """
    if len(labels) != len(values):
        raise ValueError("Every bar needs a label.")
    present = [value for value in values if value is not None]
    if not present:
        raise ValueError("No stored value to draw.")
    low = min(min(present), 0.0)
    high = max(max(present), 0.0)
    span = high - low
    usable = height - 2 * pad
    factor = 0.0 if span == 0 else usable / span
    zero_y = pad + usable if factor == 0.0 else pad + high * factor
    slot = (width - 2 * pad) / len(labels)
    bar_width = slot * 0.62
    bars: list[dict] = []
    for index, (label, value) in enumerate(zip(labels, values)):
        x = pad + slot * index + (slot - bar_width) / 2
        if value is None:
            bars.append({"label": label, "missing": True, "x": round(x, 2), "width": round(bar_width, 2)})
            continue
        length = abs(value) * factor
        y = zero_y - length if value >= 0 else zero_y
        bars.append(
            {
                "label": label,
                "missing": False,
                "value": value,
                "sign": "up" if value >= 0 else "down",
                "x": round(x, 2),
                "y": round(y, 2),
                "width": round(bar_width, 2),
                "height": round(max(length, 1.0), 2),
            }
        )
    return {
        "width": width,
        "height": height,
        "zero_y": round(zero_y, 2),
        "low": low,
        "high": high,
        "bars": bars,
        "missing_count": sum(1 for value in values if value is None),
    }
