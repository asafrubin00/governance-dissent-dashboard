import { Suspense, lazy, useEffect, useState } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import type { TrackerData } from './types'
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
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function loadData() {
      try {
        const response = await fetch('/data/tracker-data.json')
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}.`)
        }

        const payload = (await response.json()) as TrackerData
        if (active) {
          setData(payload)
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

  if (!data) {
    return <LoadingState />
  }

  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingState />}>
        <Routes>
          <Route element={<Layout generatedAt={data.metadata.generatedAt} />}>
            <Route index element={<HomePage data={data} />} />
            <Route path="/dashboard" element={<DashboardPage data={data} />} />
            <Route path="/resolution/:id" element={<ResolutionPage data={data} />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

export default App
