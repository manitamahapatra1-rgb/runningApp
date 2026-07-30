import WeekCard from './WeekCard'
import mockPlan from './mockPlan.json'

function App() {
  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4">
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-6 text-3xl font-bold text-slate-900">
          Training Plan
        </h1>
        <div className="flex flex-col gap-6">
          {mockPlan.plan.map((week) => (
            <WeekCard key={week.week} week={week} />
          ))}
        </div>
      </div>
    </div>
  )
}

export default App