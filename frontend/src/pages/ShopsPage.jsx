import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest } from '../api/client.js'
import ShopMap from '../components/ShopMap.jsx'

function ShopsPage() {
  const [shops, setShops] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiRequest('/shops')
      .then(setShops)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <section className="page-heading">
        <h1>Yakınındaki kahveler</h1>
        <p>Dükkânları haritada keşfet, menülerine göz at.</p>
      </section>
      {loading && <p>Harita yükleniyor…</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {!loading && !error && (
        <>
          <ShopMap shops={shops} />
          <section className="shop-list" aria-label="Dükkânlar">
            {shops.map((shop) => (
              <article className="shop-card" key={shop.id}>
                <div>
                  <h2>{shop.name}</h2>
                  <p>{shop.address}</p>
                </div>
                <Link className="button-link" to={`/shops/${shop.id}`}>
                  Detay ve menü
                </Link>
              </article>
            ))}
            {shops.length === 0 && <p>Henüz listelenecek dükkân yok.</p>}
          </section>
        </>
      )}
    </>
  )
}

export default ShopsPage
