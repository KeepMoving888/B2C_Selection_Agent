import { createHashRouter, Navigate } from 'react-router-dom'
import MainLayout from './components/Layout/MainLayout'
import ActionPlan from './pages/ActionPlan'
import Compliance from './pages/Compliance'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import MarketAnalysis from './pages/MarketAnalysis'
import NotFound from './pages/NotFound'
import ProfitAnalysis from './pages/ProfitAnalysis'
import ReportCenter from './pages/ReportCenter'
import ReviewInsights from './pages/ReviewInsights'
import Settings from './pages/Settings'
import Suppliers from './pages/Suppliers'
import TrendSeasonal from './pages/TrendSeasonal'

export const router = createHashRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'market-analysis', element: <MarketAnalysis /> },
      { path: 'trend-seasonal', element: <TrendSeasonal /> },
      { path: 'review-insights', element: <ReviewInsights /> },
      { path: 'profit-analysis', element: <ProfitAnalysis /> },
      { path: 'suppliers', element: <Suppliers /> },
      { path: 'compliance', element: <Compliance /> },
      { path: 'action-plan', element: <ActionPlan /> },
      { path: 'report-center', element: <ReportCenter /> },
      { path: 'settings', element: <Settings /> },
      { path: 'help', element: <Navigate to="/settings" replace /> },
      { path: '*', element: <NotFound /> },
    ],
  },
])
