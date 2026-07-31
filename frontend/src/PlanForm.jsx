import React, { useMemo, useState } from "react";

const DISTANCE_OPTIONS = [
  { label: "5K", value: "5k" },
  { label: "10K", value: "10k" },
  { label: "Half Marathon", value: "half_marathon" },
  { label: "Marathon", value: "marathon" },
];

function toNumber(value) {
  if (value === "" || value === null || value === undefined) return NaN;
  return Number(value);
}

export default function PlanForm({ onSubmit, isSubmitting, submitError }) {
  const [hours, setHours] = useState("0");
  const [minutes, setMinutes] = useState("22");
  const [seconds, setSeconds] = useState("0");
  const [raceDistance, setRaceDistance] = useState("10k");
  const [weeksUntilRace, setWeeksUntilRace] = useState("10");
  const [startingWeeklyMileage, setStartingWeeklyMileage] = useState("18");
  const [mileageCap, setMileageCap] = useState("38");
  const [localError, setLocalError] = useState("");

  const displayedError = useMemo(
    () => localError || submitError || "",
    [localError, submitError]
  );

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLocalError("");

    const hoursNum = toNumber(hours);
    const minutesNum = toNumber(minutes);
    const secondsNum = toNumber(seconds);
    const weeksNum = toNumber(weeksUntilRace);
    const startingMileageNum = toNumber(startingWeeklyMileage);
    const mileageCapNum = toNumber(mileageCap);

    if (
      Number.isNaN(hoursNum) ||
      Number.isNaN(minutesNum) ||
      Number.isNaN(secondsNum) ||
      Number.isNaN(weeksNum) ||
      Number.isNaN(startingMileageNum) ||
      Number.isNaN(mileageCapNum)
    ) {
      setLocalError("Please fill in all required fields with valid numbers.");
      return;
    }

    if (hoursNum < 0 || minutesNum < 0 || secondsNum < 0) {
      setLocalError("Race time values must be non-negative.");
      return;
    }

    if (minutesNum >= 60 || secondsNum >= 60) {
      setLocalError("Minutes and seconds must be less than 60.");
      return;
    }

    const raceTimeSeconds = hoursNum * 3600 + minutesNum * 60 + secondsNum;
    if (raceTimeSeconds <= 0) {
      setLocalError("Recent race time must be greater than 0.");
      return;
    }

    if (!raceDistance) {
      setLocalError("Please select a goal race distance.");
      return;
    }

    if (weeksNum < 1) {
      setLocalError("Weeks until race must be at least 1.");
      return;
    }

    if (startingMileageNum <= 0 || mileageCapNum <= 0) {
      setLocalError("Mileage values must be greater than 0.");
      return;
    }

    if (mileageCapNum < startingMileageNum) {
      setLocalError("Mileage cap must be greater than or equal to starting weekly mileage.");
      return;
    }

    await onSubmit({
      race_time: raceTimeSeconds,
      race_distance: raceDistance,
      weeks_until_race: Math.trunc(weeksNum),
      starting_weekly_mileage: Number(startingMileageNum),
      mileage_cap: Number(mileageCapNum),
    });
  };

  return (
    <section className="mx-auto w-full max-w-3xl rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl shadow-black/40 sm:p-6">
      <h1 className="font-display text-2xl font-bold text-white sm:text-3xl">
        Create Training Plan
      </h1>
      <p className="mt-1 text-sm text-slate-300">
        Enter your goal distance first, then your most recent finish time for that same distance.
      </p>

      <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-200">
              Goal Race Distance
            </label>
            <select
              value={raceDistance}
              onChange={(e) => setRaceDistance(e.target.value)}
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 outline-none ring-blue-500 focus:ring-2"
              required
            >
              {DISTANCE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-200">
              Weeks Until Race
            </label>
            <input
              type="number"
              min="1"
              step="1"
              value={weeksUntilRace}
              onChange={(e) => setWeeksUntilRace(e.target.value)}
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 outline-none ring-blue-500 placeholder:text-slate-400 focus:ring-2"
              required
            />
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-200">
            Recent Race Time (for selected Goal Race Distance)
          </label>
          <p className="mb-2 text-xs text-slate-400">
            Enter your most recent finish time for{" "}
            {DISTANCE_OPTIONS.find((option) => option.value === raceDistance)?.label || "this distance"}.
          </p>
          <div className="grid grid-cols-3 gap-3">
            <input
              type="number"
              min="0"
              step="1"
              value={hours}
              onChange={(e) => setHours(e.target.value)}
              className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 outline-none ring-blue-500 placeholder:text-slate-400 focus:ring-2"
              placeholder="Hours"
              required
            />
            <input
              type="number"
              min="0"
              max="59"
              step="1"
              value={minutes}
              onChange={(e) => setMinutes(e.target.value)}
              className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 outline-none ring-blue-500 placeholder:text-slate-400 focus:ring-2"
              placeholder="Minutes"
              required
            />
            <input
              type="number"
              min="0"
              max="59"
              step="1"
              value={seconds}
              onChange={(e) => setSeconds(e.target.value)}
              className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 outline-none ring-blue-500 placeholder:text-slate-400 focus:ring-2"
              placeholder="Seconds"
              required
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-200">
              Starting Weekly Mileage
            </label>
            <input
              type="number"
              min="0"
              step="0.1"
              value={startingWeeklyMileage}
              onChange={(e) => setStartingWeeklyMileage(e.target.value)}
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 outline-none ring-blue-500 placeholder:text-slate-400 focus:ring-2"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-200">
              Mileage Cap
            </label>
            <input
              type="number"
              min="0"
              step="0.1"
              value={mileageCap}
              onChange={(e) => setMileageCap(e.target.value)}
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 outline-none ring-blue-500 placeholder:text-slate-400 focus:ring-2"
              required
            />
          </div>
        </div>

        {displayedError && (
          <p className="rounded-lg border border-red-700/50 bg-red-900/30 px-3 py-2 text-sm text-red-200">
            {displayedError}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Generating..." : "Generate Plan"}
        </button>
      </form>
    </section>
  );
}