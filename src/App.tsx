import { Suspense, lazy, useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import type { LeadershipRadarData, TrackerData } from './types'
import './App.css'

const HomePage = lazy(async () => {
  const module = await import('./pages/HomePage')
  return { default: module.HomePage }
})

const DashboardPage = lazy(async () => {
  const module = await import('./pages/DashboardPage')
  return { default: module.DashboardPage }
})

const ResolutionPage = lazy(async () => {
  const module = await import('./pages/ResolutionPage')
  return { default: module.ResolutionPage }
})

const LeadershipRadarPage = lazy(async () => {
  const module = await import('./pages/LeadershipRadarPage')
  return { default: module.LeadershipRadarPage }
})

function LoadingState() {
  return (
    <div className="state-shell">
      <p className="eyebrow">Loading dataset</p>
      <h1>Preparing the shareholder dissent tracker</h1>
      <p className="lede">
        The app is reading the locally generated governance dataset from this repository.
      </p>
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="state-shell">
      <p className="eyebrow">Dataset unavailable</p>
      <h1>The dashboard could not load its local data file</h1>
      <p className="lede">{message}</p>
      <p className="state-shell__hint">
        Run <code>npm run data</code> and reload the app.
      </p>
    </div>
  )
}

function App() {
  const [data, setData] = useState<TrackerData | null>(null)
  const [radarData, setRadarData] = useState<LeadershipRadarData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function loadData() {
      try {
        const [trackerResponse, radarResponse] = await Promise.all([
          fetch('/data/tracker-data.json'),
          fetch('/data/leadership-radar.json'),
        ])
        if (!trackerResponse.ok || !radarResponse.ok) {
          throw new Error(
            `Dataset request failed (${trackerResponse.status}/${radarResponse.status}).`,
          )
        }

        const payload = (await trackerResponse.json()) as TrackerData
        const radarPayload = (await radarResponse.json()) as LeadershipRadarData
        if (active) {
          setData(payload)
          setRadarData(radarPayload)
        }
      } catch (loadError) {
        if (active) {
          setError(
            loadError instanceof Error ? loadError.message : 'Unknown loading error.',
          )
        }
      }
    }

    loadData()

    return () => {
      active = false
    }
  }, [])

  if (error) {
    return <ErrorState message={error} />
  }

  if (!data || !radarData) {
    return <LoadingState />
  }

  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingState />}>
        <Routes>
          <Route element={<Layout generatedAt={radarData.metadata.generatedAt} />}>
            <Route index element={<HomePage data={data} radarData={radarData} />} />
            <Route path="/radar" element={<LeadershipRadarPage data={radarData} />} />
            <Route path="/proxy-voting" element={<DashboardPage data={data} />} />
            <Route path="/dashboard" element={<Navigate replace to="/radar" />} />
            <Route path="/resolution/:id" element={<ResolutionPage data={data} />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

export default App
