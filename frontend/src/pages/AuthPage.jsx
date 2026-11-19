import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiRequest } from '../api/client.js'
import AuthCard from '../components/AuthCard.jsx'

function AuthPage({ mode }) {
  const isRegister = mode === 'register'
  const isOtpLogin = mode === 'otp-login'
  const navigate = useNavigate()
  const [phoneNumber, setPhoneNumber] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setError('')
    setBusy(true)

    try {
      if (isOtpLogin) {
        await apiRequest('/auth/login', {
          method: 'POST',
          body: { phone_number: phoneNumber },
          auth: false,
        })
        navigate('/otp', { state: { phoneNumber } })
        return
      }

      if (isRegister) {
        await apiRequest('/auth/register', {
          method: 'POST',
          body: {
            phone_number: phoneNumber,
            full_name: fullName,
            password,
          },
          auth: false,
        })
        navigate('/otp', { state: { phoneNumber } })
        return
      }

      const result = await apiRequest('/auth/login/password', {
        method: 'POST',
        body: { phone_number: phoneNumber, password },
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

  return (
    <AuthCard
      title={
        isRegister
          ? 'Hesap oluştur'
          : isOtpLogin
            ? 'SMS ile giriş'
            : 'Tekrar hoşgeldin'
      }
      description={
        isRegister
          ? 'KahveCell hesabın için bilgilerini gir.'
          : isOtpLogin
            ? 'Telefonuna gelen doğrulama koduyla devam et.'
            : 'Devam etmek için hesabına giriş yap.'
      }
    >
      <form className="auth-form" onSubmit={submit}>
        {isRegister && (
          <>
            <label htmlFor="fullName">Ad soyad</label>
            <input
              id="fullName"
              autoComplete="name"
              maxLength={100}
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              required
            />
          </>
        )}
        <label htmlFor="phoneNumber">Telefon numarası</label>
        <input
          id="phoneNumber"
          autoComplete="tel"
          inputMode="tel"
          placeholder="+905550000001"
          value={phoneNumber}
          onChange={(event) => setPhoneNumber(event.target.value)}
          required
        />
        {!isOtpLogin && (
          <>
            <label htmlFor="password">Şifre</label>
            <input
              id="password"
              type="password"
              autoComplete={isRegister ? 'new-password' : 'current-password'}
              minLength={8}
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </>
        )}
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="auth-submit" disabled={busy} type="submit">
          {busy
            ? 'Lütfen bekle…'
            : isRegister
              ? 'Kayıt ol'
              : isOtpLogin
                ? 'Doğrulama kodu iste'
                : 'Giriş yap'}
        </button>
      </form>
      {isOtpLogin ? (
        <p className="auth-switch"><Link to="/login">Şifreyle girişe dön</Link></p>
      ) : (
        <p className="auth-switch">
          {isRegister ? 'Zaten hesabın var mı?' : 'Henüz hesabın yok mu?'}{' '}
          <Link to={isRegister ? '/login' : '/register'}>
            {isRegister ? 'Giriş yap' : 'Kayıt ol'}
          </Link>
        </p>
      )}
      {!isRegister && !isOtpLogin && (
        <p className="auth-switch">
          <Link to="/login/otp">SMS koduyla giriş</Link>
        </p>
      )}
    </AuthCard>
  )
}

export default AuthPage
