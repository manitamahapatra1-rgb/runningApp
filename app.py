"""Minimal FastAPI app exposing plan-generation pipeline."""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from full_training_plan import assemble_training_plan
from mesocycle_phases import assign_training_phases
from vdot_paces import daniels_vdot
from weekly_mileage_progression import generate_weekly_mileage_progression

app = FastAPI()
DATABASE_URL = "sqlite:///./training_plans.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class TrainingPlanRecord(Base):
    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_time: Mapped[float] = mapped_column(Float, nullable=False)
    race_distance: Mapped[str] = mapped_column(String, nullable=False)
    weeks_until_race: Mapped[int] = mapped_column(Integer, nullable=False)
    starting_weekly_mileage: Mapped[float] = mapped_column(Float, nullable=False)
    mileage_cap: Mapped[float] = mapped_column(Float, nullable=False)
    generated_plan_json: Mapped[str] = mapped_column(Text, nullable=False)


Base.metadata.create_all(bind=engine)


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


class StoredPlanResponse(GeneratePlanResponse):
    id: int


@app.post("/api/generate-plan", response_model=StoredPlanResponse)
def generate_plan(payload: GeneratePlanRequest) -> StoredPlanResponse:
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

    generated_response = GeneratePlanResponse(
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

    with SessionLocal() as session:
        record = TrainingPlanRecord(
            race_time=payload.race_time,
            race_distance=payload.race_distance,
            weeks_until_race=payload.weeks_until_race,
            starting_weekly_mileage=payload.starting_weekly_mileage,
            mileage_cap=payload.mileage_cap,
            generated_plan_json=generated_response.model_dump_json(),
        )
        session.add(record)
        session.commit()
        session.refresh(record)

    return StoredPlanResponse(id=record.id, **generated_response.model_dump())


@app.get("/api/plan/{plan_id}", response_model=StoredPlanResponse)
def get_plan(plan_id: int) -> StoredPlanResponse:
    with SessionLocal() as session:
        record = session.get(TrainingPlanRecord, plan_id)

    if record is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    generated_response = GeneratePlanResponse.model_validate(json.loads(record.generated_plan_json))
    return StoredPlanResponse(id=record.id, **generated_response.model_dump())
