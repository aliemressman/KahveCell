import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiRequest } from '../api/client.js'

function ShopDetailPage() {
  const { shopId } = useParams()
  const [shop, setShop] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    apiRequest(`/shops/${shopId}`)
      .then(setShop)
      .catch((requestError) => setError(requestError.message))
  }, [shopId])

  if (error) return <p className="error" role="alert">{error}</p>
  if (!shop) return <p>Dükkân bilgileri yükleniyor…</p>

  return (
    <section>
      <Link to="/">← Dükkân listesine dön</Link>
      <h1>{shop.name}</h1>
      <p>{shop.address}</p>
      <h2>Menü</h2>
      <ul className="menu-list">
        {shop.products.map((product) => (
          <li key={product.id}>
            <span>{product.name}</span>
            <span>{Number(product.price).toFixed(2)} TL</span>
          </li>
        ))}
      </ul>
      <Link className="button-link" to={`/order/new?shopId=${shop.id}`}>
        Bu dükkândan sipariş ver
      </Link>
    </section>
  )
}

export default ShopDetailPage
