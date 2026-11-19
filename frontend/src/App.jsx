import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout.jsx'
import AuthPage from './pages/AuthPage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import HomePage from './pages/HomePage.jsx'
import OrderPage from './pages/OrderPage.jsx'
import OtpPage from './pages/OtpPage.jsx'
import QrPage from './pages/QrPage.jsx'
import ShopDetailPage from './pages/ShopDetailPage.jsx'
import ShopsPage from './pages/ShopsPage.jsx'
import SubscriptionPage from './pages/SubscriptionPage.jsx'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="login" element={<AuthPage mode="login" />} />
        <Route path="login/otp" element={<AuthPage mode="otp-login" />} />
        <Route path="register" element={<AuthPage mode="register" />} />
        <Route path="otp" element={<OtpPage />} />
        <Route element={<AppLayout />}>
          <Route index element={<HomePage />} />
          <Route path="shops" element={<ShopsPage />} />
          <Route path="shops/:shopId" element={<ShopDetailPage />} />
          <Route path="order/new" element={<OrderPage />} />
          <Route path="qr/:orderId" element={<QrPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="subscription" element={<SubscriptionPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
