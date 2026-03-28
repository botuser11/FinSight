import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Transactions from './pages/Transactions'
import Anomalies from './pages/Anomalies'
import Forecast from './pages/Forecast'
import Savings from './pages/Savings'
import EmptyState from './components/ui/EmptyState'
import { PieChart } from 'lucide-react'

function Placeholder({ title, Icon }) {
  return (
    <div className="flex items-center justify-center h-[60vh]">
      <EmptyState icon={Icon} title={title} description="Coming soon." />
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route element={<Layout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/categories" element={<Placeholder title="Categories" Icon={PieChart} />} />
        <Route path="/forecast" element={<Forecast />} />
        <Route path="/anomalies" element={<Anomalies />} />
        <Route path="/savings" element={<Savings />} />
      </Route>
    </Routes>
  )
}

export default App
