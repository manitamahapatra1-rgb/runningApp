import { useState, useEffect } from 'react'
import WeekCard from './WeekCard'

function App() {
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('http://localhost:8000/api/generate-plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        race_time: 1320,
        race_distance: '10k',
        weeks_until_race: 10,
        starting_weekly_mileage: 18,
        mileage_cap: 38,
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Server responded with ${res.status}`)
        return res.json()
      })
      .then((data) => {
        setPlan(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) return <div className="p-8 text-center text-slate-600">Loading your plan...</div>
  if (error) return <div className="p-8 text-center text-red-600">Error: {error}</div>

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4">
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-6 text-3xl font-bold text-slate-900">
          Training Plan
        </h1>
        <div className="flex flex-col gap-6">
          {plan.plan.map((week) => (
            <WeekCard key={week.week} week={week} />
          ))}
        </div>
      </div>
    </div>
  )
}

export default App