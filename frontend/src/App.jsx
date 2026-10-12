import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/layout/Layout'
import LoadingSpinner from './components/ui/LoadingSpinner'

// Route-level code splitting: each page (and its chart code) loads on demand
const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Transactions = lazy(() => import('./pages/Transactions'))
const Categories = lazy(() => import('./pages/Categories'))
const Anomalies = lazy(() => import('./pages/Anomalies'))
const Forecast = lazy(() => import('./pages/Forecast'))
const Savings = lazy(() => import('./pages/Savings'))

function App() {
  return (
    <Suspense fallback={<LoadingSpinner size="lg" className="h-[60vh]" />}>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/categories" element={<Categories />} />
          <Route path="/forecast" element={<Forecast />} />
          <Route path="/anomalies" element={<Anomalies />} />
          <Route path="/savings" element={<Savings />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

export default App
