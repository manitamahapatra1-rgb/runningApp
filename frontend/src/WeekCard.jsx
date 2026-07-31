import React, { useEffect, useState } from "react";
import { Footprints, Gauge, Route, Timer, X, Zap } from "lucide-react";

const PHASE_ACCENTS = {
  Base: {
    bar: "bg-emerald-500",
    border: "border-l-emerald-500",
    badge: "bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-400/40",
    mileage: "text-emerald-300",
  },
  Build: {
    bar: "bg-blue-500",
    border: "border-l-blue-500",
    badge: "bg-blue-500/20 text-blue-200 ring-1 ring-blue-400/40",
    mileage: "text-blue-300",
  },
  Peak: {
    bar: "bg-purple-500",
    border: "border-l-purple-500",
    badge: "bg-purple-500/20 text-purple-200 ring-1 ring-purple-400/40",
    mileage: "text-purple-300",
  },
  Taper: {
    bar: "bg-orange-500",
    border: "border-l-orange-500",
    badge: "bg-orange-500/20 text-orange-200 ring-1 ring-orange-400/40",
    mileage: "text-orange-300",
  },
};

const WORKOUT_META = {
  "Easy Run": {
    icon: Footprints,
    card: "bg-gradient-to-br from-sky-100 to-teal-100 border-sky-300 text-sky-900",
    distance: "text-sky-900",
    modal: "bg-gradient-to-br from-sky-50 to-teal-50 border-sky-200",
  },
  "Long Run": {
    icon: Route,
    card: "bg-gradient-to-br from-amber-100 to-yellow-100 border-amber-300 text-amber-900",
    distance: "text-amber-900",
    modal: "bg-gradient-to-br from-amber-50 to-yellow-50 border-amber-200",
  },
  Tempo: {
    icon: Gauge,
    card: "bg-gradient-to-br from-amber-100 to-orange-100 border-orange-300 text-orange-900",
    distance: "text-orange-900",
    modal: "bg-gradient-to-br from-amber-50 to-orange-50 border-orange-200",
  },
  Fartlek: {
    icon: Zap,
    card: "bg-gradient-to-br from-orange-100 to-orange-200 border-orange-300 text-orange-900",
    distance: "text-orange-900",
    modal: "bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200",
  },
  "Mile Reps": {
    icon: Timer,
    card: "bg-gradient-to-br from-red-100 to-rose-100 border-red-300 text-red-900",
    distance: "text-red-900",
    modal: "bg-gradient-to-br from-red-50 to-rose-50 border-red-200",
  },
};

const DEFAULT_WORKOUT = {
  icon: Footprints,
  card: "bg-gradient-to-br from-slate-100 to-slate-200 border-slate-300 text-slate-900",
  distance: "text-slate-900",
  modal: "bg-slate-50 border-slate-200",
};

export default function WeekCard({ week }) {
  const [selectedWorkout, setSelectedWorkout] = useState(null);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === "Escape") {
        setSelectedWorkout(null);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  if (!week) return null;

  const phaseStyles = PHASE_ACCENTS[week.phase] || {
    bar: "bg-slate-500",
    border: "border-l-slate-500",
    badge: "bg-slate-500/20 text-slate-200 ring-1 ring-slate-400/40",
    mileage: "text-slate-200",
  };

  const selectedMeta = selectedWorkout
    ? WORKOUT_META[selectedWorkout.workout_type] || DEFAULT_WORKOUT
    : DEFAULT_WORKOUT;

  return (
    <>
      <section
        className={`relative overflow-hidden rounded-2xl border border-slate-700 border-l-4 ${phaseStyles.border} bg-slate-800 p-5 shadow-2xl shadow-black/40 sm:p-6`}
      >
        <div className={`absolute inset-x-0 top-0 h-1.5 ${phaseStyles.bar}`} />

        <header className="mb-5 mt-1 flex items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-4xl font-bold leading-none text-white sm:text-5xl">
              Week {week.week}
            </h2>

            <div className="mt-3 space-y-1.5 text-xs text-slate-300 sm:text-sm">
              <p>
                Total Mileage:{" "}
                <span className={`font-display text-xl font-bold sm:text-2xl ${phaseStyles.mileage}`}>
                  {week.total_mileage} mi
                </span>
              </p>
              <p>
                Long Run:{" "}
                <span className="font-semibold text-slate-100">
                  {week.long_run_mileage} mi
                </span>
              </p>
            </div>
          </div>

          <span
            className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${phaseStyles.badge}`}
          >
            {week.phase}
          </span>
        </header>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
          {week.workouts?.map((workout, idx) => {
            const meta = WORKOUT_META[workout.workout_type] || DEFAULT_WORKOUT;
            const Icon = meta.icon;

            return (
              <button
                key={`${workout.day}-${workout.workout_type}-${idx}`}
                type="button"
                onClick={() => setSelectedWorkout(workout)}
                className={`min-h-[170px] rounded-xl border p-4 text-left shadow-md transition hover:-translate-y-0.5 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-slate-300 ${meta.card} sm:min-h-[190px] sm:p-5`}
              >
                <p className="text-base font-bold leading-tight sm:text-lg">
                  {workout.day}
                </p>
                <p
                  className={`mt-2 font-display text-3xl font-bold leading-tight sm:text-4xl ${meta.distance}`}
                >
                  {workout.distance_miles} mi
                </p>
                <p className="mt-3 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide opacity-95 sm:text-sm">
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{workout.workout_type}</span>
                </p>
              </button>
            );
          })}
        </div>
      </section>

      {selectedWorkout && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setSelectedWorkout(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            className={`w-full max-w-md rounded-2xl border p-6 shadow-2xl ${selectedMeta.modal}`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between">
              <h3 className="font-display text-xl font-bold text-slate-900">
                Workout Details
              </h3>
              <button
                type="button"
                onClick={() => setSelectedWorkout(null)}
                className="rounded-md p-1 text-slate-500 hover:bg-slate-200/70 hover:text-slate-700"
                aria-label="Close workout details"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3 text-sm text-slate-700 sm:text-base">
              <p>
                <span className="font-semibold text-slate-900">Day:</span>{" "}
                {selectedWorkout.day}
              </p>
              <p>
                <span className="font-semibold text-slate-900">Workout Type:</span>{" "}
                {selectedWorkout.workout_type}
              </p>
              <p>
                <span className="font-semibold text-slate-900">Distance:</span>{" "}
                <span className="font-display text-xl font-bold text-slate-900">
                  {selectedWorkout.distance_miles} miles
                </span>
              </p>
              <p>
                <span className="font-semibold text-slate-900">Pace:</span>{" "}
                {selectedWorkout.pace}
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}