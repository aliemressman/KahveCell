import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { apiRequest } from '../api/client.js'
import AuthCard from '../components/AuthCard.jsx'

function OtpPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const phoneNumber = location.state?.phoneNumber
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function verifyCode(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const result = await apiRequest('/auth/verify-otp', {
        method: 'POST',
        body: { phone_number: phoneNumber, code },
        auth: false,
      })
      localStorage.setItem('kahvecell.accessToken', result.access_token)
      localStorage.setItem('kahvecell.refreshToken', result.refresh_token)
      navigate('/', { replace: true })
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  if (!phoneNumber) {
    return (
      <AuthCard
        title="Telefon doğrulaması"
        description="Önce telefon numaranı girerek kayıt işlemini başlat."
      >
        <Link className="auth-submit link-submit" to="/register">Kayıt ekranına dön</Link>
      </AuthCard>
    )
  }

  return (
    <AuthCard
      title="Telefonunu doğrula"
      description={`${phoneNumber} numarasına gelen 4 haneli kodu gir.`}
    >
      <form className="auth-form" onSubmit={verifyCode}>
        <label htmlFor="otpCode">Doğrulama kodu</label>
        <input
          id="otpCode"
          autoComplete="one-time-code"
          inputMode="numeric"
          maxLength={4}
          pattern="[0-9]{4}"
          placeholder="••••"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          required
        />
        <p className="otp-note">Test notu: SMS simülasyon kodu her zaman 1234.</p>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="auth-submit" disabled={busy} type="submit">
          {busy ? 'Doğrulanıyor…' : 'Telefonu doğrula'}
        </button>
      </form>
    </AuthCard>
  )
}

export default OtpPage
