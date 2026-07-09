import { createBrowserRouter, Navigate } from 'react-router-dom'
import MainLayout from './components/Layout/MainLayout'
import Dashboard from './pages/Dashboard'
import ProductAnalysis from './pages/ProductAnalysis'
import ProfitCalculator from './pages/ProfitCalculator'
import MarketInsights from './pages/MarketInsights'
import ReviewAnalytics from './pages/ReviewAnalytics'
import ReportCenter from './pages/ReportCenter'
import Settings from './pages/Settings'
import Login from './pages/Login'
import NotFound from './pages/NotFound'

export const router = createBrowserRouter([
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
      { path: 'product-analysis', element: <ProductAnalysis /> },
      { path: 'profit-calculator', element: <ProfitCalculator /> },
      { path: 'market-insights', element: <MarketInsights /> },
      { path: 'review-analytics', element: <ReviewAnalytics /> },
      { path: 'report-center', element: <ReportCenter /> },
      { path: 'settings', element: <Settings /> },
      { path: 'help', element: <Navigate to="/settings" replace /> },
      { path: '*', element: <NotFound /> },
    ],
  },
])
