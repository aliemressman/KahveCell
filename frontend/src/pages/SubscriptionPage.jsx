import { useEffect, useState } from 'react'
import { apiRequest, ApiError } from '../api/client.js'

function SubscriptionPage() {
  const [plans, setPlans] = useState([])
  const [activeSubscription, setActiveSubscription] = useState(null)
  const [planType, setPlanType] = useState('STARTER')
  const [cardNumber, setCardNumber] = useState('4242-4242-4242-4242')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    apiRequest('/subscriptions/plans', { auth: false })
      .then(setPlans)
      .catch((requestError) => setError(requestError.message))
    apiRequest('/subscriptions/me')
      .then(setActiveSubscription)
      .catch((requestError) => {
        if (!(requestError instanceof ApiError) || requestError.statusCode !== 404) {
          setError(requestError.message)
        }
      })
  }, [])

  async function purchasePlan(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const path = activeSubscription ? '/subscriptions/me' : '/subscriptions'
      const method = activeSubscription ? 'PATCH' : 'POST'
      const result = await apiRequest(path, {
        method,
        body: { plan_type: planType, card_number: cardNumber },
      })
      setActiveSubscription(result.subscription)
      setMessage(result.message)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h1>Abonelik</h1>
      {activeSubscription ? (
        <p>
          Aktif paket: <strong>{activeSubscription.plan_name}</strong>
          {' · '}Kalan kahve: {activeSubscription.remaining_credits ?? 'Sınırsız'}
        </p>
      ) : (
        <p>Aktif bir aboneliğin bulunmuyor.</p>
      )}
      <div className="plan-list">
        {plans.map((plan) => (
          <article className="plan-card" key={plan.plan_type}>
            <h2>{plan.name}</h2>
            <p>{plan.monthly_price} TL / ay</p>
            <p>{plan.coffee_credits ?? 'Sınırsız'} kahve</p>
          </article>
        ))}
      </div>
      <form className="form narrow-form" onSubmit={purchasePlan}>
        <label htmlFor="plan">Paket seç</label>
        <select id="plan" value={planType} onChange={(event) => setPlanType(event.target.value)}>
          {plans.map((plan) => (
            <option key={plan.plan_type} value={plan.plan_type}>{plan.name}</option>
          ))}
        </select>
        <label htmlFor="cardNumber">Test kartı</label>
        <input
          id="cardNumber"
          value={cardNumber}
          onChange={(event) => setCardNumber(event.target.value)}
          required
        />
        <button disabled={busy || plans.length === 0} type="submit">
          {busy ? 'İşleniyor…' : activeSubscription ? 'Paketi değiştir' : 'Satın al'}
        </button>
      </form>
      {message && <p role="status">{message}</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </section>
  )
}

export default SubscriptionPage
