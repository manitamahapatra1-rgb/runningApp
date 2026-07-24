"""
Weekly mileage progression with cutback logic and long-run safeguards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


_CUTBACK_REDUCTION = 0.22  # Fixed 22% cutback (within the required 20-25% range).


@dataclass(frozen=True)
class WeekMileage:
    """Mileage targets for one training week."""

    week: int
    total_mileage: float
    long_run_mileage: float


def generate_weekly_mileage_progression(
    starting_weekly_mileage: float,
    weekly_mileage_cap: float,
    total_weeks: int,
    scheduled_runs_per_week: int | Sequence[int] = 4,
) -> list[WeekMileage]:
    """
    Generate week-by-week mileage progression for a training plan.

    Rule 1 (weekly progression + cap):
    Total mileage increases by exactly 1 mile per scheduled run each increase-week.
    This keeps load progression predictable while limiting sudden spikes. Once the
    weekly cap is reached, mileage holds at that cap to limit overload risk.

    Rule 2 (long run progression):
    The long run is managed separately and grows more slowly than total mileage:
    it increases every second increase-week (not every single week), holds flat
    during cutback/cap-hold weeks, and is always capped at 30% of weekly total.
    This reduces concentrated stress from overly aggressive long-run growth.

    Rule 3 (cutback week after 3 increases):
    After 3 consecutive increase-weeks, a cutback week reduces total mileage by
    22% (inside the required 20-25% band). This planned deload helps recovery,
    then progression resumes from the reduced baseline rather than the pre-cutback
    level.

    Parameters
    ----------
    starting_weekly_mileage:
        Initial weekly mileage before progression starts.
    weekly_mileage_cap:
        User-defined maximum weekly mileage.
    total_weeks:
        Number of weeks to generate.
    scheduled_runs_per_week:
        Either a single integer (same each week) or a per-week sequence.

    Returns
    -------
    list[WeekMileage]
        Week-by-week targets with total mileage and long-run mileage.
    """
    if total_weeks < 1:
        raise ValueError("total_weeks must be at least 1")
    if starting_weekly_mileage <= 0:
        raise ValueError("starting_weekly_mileage must be positive")
    if weekly_mileage_cap <= 0:
        raise ValueError("weekly_mileage_cap must be positive")

    if isinstance(scheduled_runs_per_week, int):
        if scheduled_runs_per_week < 1:
            raise ValueError("scheduled_runs_per_week must be at least 1")
        runs_schedule = [scheduled_runs_per_week] * total_weeks
    else:
        runs_schedule = list(scheduled_runs_per_week)
        if len(runs_schedule) != total_weeks:
            raise ValueError("scheduled_runs_per_week sequence length must match total_weeks")
        if any(runs < 1 for runs in runs_schedule):
            raise ValueError("scheduled_runs_per_week values must be at least 1")

    week_1_total = min(starting_weekly_mileage, weekly_mileage_cap)
    week_1_long_run = min(week_1_total * 0.25, week_1_total * 0.30)
    plan: list[WeekMileage] = [
        WeekMileage(week=1, total_mileage=round(week_1_total, 2), long_run_mileage=round(week_1_long_run, 2))
    ]

    consecutive_increase_weeks = 0
    increase_weeks_since_long_run_bump = 0

    for week_index in range(1, total_weeks):
        previous = plan[-1]
        previous_total = previous.total_mileage
        previous_long_run = previous.long_run_mileage

        # Rule 1: hold at cap once reached.
        if previous_total >= weekly_mileage_cap:
            current_total = weekly_mileage_cap
            consecutive_increase_weeks = 0
        # Rule 3: after 3 consecutive increase-weeks, insert a cutback week.
        elif consecutive_increase_weeks >= 3:
            current_total = previous_total * (1.0 - _CUTBACK_REDUCTION)
            consecutive_increase_weeks = 0
        else:
            # Rule 1: increase by 1 mile per scheduled run for the week.
            current_total = min(previous_total + runs_schedule[week_index], weekly_mileage_cap)

            if current_total > previous_total:
                consecutive_increase_weeks += 1
            else:
                consecutive_increase_weeks = 0

        # Rule 2: long run grows slower (every second increase-week), never >30% of total.
        if current_total < previous_total:
            long_run_candidate = previous_long_run
        elif current_total > previous_total:
            increase_weeks_since_long_run_bump += 1
            if increase_weeks_since_long_run_bump % 2 == 0:
                long_run_candidate = previous_long_run + 1.0
            else:
                long_run_candidate = previous_long_run
        else:
            long_run_candidate = previous_long_run

        current_long_run = min(long_run_candidate, current_total * 0.30)

        plan.append(
            WeekMileage(
                week=week_index + 1,
                total_mileage=round(current_total, 2),
                long_run_mileage=round(current_long_run, 2),
            )
        )

    return plan


if __name__ == "__main__":
    scenario_a = generate_weekly_mileage_progression(
        starting_weekly_mileage=18,
        weekly_mileage_cap=50,
        total_weeks=16,
        scheduled_runs_per_week=5,
    )
    print("Scenario A: starts well below cap (shows multiple cutback cycles)")
    for week in scenario_a:
        print(f"Week {week.week:2d}: total={week.total_mileage:5.2f} | long_run={week.long_run_mileage:5.2f}")
    print()

    scenario_b = generate_weekly_mileage_progression(
        starting_weekly_mileage=34,
        weekly_mileage_cap=40,
        total_weeks=10,
        scheduled_runs_per_week=4,
    )
    print("Scenario B: starts near cap (shows cap hold behavior)")
    for week in scenario_b:
        print(f"Week {week.week:2d}: total={week.total_mileage:5.2f} | long_run={week.long_run_mileage:5.2f}")
