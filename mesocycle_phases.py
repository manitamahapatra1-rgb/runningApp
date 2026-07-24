"""
Training mesocycle phase planner (Base → Build → Peak → Taper).

Splits a goal-race countdown into four classical periodization blocks. Proportions
and taper lengths follow patterns common in Jack Daniels' phase plans and
Pete Pfitzinger's distance-specific schedules (*Advanced Marathoning*, 2nd ed.;
*Faster Road Racing*): longer races get more base mileage and a longer taper,
while 5K/10K plans shift earlier toward quality (Build/Peak) and use shorter
tapers because neuromuscular freshness matters more than glycogen supercompensation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Union

PhaseName = str  # "Base" | "Build" | "Peak" | "Taper"


class GoalDistance(Enum):
    """Supported goal race distances."""

    FIVE_K = "5k"
    TEN_K = "10k"
    HALF_MARATHON = "half_marathon"
    MARATHON = "marathon"


@dataclass(frozen=True)
class DistancePhaseConfig:
    """Phase parameters for one goal distance."""

    taper_weeks: int
    min_base_weeks: int
    base_ratio: float
    build_ratio: float
    peak_ratio: float


# Non-taper week ratios (must sum to 1.0) and fixed taper lengths per distance.
_DISTANCE_CONFIG: dict[GoalDistance, DistancePhaseConfig] = {
    GoalDistance.FIVE_K: DistancePhaseConfig(
        taper_weeks=1,
        min_base_weeks=2,
        base_ratio=0.35,
        build_ratio=0.40,
        peak_ratio=0.25,
    ),
    GoalDistance.TEN_K: DistancePhaseConfig(
        taper_weeks=1,
        min_base_weeks=3,
        base_ratio=0.40,
        build_ratio=0.35,
        peak_ratio=0.25,
    ),
    GoalDistance.HALF_MARATHON: DistancePhaseConfig(
        taper_weeks=2,
        min_base_weeks=3,
        base_ratio=0.45,
        build_ratio=0.35,
        peak_ratio=0.20,
    ),
    GoalDistance.MARATHON: DistancePhaseConfig(
        taper_weeks=3,
        min_base_weeks=4,
        base_ratio=0.50,
        build_ratio=0.30,
        peak_ratio=0.20,
    ),
}


@dataclass(frozen=True)
class WeekAssignment:
    """One week of the plan mapped to a mesocycle phase."""

    week: int
    phase: PhaseName


@dataclass(frozen=True)
class MesocyclePlan:
    """
    Full week-by-week phase assignment.

    ``note`` is set when the input window is too short for ideal proportions;
    Build and/or Peak may be shortened or omitted while Base and Taper are
    preserved as far as possible.
    """

    weeks: tuple[WeekAssignment, ...]
    note: str | None = None


def _resolve_distance(distance: Union[GoalDistance, str]) -> GoalDistance:
    if isinstance(distance, GoalDistance):
        return distance

    key = distance.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "5k": GoalDistance.FIVE_K,
        "5_k": GoalDistance.FIVE_K,
        "10k": GoalDistance.TEN_K,
        "10_k": GoalDistance.TEN_K,
        "half": GoalDistance.HALF_MARATHON,
        "half_marathon": GoalDistance.HALF_MARATHON,
        "hm": GoalDistance.HALF_MARATHON,
        "marathon": GoalDistance.MARATHON,
        "full": GoalDistance.MARATHON,
        "full_marathon": GoalDistance.MARATHON,
    }
    if key not in aliases:
        raise ValueError(
            f"Unknown distance {distance!r}. Use GoalDistance or one of: "
            f"{', '.join(sorted(aliases))}"
        )
    return aliases[key]


def _split_training_weeks(
    training_weeks: int,
    config: DistancePhaseConfig,
) -> tuple[int, int, int]:
    """
    Allocate pre-taper weeks across Base, Build, and Peak.

    When weeks are tight, Base is protected first (at least ``min_base_weeks``
    when possible), then remaining weeks go to Build before Peak. Peak is dropped
    before Build when space runs out — an underdeveloped speed block is safer
    than skipping aerobic foundation.
    """
    if training_weeks <= 0:
        return 0, 0, 0

    # Target proportions, but never allocate less base than the distance minimum.
    base = max(config.min_base_weeks, round(training_weeks * config.base_ratio))
    base = min(base, training_weeks)

    remaining = training_weeks - base
    if remaining == 0:
        return base, 0, 0
    if remaining == 1:
        return base, 1, 0

    middle_total = config.build_ratio + config.peak_ratio
    build = round(remaining * config.build_ratio / middle_total)
    build = max(1, min(build, remaining))
    peak = remaining - build

    # Prefer at least one Peak week when three or more middle weeks exist.
    if peak == 0 and remaining >= 2:
        build -= 1
        peak = 1

    return base, build, peak


def assign_training_phases(
    total_weeks: int,
    goal_distance: Union[GoalDistance, str],
) -> MesocyclePlan:
    """
    Split *total_weeks* into Base, Build, Peak, and Taper mesocycle phases.

    Weeks are numbered 1 … *total_weeks*; the final ``taper_weeks`` (distance-
    dependent) are always Taper. Phase proportions for the pre-taper block
    follow Daniels-/Pfitzinger-style periodization: ~35–50 % Base (aerobic
    foundation), ~30–40 % Build (introduce quality), ~20–25 % Peak (race-
    specific intensity), with marathon plans weighted most toward Base and
    given the longest taper (3 weeks vs. 1 week for 5K/10K).

    Short-window handling
    ---------------------
    If the calendar is too short for all four phases at target proportions,
    **Taper length and Base are preserved first**; Build and Peak are compressed
    or dropped. Skipping taper risks arriving at the start line fatigued; skipping
    Base leaves insufficient aerobic support for hard sessions. A truncated Build/
    Peak block is the least risky compromise — documented in ``MesocyclePlan.note``
    when it occurs.

    Parameters
    ----------
    total_weeks:
        Integer number of weeks until the goal race (week *total_weeks* is Taper
        week / race week).
    goal_distance:
        ``GoalDistance`` member or alias string (``"5k"``, ``"marathon"``, …).

    Returns
    -------
    MesocyclePlan
        Ordered week-by-week assignments plus an optional note on tradeoffs.
    """
    if total_weeks < 1:
        raise ValueError("total_weeks must be at least 1")

    config = _DISTANCE_CONFIG[_resolve_distance(goal_distance)]
    notes: list[str] = []

    # Reserve taper at the end. Keep at least one pre-taper week when possible.
    taper = config.taper_weeks
    if total_weeks <= taper:
        taper = max(1, total_weeks - 1)
        notes.append(
            f"Taper shortened to {taper} week(s) to retain at least one "
            "pre-taper training week."
        )

    training_weeks = total_weeks - taper
    base, build, peak = _split_training_weeks(training_weeks, config)

    if build == 0 and peak == 0 and training_weeks > 0:
        notes.append(
            "Build and Peak phases omitted — not enough weeks after reserving "
            "Base and Taper. Aerobic foundation and pre-race recovery take "
            "priority over race-specific sharpening."
        )
    elif peak == 0 and build > 0:
        notes.append(
            "Peak phase omitted; remaining weeks assigned to Build only."
        )
    elif base < config.min_base_weeks:
        notes.append(
            f"Base phase is {base} week(s), below the {config.min_base_weeks}-week "
            "target for this distance — calendar too short for an ideal build."
        )

    assignments: list[WeekAssignment] = []
    week = 1
    for count, phase in (
        (base, "Base"),
        (build, "Build"),
        (peak, "Peak"),
        (taper, "Taper"),
    ):
        for _ in range(count):
            assignments.append(WeekAssignment(week=week, phase=phase))
            week += 1

    return MesocyclePlan(
        weeks=tuple(assignments),
        note=" ".join(notes) if notes else None,
    )


def _print_plan(label: str, plan: MesocyclePlan) -> None:
    print(label)
    if plan.note:
        print(f"  Note: {plan.note}")
    for assignment in plan.weeks:
        print(f"  Week {assignment.week:2d} → {assignment.phase}")
    print()


if __name__ == "__main__":
    marathon_16 = assign_training_phases(16, GoalDistance.MARATHON)
    _print_plan("16-week marathon build:", marathon_16)

    five_k_8 = assign_training_phases(8, "5k")
    _print_plan("8-week 5K build (short window):", five_k_8)
