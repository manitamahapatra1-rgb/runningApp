"""
Jack Daniels' VDOT calculator and training-pace derivation.

Implements the Daniels-Gilbert oxygen-cost model from *Daniels' Running Formula*
(Human Kinetics). VDOT is the steady-state oxygen demand (ml/kg/min) of a race
divided by the fraction of VO2max sustainable for that duration. Training paces
are derived by inverting the cost equation at zone-specific intensity fractions,
except Marathon (M) pace, which equals the VDOT-predicted marathon race pace.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Union

# --- Daniels-Gilbert oxygen-cost coefficients (velocity in m/min) ---
_VO2_INTERCEPT = -4.60
_VO2_LINEAR = 0.182258
_VO2_QUAD = 0.000104

# Fraction of VO2max sustainable for a given duration (T in minutes).
_PCT_VO2MAX_A = 0.8
_PCT_VO2MAX_B = 0.1894393
_PCT_VO2MAX_C = -0.012778
_PCT_VO2MAX_D = 0.2989558
_PCT_VO2MAX_E = -0.1932605

# Training-zone intensity as a fraction of VDOT (3rd-edition Daniels bands).
_EASY_SLOW = 0.59   # slow end of Easy (E)
_EASY_FAST = 0.74   # fast end of Easy (E)
_THRESHOLD = 0.88   # Threshold (T)
_INTERVAL = 0.98   # Interval (I)
_REPETITION = 1.10  # Repetition (R), mid-range of 105–115%

_METERS_PER_KM = 1_000.0
_METERS_PER_MILE = 1_609.344


class RaceDistance(Enum):
    """Standard race distances in meters."""

    FIVE_K = 5_000.0
    TEN_K = 10_000.0
    HALF_MARATHON = 21_097.5
    MARATHON = 42_195.0


@dataclass(frozen=True)
class Pace:
    """Pace expressed as seconds per kilometer and per mile."""

    seconds_per_km: float
    seconds_per_mile: float

    def format_km(self) -> str:
        return _format_pace(self.seconds_per_km)

    def format_mile(self) -> str:
        return _format_pace(self.seconds_per_mile)


@dataclass(frozen=True)
class EasyPace:
    """Easy (E) pace is a range in Daniels' system (59–74% of VDOT)."""

    slow: Pace
    fast: Pace


@dataclass(frozen=True)
class TrainingPaces:
    """Daniels training zones: E, M, T, I, R."""

    easy: EasyPace
    marathon: Pace
    threshold: Pace
    interval: Pace
    repetition: Pace


@dataclass(frozen=True)
class VdotResult:
    """VDOT score and derived training paces."""

    vdot: float
    paces: TrainingPaces


def _vo2_demand(velocity_m_per_min: float) -> float:
    """Oxygen cost (ml/kg/min) at a given running velocity."""
    v = velocity_m_per_min
    return _VO2_INTERCEPT + _VO2_LINEAR * v + _VO2_QUAD * v * v


def _fraction_vo2max(time_minutes: float) -> float:
    """Fraction of VO2max a runner can sustain for *time_minutes*."""
    t = time_minutes
    return (
        _PCT_VO2MAX_A
        + _PCT_VO2MAX_B * math.exp(_PCT_VO2MAX_C * t)
        + _PCT_VO2MAX_D * math.exp(_PCT_VO2MAX_E * t)
    )


def _velocity_from_vo2(vo2: float) -> float:
    """
    Invert the Daniels cost equation for velocity (m/min).

    0.000104·v² + 0.182258·v − (4.60 + VO2) = 0  →  positive root via quadratic formula.
    """
    a = _VO2_QUAD
    b = _VO2_LINEAR
    c = _VO2_INTERCEPT - vo2
    discriminant = b * b - 4.0 * a * c
    if discriminant < 0:
        raise ValueError(f"Cannot solve for velocity at VO2={vo2:.2f}")
    return (-b + math.sqrt(discriminant)) / (2.0 * a)


def _pace_from_velocity(velocity_m_per_min: float) -> Pace:
    """Convert velocity (m/min) to seconds per km and per mile."""
    if velocity_m_per_min <= 0:
        raise ValueError("Velocity must be positive")
    return Pace(
        seconds_per_km=_METERS_PER_KM / velocity_m_per_min * 60.0,
        seconds_per_mile=_METERS_PER_MILE / velocity_m_per_min * 60.0,
    )


def _format_pace(seconds: float) -> str:
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes}:{secs:02d}"


def parse_race_time(
    hours: int = 0,
    minutes: int = 0,
    seconds: float = 0.0,
) -> float:
    """
    Convert clock components to total race time in seconds.

    Examples:
        parse_race_time(minutes=18, seconds=30)  -> 1110.0
        parse_race_time(hours=1, minutes=30)     -> 5400.0
    """
    if hours < 0 or minutes < 0 or seconds < 0:
        raise ValueError("Race time components must be non-negative")
    return hours * 3600 + minutes * 60 + seconds


def _resolve_distance(distance: Union[RaceDistance, str, float]) -> float:
    """Accept RaceDistance, alias string ('5k', 'half_marathon', …), or meters."""
    if isinstance(distance, RaceDistance):
        return distance.value
    if isinstance(distance, (int, float)):
        if distance <= 0:
            raise ValueError("Distance in meters must be positive")
        return float(distance)

    key = distance.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "5k": RaceDistance.FIVE_K,
        "5_k": RaceDistance.FIVE_K,
        "10k": RaceDistance.TEN_K,
        "10_k": RaceDistance.TEN_K,
        "half": RaceDistance.HALF_MARATHON,
        "half_marathon": RaceDistance.HALF_MARATHON,
        "hm": RaceDistance.HALF_MARATHON,
        "marathon": RaceDistance.MARATHON,
        "full": RaceDistance.MARATHON,
        "full_marathon": RaceDistance.MARATHON,
    }
    if key not in aliases:
        raise ValueError(
            f"Unknown distance {distance!r}. Use RaceDistance, meters, or one of: "
            f"{', '.join(sorted(aliases))}"
        )
    return aliases[key].value


