"""
Full weekly training-plan assembly from phases, mileage, and VDOT paces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from vdot_paces import RaceDistance, TrainingPaces, daniels_vdot, parse_race_time
from mesocycle_phases import GoalDistance, WeekAssignment, assign_training_phases
from weekly_mileage_progression import WeekMileage, generate_weekly_mileage_progression

_DAY_ORDER = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_RUN_DAY_PATTERNS: dict[int, tuple[str, ...]] = {
    3: ("Tuesday", "Thursday", "Sunday"),
    4: ("Tuesday", "Thursday", "Saturday", "Sunday"),
    5: ("Monday", "Tuesday", "Thursday", "Saturday", "Sunday"),
    6: ("Monday", "Tuesday", "Wednesday", "Thursday", "Saturday", "Sunday"),
    7: _DAY_ORDER,
}
_QUALITY_ROTATION = ("Tempo", "Fartlek", "Mile Reps")


@dataclass(frozen=True)
class DayWorkout:
    day: str
    workout_type: str
    distance_miles: float
    pace: str


@dataclass(frozen=True)
class PlannedWeek:
    week: int
    phase: str
    total_mileage: float
    long_run_mileage: float
    workouts: tuple[DayWorkout, ...]


def _easy_pace_label(paces: TrainingPaces) -> str:
    return f"Easy {paces.easy.slow.format_mile()}-{paces.easy.fast.format_mile()}/mi"


def _marathon_pace_label(paces: TrainingPaces) -> str:
    return f"Marathon {paces.marathon.format_mile()}/mi"


def _tempo_pace_label(paces: TrainingPaces) -> str:
    return f"Threshold {paces.threshold.format_mile()}/mi"


def _fartlek_pace_label(paces: TrainingPaces) -> str:
    return (
        f"Surges {paces.threshold.format_mile()} to {paces.interval.format_mile()}/mi, "
        f"recover at easy pace"
    )


def _mile_reps_pace_label(paces: TrainingPaces) -> str:
    return f"Reps {paces.interval.format_mile()}-{paces.repetition.format_mile()}/mi"


def _quality_sessions_for_phase(phase: str) -> int:
    if phase == "Base":
        return 1
    if phase in {"Build", "Peak"}:
        return 2
    if phase == "Taper":
        return 1  # Keep a touch of quality for sharpness while reducing load.
    raise ValueError(f"Unsupported phase {phase!r}")


def _quality_distance_factor(phase: str) -> float:
    if phase == "Base":
        return 0.18
    if phase == "Build":
        return 0.14
    if phase == "Peak":
        return 0.13
    if phase == "Taper":
        return 0.10  # Reduced intensity volume in taper, but not zero.
    raise ValueError(f"Unsupported phase {phase!r}")


def _split_distance(total_distance: float, parts: int) -> list[float]:
    if parts < 1:
        return []
    if parts == 1:
        return [round(total_distance, 2)]

    base = round(total_distance / parts, 2)
    split = [base] * parts
    used = round(base * (parts - 1), 2)
    split[-1] = round(max(0.0, total_distance - used), 2)
    return split


def _taper_reduction_fraction(taper_index: int, taper_count: int) -> float:
    """
    Return taper-week reduction fraction relative to peak mileage.

    First taper week starts around 20% down; final taper week approaches 35-40%
    down, with linear progression between them when taper has >2 weeks.
    """
    if taper_count <= 0:
        return 0.0
    if taper_count == 1:
        return 0.35

    start, end = 0.20, 0.38
    progress = taper_index / (taper_count - 1)
    return start + (end - start) * progress


def assemble_training_plan(
    phase_weeks: Sequence[WeekAssignment],
    mileage_weeks: Sequence[WeekMileage],
    training_paces: TrainingPaces,
    run_days_per_week: int = 5,
) -> list[PlannedWeek]:
    """
    Assemble a full day-by-day plan from mesocycle phases, mileage, and paces.

    Design choices
    --------------
    - Long run is always on Sunday.
    - Peak/Taper long-run pace rule is explicit and consistent:
      - Peak weeks: Marathon pace (race-specific endurance stimulus).
      - Taper weeks except final taper week: Marathon pace.
      - Final taper week (race week): Easy pace to prioritize freshness.
    - Taper weekly volume is reduced inside this assembler relative to peak-week
      mileage: roughly 20% down at taper start, progressing toward ~38% down in
      the final taper week.
    - Taper keeps one quality session per week, but with lower quality distance
      factor than other phases. This preserves neuromuscular sharpness while
      reducing fatigue before race day.
    - Primary quality workout rotates Tempo -> Fartlek -> Mile Reps weekly and
      never repeats in consecutive weeks; a second quality day (Build/Peak only)
      uses the next workout type in rotation.
    """
    if len(phase_weeks) != len(mileage_weeks):
        raise ValueError("phase_weeks and mileage_weeks must have the same length")
    if run_days_per_week not in _RUN_DAY_PATTERNS:
        raise ValueError("run_days_per_week must be one of 3, 4, 5, 6, or 7")

    run_days = _RUN_DAY_PATTERNS[run_days_per_week]
    easy_label = _easy_pace_label(training_paces)
    plan: list[PlannedWeek] = []
    rotation_index = 0
    peak_reference_mileage = max((week.total_mileage for week in mileage_weeks if week.total_mileage > 0), default=0.0)
    taper_count = sum(1 for phase_week in phase_weeks if phase_week.phase == "Taper")
    taper_seen = 0

    for index, (phase_week, mileage_week) in enumerate(zip(phase_weeks, mileage_weeks), start=1):
        if phase_week.week != mileage_week.week:
            raise ValueError(
                f"Week mismatch: phase week {phase_week.week} vs mileage week {mileage_week.week}"
            )

        phase = phase_week.phase
        if phase == "Taper":
            reduction = _taper_reduction_fraction(taper_seen, taper_count)
            total_mileage = round(peak_reference_mileage * (1.0 - reduction), 2)
            taper_seen += 1
        else:
            total_mileage = mileage_week.total_mileage
        long_run_mileage = round(min(mileage_week.long_run_mileage, total_mileage * 0.30), 2)

        quality_count = _quality_sessions_for_phase(phase)
        non_long_run_days = [day for day in run_days if day != "Sunday"]
        if quality_count > len(non_long_run_days):
            raise ValueError("Not enough non-long-run days for quality sessions")

        quality_days = non_long_run_days[:quality_count]
        quality_types: list[str] = []
        for _ in range(quality_count):
            quality_types.append(_QUALITY_ROTATION[rotation_index % len(_QUALITY_ROTATION)])
            rotation_index += 1

        easy_days = [day for day in run_days if day not in {"Sunday", *quality_days}]

        # Rule 2 target total quality mileage (per phase).
        quality_total_target = total_mileage * _quality_distance_factor(phase)

        # Rule 3 allocation with cap guarantees:
        # - every quality/easy run <= 80% of long run
        # - try bounded long-run increase (to ~35%) first
        # - if still infeasible, overflow is absorbed by long run
        long_run_mileage, quality_distances, easy_distances = _allocate_capped_week_distances(
            total_mileage=total_mileage,
            initial_long_run_mileage=long_run_mileage,
            quality_total_target=quality_total_target,
            quality_count=quality_count,
            easy_day_count=len(easy_days),
            per_non_long_cap_ratio=0.80,
            bounded_long_run_ratio=0.35,
        )

        workouts_by_day: dict[str, DayWorkout] = {}

        # Rule 1: Long run on a weekend day, with phase-aware pace choice.
        if phase == "Peak":
            long_run_pace = _marathon_pace_label(training_paces)
        elif phase == "Taper" and taper_seen < taper_count:
            long_run_pace = _marathon_pace_label(training_paces)
        else:
            long_run_pace = easy_label
        workouts_by_day["Sunday"] = DayWorkout(
            day="Sunday",
            workout_type="Long Run",
            distance_miles=round(long_run_mileage, 2),
            pace=long_run_pace,
        )

        # Rule 2: Quality workout frequency by phase, rotating workout types.
        for quality_day, quality_type, quality_distance in zip(quality_days, quality_types, quality_distances):
            if quality_type == "Tempo":
                pace = _tempo_pace_label(training_paces)
            elif quality_type == "Fartlek":
                pace = _fartlek_pace_label(training_paces)
            else:
                pace = _mile_reps_pace_label(training_paces)
            workouts_by_day[quality_day] = DayWorkout(
                day=quality_day,
                workout_type=quality_type,
                distance_miles=quality_distance,
                pace=pace,
            )

        # Rule 3: Fill remaining run days with Easy mileage from remaining volume.
        for easy_day, easy_distance in zip(easy_days, easy_distances):
            workouts_by_day[easy_day] = DayWorkout(
                day=easy_day,
                workout_type="Easy Run",
                distance_miles=easy_distance,
                pace=easy_label,
            )

        ordered_workouts = tuple(workouts_by_day[day] for day in _DAY_ORDER if day in workouts_by_day)

        # Guarantee check (easy to test from __main__): long run is always >= every other single run in the week.
        max_non_long = max(
            (workout.distance_miles for workout in ordered_workouts if workout.workout_type != "Long Run"),
            default=0.0,
        )
        if long_run_mileage + 1e-9 < max_non_long:
            raise ValueError(
                "Invariant violation: long run is always >= every other single run in the week."
            )

        plan.append(
            PlannedWeek(
                week=index,
                phase=phase,
                total_mileage=total_mileage,
                long_run_mileage=long_run_mileage,
                workouts=ordered_workouts,
            )
        )

    return plan


if __name__ == "__main__":
    total_weeks = 12
    run_days = 5

    race_time = parse_race_time(minutes=22, seconds=0)
    vdot_result = daniels_vdot(race_time, RaceDistance.FIVE_K)

    phase_plan = assign_training_phases(total_weeks=total_weeks, goal_distance=GoalDistance.HALF_MARATHON)
    mileage_plan = generate_weekly_mileage_progression(
        starting_weekly_mileage=20,
        weekly_mileage_cap=42,
        total_weeks=total_weeks,
        scheduled_runs_per_week=run_days,
    )

    full_plan = assemble_training_plan(
        phase_weeks=phase_plan.weeks,
        mileage_weeks=mileage_plan,
        training_paces=vdot_result.paces,
        run_days_per_week=run_days,
    )

    print("12-week half-marathon example schedule")
    if phase_plan.note:
        print(f"Note: {phase_plan.note}")
    print()

    for week in full_plan:
        print(
            f"Week {week.week:2d} ({week.phase}) - Total {week.total_mileage:.2f} mi | "
            f"Long Run {week.long_run_mileage:.2f} mi"
        )
        for workout in week.workouts:
            print(
                f"  {workout.day:9s} | {workout.workout_type:10s} | "
                f"{workout.distance_miles:5.2f} mi | {workout.pace}"
            )
        print()


def _allocate_capped_week_distances(
    *,
    total_mileage: float,
    initial_long_run_mileage: float,
    quality_total_target: float,
    quality_count: int,
    easy_day_count: int,
    per_non_long_cap_ratio: float = 0.80,
    bounded_long_run_ratio: float = 0.35,
) -> tuple[float, list[float], list[float]]:
    """
    Allocate long/quality/easy distances with caps:
    - Each quality/easy run <= per_non_long_cap_ratio * long_run_mileage.
    - Prefer increasing long run only up to bounded_long_run_ratio * total_mileage to make
      easy-day even split feasible under cap.
    - If still infeasible, cap easy days and push true overflow onto long run.
    """
    long_run_mileage = round(initial_long_run_mileage, 2)
    max_bounded_long_run = round(total_mileage * bounded_long_run_ratio, 2)
    quality_targets = _split_distance(quality_total_target, quality_count)

    def evaluate(candidate_long_run: float) -> tuple[list[float], list[float], bool, float]:
        cap = candidate_long_run * per_non_long_cap_ratio
        capped_quality = [round(min(distance, cap), 2) for distance in quality_targets]

        remaining_mileage = max(0.0, round(total_mileage - candidate_long_run - sum(capped_quality), 2))
        evenly_split_easy = _split_distance(remaining_mileage, easy_day_count)

        easy_within_cap = all(distance <= cap + 1e-9 for distance in evenly_split_easy)
        if easy_within_cap:
            return capped_quality, evenly_split_easy, True, 0.0

        capped_easy = [round(cap, 2) for _ in range(easy_day_count)]
        overflow = max(0.0, round(remaining_mileage - sum(capped_easy), 2))
        return capped_quality, capped_easy, False, overflow

    quality_distances, easy_distances, easy_feasible, overflow_to_long = evaluate(long_run_mileage)

    if not easy_feasible and easy_day_count > 0 and long_run_mileage < max_bounded_long_run:
        start_cents = int(round(long_run_mileage * 100))
        max_cents = int(round(max_bounded_long_run * 100))

        found_feasible = False
        for cents in range(start_cents, max_cents + 1):
            candidate_long = round(cents / 100.0, 2)
            candidate_quality, candidate_easy, candidate_feasible, candidate_overflow = evaluate(candidate_long)
            if candidate_feasible:
                long_run_mileage = candidate_long
                quality_distances = candidate_quality
                easy_distances = candidate_easy
                overflow_to_long = candidate_overflow
                found_feasible = True
                break

        if not found_feasible:
            long_run_mileage = max_bounded_long_run
            quality_distances, easy_distances, _, overflow_to_long = evaluate(long_run_mileage)

    if overflow_to_long > 0:
        # Edge case: even at bounded long-run ratio, easy-day cap is still infeasible.
        # Preserve mileage by absorbing overflow into the long run (may exceed 35%).
        long_run_mileage = round(long_run_mileage + overflow_to_long, 2)

    return long_run_mileage, quality_distances, easy_distances


