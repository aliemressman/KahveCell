import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiRequest } from '../api/client.js'

function OrderPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const shopId = searchParams.get('shopId')
  const [products, setProducts] = useState([])
  const [productId, setProductId] = useState('')
  const [size, setSize] = useState('M')
  const [sugarLevel, setSugarLevel] = useState(0)
  const [milkType, setMilkType] = useState('whole')
  const [extraShot, setExtraShot] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loadingMenu, setLoadingMenu] = useState(Boolean(shopId))

  useEffect(() => {
    if (!shopId) return
    apiRequest(`/shops/${shopId}/menu`)
      .then((menu) => {
        const availableProducts = menu.filter((product) => product.is_available)
        setProducts(availableProducts)
        setProductId(availableProducts[0] ? String(availableProducts[0].id) : '')
      })
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoadingMenu(false))
  }, [shopId])

  const displayError =
    error || (!shopId ? 'Sipariş vermek için önce bir dükkân seçin.' : '')

  async function submitOrder(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const order = await apiRequest('/orders', {
        method: 'POST',
        body: {
          shop_id: Number(shopId),
          product_id: Number(productId),
          size,
          sugar_level: Number(sugarLevel),
          milk_type: milkType,
          extra_shot: extraShot,
        },
      })
      navigate(`/qr/${order.order_id}`, { state: { order } })
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="narrow-page">
      <h1>Sipariş oluştur</h1>
      {loadingMenu && <p>Menü yükleniyor…</p>}
      {!loadingMenu && !error && products.length === 0 && (
        <p>Bu dükkânda siparişe açık ürün yok.</p>
      )}
      {products.length > 0 && (
        <form className="form" onSubmit={submitOrder}>
          <label htmlFor="product">Ürün</label>
          <select
            id="product"
            value={productId}
            onChange={(event) => setProductId(event.target.value)}
            required
          >
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name} — {Number(product.price).toFixed(2)} TL
              </option>
            ))}
          </select>

          <label htmlFor="size">Boyut</label>
          <select id="size" value={size} onChange={(event) => setSize(event.target.value)}>
            <option value="S">Küçük</option>
            <option value="M">Orta</option>
            <option value="L">Büyük</option>
          </select>

          <label htmlFor="sugar">Şeker seviyesi</label>
          <select
            id="sugar"
            value={sugarLevel}
            onChange={(event) => setSugarLevel(event.target.value)}
          >
            {[0, 1, 2, 3, 4, 5].map((level) => (
              <option key={level} value={level}>{level}</option>
            ))}
          </select>

          <label htmlFor="milk">Süt tercihi</label>
          <select id="milk" value={milkType} onChange={(event) => setMilkType(event.target.value)}>
            <option value="whole">Normal süt</option>
            <option value="none">Sütsüz</option>
            <option value="lactose_free">Laktozsuz</option>
            <option value="oat">Yulaf</option>
            <option value="almond">Badem</option>
            <option value="soy">Soya</option>
          </select>

          <label className="checkbox-label" htmlFor="extraShot">
            <input
              id="extraShot"
              type="checkbox"
              checked={extraShot}
              onChange={(event) => setExtraShot(event.target.checked)}
            />
            Ekstra shot
          </label>
          <button disabled={busy || !productId} type="submit">
            {busy ? 'Sipariş veriliyor…' : 'Siparişi ver'}
          </button>
        </form>
      )}
      {displayError && <p className="error" role="alert">{displayError}</p>}
    </section>
  )
}

export default OrderPage
