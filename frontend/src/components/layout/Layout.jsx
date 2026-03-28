import { Outlet } from 'react-router-dom'
import ProtectedRoute from '../ProtectedRoute'
import Sidebar from './Sidebar'
import TopBar from './TopBar'

export default function Layout() {
  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-[#F9F8F5] dark:bg-[#0F0F0F]">
        <Sidebar />
        <div className="flex flex-col flex-1 ml-[220px] min-w-0 overflow-hidden">
          <TopBar />
          <main className="flex-1 overflow-y-auto p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </ProtectedRoute>
  )
}
