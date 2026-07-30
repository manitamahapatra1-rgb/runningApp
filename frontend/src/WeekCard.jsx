
import React, { useState } from "react";

const WORKOUT_STYLES = {
  "Easy Run": "bg-gradient-to-br from-sky-100 to-teal-100 border-sky-300 text-sky-900",
  "Long Run": "bg-gradient-to-br from-amber-100 to-yellow-100 border-amber-300 text-amber-900",
  Tempo: "bg-gradient-to-br from-amber-100 to-orange-100 border-orange-300 text-orange-900",
  Fartlek: "bg-gradient-to-br from-orange-100 to-orange-200 border-orange-300 text-orange-900",
  "Mile Reps": "bg-gradient-to-br from-red-100 to-rose-100 border-red-300 text-red-900",
};

function getWorkoutStyle(type) {
  return (
    WORKOUT_STYLES[type] ||
    "bg-gradient-to-br from-slate-100 to-slate-200 border-slate-300 text-slate-900"
  );
}

export default function WeekCard({ week }) {
  const [selectedWorkout, setSelectedWorkout] = useState(null);

  if (!week) return null;

  return (
    <>
      <div className="w-full rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <header className="mb-4">
          <h2 className="text-xl font-bold text-slate-900">Week {week.week}</h2>
          <p className="text-sm text-slate-600">Phase: {week.phase}</p>
          <p className="text-sm font-medium text-slate-800">
            Total Mileage: {week.total_mileage} mi
          </p>
        </header>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {week.workouts?.map((workout, idx) => (
            <button
              key={`${workout.day}-${workout.workout_type}-${idx}`}
              type="button"
              onClick={() => setSelectedWorkout(workout)}
              className={`rounded-xl border p-3 text-left shadow-sm transition hover:scale-[1.01] hover:shadow-md focus:outline-none focus:ring-2 focus:ring-slate-400 ${getWorkoutStyle(
                workout.workout_type
              )}`}
            >
              <div className="text-base font-bold">{workout.day}</div>
              <div className="mt-1 text-2xl font-extrabold">
                {workout.distance_miles} mi
              </div>
              <div className="mt-1 text-sm font-medium opacity-90">
                {workout.workout_type}
              </div>
            </button>
          ))}
        </div>
      </div>

      {selectedWorkout && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setSelectedWorkout(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold text-slate-900">Workout Details</h3>
            <div className="mt-4 space-y-2 text-slate-700">
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
                {selectedWorkout.distance_miles} miles
              </p>
              <p>
                <span className="font-semibold text-slate-900">Pace:</span>{" "}
                {selectedWorkout.pace}
              </p>
            </div>

            <button
              type="button"
              onClick={() => setSelectedWorkout(null)}
              className="mt-6 inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}
