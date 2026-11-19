import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest } from '../api/client.js'

function HistoryPage() {
  const [orders, setOrders] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiRequest('/orders/mine')
      .then(setOrders)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <section>
      <h1>Sipariş geçmişi</h1>
      {loading && <p>Siparişler yükleniyor…</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {!loading && !error && orders.length === 0 && <p>Henüz siparişin yok.</p>}
      <ul className="order-list">
        {orders.map((order) => (
          <li key={order.order_id}>
            <div>
              <strong>{order.product_name}</strong>
              <p>{order.shop_name} · {order.status}</p>
            </div>
            <Link to={`/qr/${order.order_id}`}>Siparişi gör</Link>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default HistoryPage
