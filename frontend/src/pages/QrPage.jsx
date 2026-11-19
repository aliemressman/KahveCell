import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { apiRequest } from '../api/client.js'

function QrPage() {
  const { orderId } = useParams()
  const location = useLocation()
  const [order, setOrder] = useState(location.state?.order || null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (order) return
    apiRequest(`/orders/${orderId}`)
      .then(setOrder)
      .catch((requestError) => setError(requestError.message))
  }, [order, orderId])

  if (error) return <p className="error" role="alert">{error}</p>
  if (!order) return <p>Sipariş ve QR kod yükleniyor…</p>

  return (
    <section className="narrow-page">
      <h1>Sipariş QR kodu</h1>
      <p>{order.shop_name} · {order.product_name}</p>
      <p>Sipariş durumu: {order.status}</p>
      <img className="qr-image" src={order.qr_code_image} alt="Sipariş QR kodu" />
      <details>
        <summary>QR kod verisi</summary>
        <pre>{JSON.stringify(order.qr_code, null, 2)}</pre>
      </details>
      <Link to="/history">Sipariş geçmişine git</Link>
    </section>
  )
}

export default QrPage
