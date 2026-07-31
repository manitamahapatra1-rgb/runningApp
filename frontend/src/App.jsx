import React, { useEffect, useMemo, useRef, useState } from "react";
import WeekCard from "./WeekCard";
import PlanForm from "./PlanForm";

const PLAN_API_URL =
  import.meta.env.VITE_PLAN_API_URL || "http://localhost:8000/api/generate-plan";

function formatApiError(errorPayload) {
  if (!errorPayload) return "Unable to generate training plan.";

  if (typeof errorPayload.detail === "string") {
    return errorPayload.detail;
  }

  if (Array.isArray(errorPayload.detail)) {
    return errorPayload.detail
      .map((item) => {
        const path = Array.isArray(item.loc) ? item.loc.join(" > ") : "field";
        return `${path}: ${item.msg}`;
      })
      .join(" | ");
  }

  return "Unable to generate training plan.";
}

export default function App() {
  const [appState, setAppState] = useState("form"); // form | loading | plan
  const [planData, setPlanData] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [currentWeekIndex, setCurrentWeekIndex] = useState(0);

  const weekRefs = useRef([]);
  const weeks = useMemo(() => planData?.plan ?? [], [planData]);

  const handleGeneratePlan = async (payload) => {
    setErrorMsg("");
    setAppState("loading");
    setCurrentWeekIndex(0);

    try {
      const res = await fetch(PLAN_API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        let apiError;
        try {
          apiError = await res.json();
        } catch {
          apiError = null;
        }
        throw new Error(formatApiError(apiError));
      }

      const data = await res.json();
      setPlanData(data);
      setAppState("plan");
    } catch (error) {
      setErrorMsg(error.message || "Unable to generate training plan.");
      setAppState("form");
    }
  };

  const handleReset = () => {
    setPlanData(null);
    setErrorMsg("");
    setCurrentWeekIndex(0);
    weekRefs.current = [];
    setAppState("form");
  };

  useEffect(() => {
    if (appState !== "plan" || !weeks.length) return;

    const updateCurrentWeek = () => {
      const anchorY = 130;
      let closestIdx = 0;
      let closestDistance = Number.POSITIVE_INFINITY;

      weekRefs.current.forEach((el, idx) => {
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const distance = Math.abs(rect.top - anchorY);
        if (distance < closestDistance) {
          closestDistance = distance;
          closestIdx = idx;
        }
      });

      setCurrentWeekIndex(closestIdx);
    };

    updateCurrentWeek();
    window.addEventListener("scroll", updateCurrentWeek, { passive: true });
    window.addEventListener("resize", updateCurrentWeek);

    return () => {
      window.removeEventListener("scroll", updateCurrentWeek);
      window.removeEventListener("resize", updateCurrentWeek);
    };
  }, [appState, weeks]);

  if (appState === "loading") {
    return (
      <div className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100">
        <div className="mx-auto flex w-full max-w-3xl items-center gap-3 rounded-xl border border-slate-700 bg-slate-900 px-4 py-4">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-500 border-t-blue-400" />
          <span>Generating your plan...</span>
        </div>
      </div>
    );
  }

  if (appState === "form") {
    return (
      <div className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100">
        <PlanForm
          onSubmit={handleGeneratePlan}
          isSubmitting={false}
          submitError={errorMsg}
        />
      </div>
    );
  }

  const totalWeeks = weeks.length;
  const currentWeek = weeks[currentWeekIndex];
  const weeksUntilRace =
    totalWeeks > 0 ? Math.max(totalWeeks - (currentWeekIndex + 1), 0) : 0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-40 border-b border-slate-700/80 bg-slate-900/85 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3 px-3 py-3 sm:px-4">
          <div className="flex min-w-0 flex-col gap-1">
            <p className="font-display text-sm font-semibold tracking-wide text-slate-100 sm:text-base">
              {totalWeeks > 0 && currentWeek
                ? `Week ${currentWeek.week} of ${totalWeeks} — ${currentWeek.phase}`
                : "Training Plan"}
            </p>
            <p className="text-xs text-slate-300 sm:text-sm">
              Weeks until race: {weeksUntilRace}
            </p>
          </div>
          <button
            type="button"
            onClick={handleReset}
            className="shrink-0 rounded-lg border border-slate-500 bg-slate-800 px-3 py-1.5 text-sm font-semibold text-slate-100 transition hover:bg-slate-700"
          >
            Create New Plan
          </button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl space-y-6 px-3 py-5 sm:px-4 sm:py-6">
        {weeks.map((week, idx) => (
          <div
            key={`week-${week.week}-${idx}`}
            ref={(el) => {
              weekRefs.current[idx] = el;
            }}
          >
            <WeekCard week={week} />
          </div>
        ))}
      </main>
    </div>
  );
}