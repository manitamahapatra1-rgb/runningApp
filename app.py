"""Minimal FastAPI app exposing plan-generation pipeline."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from full_training_plan import assemble_training_plan
from mesocycle_phases import assign_training_phases
from vdot_paces import daniels_vdot
from weekly_mileage_progression import generate_weekly_mileage_progression

app = FastAPI()


class GeneratePlanRequest(BaseModel):
    race_time: float = Field(gt=0, description="Race time in seconds.")
    race_distance: str
    weeks_until_race: int = Field(ge=1)
    starting_weekly_mileage: float = Field(gt=0)
    mileage_cap: float = Field(gt=0)


class WorkoutResponse(BaseModel):
    day: str
    workout_type: str
    distance_miles: float
    pace: str


class WeekPlanResponse(BaseModel):
    week: int
    phase: str
    total_mileage: float
    long_run_mileage: float
    workouts: list[WorkoutResponse]


class GeneratePlanResponse(BaseModel):
    plan: list[WeekPlanResponse]


@app.post("/api/generate-plan", response_model=GeneratePlanResponse)
def generate_plan(payload: GeneratePlanRequest) -> GeneratePlanResponse:
    vdot_result = daniels_vdot(payload.race_time, payload.race_distance)
    mesocycle_plan = assign_training_phases(payload.weeks_until_race, payload.race_distance)
    mileage_plan = generate_weekly_mileage_progression(
        starting_weekly_mileage=payload.starting_weekly_mileage,
        weekly_mileage_cap=payload.mileage_cap,
        total_weeks=payload.weeks_until_race,
    )
    full_plan = assemble_training_plan(
        phase_weeks=mesocycle_plan.weeks,
        mileage_weeks=mileage_plan,
        training_paces=vdot_result.paces,
    )

    return GeneratePlanResponse(
        plan=[
            WeekPlanResponse(
                week=week.week,
                phase=week.phase,
                total_mileage=week.total_mileage,
                long_run_mileage=week.long_run_mileage,
                workouts=[
                    WorkoutResponse(
                        day=workout.day,
                        workout_type=workout.workout_type,
                        distance_miles=workout.distance_miles,
                        pace=workout.pace,
                    )
                    for workout in week.workouts
                ],
            )
            for week in full_plan
        ]
    )