def calculate_vdot(distance_meters: float, time_seconds: float) -> float:
    """
    Compute VDOT from a race result using the Daniels-Gilbert formula.

    VDOT = VO2_demand(velocity) / fraction_VO2max(duration)

    Parameters
    ----------
    distance_meters:
        Race distance in meters.
    time_seconds:
        Finish time in seconds.

    Returns
    -------
    float
        VDOT score (effective VO2max from race performance).
    """
    if distance_meters <= 0 or time_seconds <= 0:
        raise ValueError("Distance and time must be positive")

    time_minutes = time_seconds / 60.0
    velocity = distance_meters / time_minutes
    vo2 = _vo2_demand(velocity)
    fraction = _fraction_vo2max(time_minutes)
    return vo2 / fraction


def _predict_race_time_seconds(distance_meters: float, target_vdot: float) -> float:
    """
    Predict finish time at *distance_meters* for a given VDOT.

    Binary-search the duration whose implied VDOT matches *target_vdot*.
    VDOT decreases as finish time increases (slower pace), so we move
    *lo* upward when VDOT is too high and *hi* downward when too low.
    """
    lo, hi = 1.0, 24.0 * 3600.0  # 1 s to 24 h
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if calculate_vdot(distance_meters, mid) > target_vdot:
            lo = mid  # too fast — need a longer (slower) time
        else:
            hi = mid  # too slow — need a shorter (faster) time
    return (lo + hi) / 2.0


def _pace_at_vdot_fraction(vdot: float, fraction: float) -> Pace:
    """Pace when running at *fraction* × VDOT oxygen demand."""
    velocity = _velocity_from_vo2(vdot * fraction)
    return _pace_from_velocity(velocity)


def derive_training_paces(vdot: float) -> TrainingPaces:
    """
    Derive Daniels E/M/T/I/R training paces from a VDOT score.

    Easy (E) is returned as a slow–fast range (59–74% of VDOT).
    Marathon (M) is the VDOT-predicted marathon race pace.
    Threshold (T), Interval (I), and Repetition (R) use the standard
    intensity fractions published in Daniels' Running Formula.
    """
    if vdot <= 0:
        raise ValueError("VDOT must be positive")

    marathon_time_s = _predict_race_time_seconds(RaceDistance.MARATHON.value, vdot)
    marathon_velocity = RaceDistance.MARATHON.value / (marathon_time_s / 60.0)

    return TrainingPaces(
        easy=EasyPace(
            slow=_pace_at_vdot_fraction(vdot, _EASY_SLOW),
            fast=_pace_at_vdot_fraction(vdot, _EASY_FAST),
        ),
        marathon=_pace_from_velocity(marathon_velocity),
        threshold=_pace_at_vdot_fraction(vdot, _THRESHOLD),
        interval=_pace_at_vdot_fraction(vdot, _INTERVAL),
        repetition=_pace_at_vdot_fraction(vdot, _REPETITION),
    )


def daniels_vdot(
    race_time_seconds: float,
    distance: Union[RaceDistance, str, float],
) -> VdotResult:
    """
    Calculate VDOT and Daniels training paces from a race performance.

    Implements Jack Daniels' VDOT formula (Daniels & Gilbert, 1979; published in
    *Daniels' Running Formula*, Human Kinetics). Training paces follow the
    five-zone E/M/T/I/R system from the same methodology.

    Parameters
    ----------
    race_time_seconds:
        Finish time in seconds (use :func:`parse_race_time` for convenience).
    distance:
        ``RaceDistance`` enum member, alias string (``'5k'``, ``'marathon'``, …),
        or distance in meters.

    Returns
    -------
    VdotResult
        VDOT score and training paces (seconds per km and per mile).
    """
    distance_m = _resolve_distance(distance)
    vdot = calculate_vdot(distance_m, race_time_seconds)
    paces = derive_training_paces(vdot)
    return VdotResult(vdot=vdot, paces=paces)


if __name__ == "__main__":
    # Known benchmark: 18:30 5K → VDOT ~54–55, paces should align with Daniels tables.
    time_s = parse_race_time(minutes=18, seconds=30)
    result = daniels_vdot(time_s, RaceDistance.FIVE_K)

    print(f"Race: 5K in { _format_pace(time_s) }")
    print(f"VDOT: {result.vdot:.1f}\n")
    print("Training paces (Daniels E/M/T/I/R):\n")

    p = result.paces
    print(
        f"  Easy (E):       {p.easy.slow.format_km()}/km  –  {p.easy.fast.format_km()}/km"
        f"    ({p.easy.slow.format_mile()}/mi  –  {p.easy.fast.format_mile()}/mi)"
    )
    print(
        f"  Marathon (M):   {p.marathon.format_km()}/km"
        f"    ({p.marathon.format_mile()}/mi)"
    )
    print(
        f"  Threshold (T):  {p.threshold.format_km()}/km"
        f"    ({p.threshold.format_mile()}/mi)"
    )
    print(
        f"  Interval (I):   {p.interval.format_km()}/km"
        f"    ({p.interval.format_mile()}/mi)"
    )
    print(
        f"  Repetition (R): {p.repetition.format_km()}/km"
        f"    ({p.repetition.format_mile()}/mi)"
    )
