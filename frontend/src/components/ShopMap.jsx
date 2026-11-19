import { useEffect } from 'react'
import L from 'leaflet'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import markerIcon from 'leaflet/dist/images/marker-icon.png?url'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png?url'
import markerShadow from 'leaflet/dist/images/marker-shadow.png?url'
import { Link } from 'react-router-dom'

const shopIcon = new L.Icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

function FitShops({ shops }) {
  const map = useMap()

  useEffect(() => {
    if (shops.length === 1) {
      map.setView([shops[0].latitude, shops[0].longitude], 13)
    } else if (shops.length > 1) {
      const bounds = L.latLngBounds(
        shops.map((shop) => [shop.latitude, shop.longitude]),
      )
      map.fitBounds(bounds, { padding: [32, 32], maxZoom: 13 })
    }
  }, [map, shops])

  return null
}

function ShopMap({ shops }) {
  return (
    <MapContainer
      className="shop-map"
      center={[39.9208, 32.8541]}
      zoom={12}
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitShops shops={shops} />
      {shops.map((shop) => (
        <Marker
          key={shop.id}
          position={[shop.latitude, shop.longitude]}
          icon={shopIcon}
        >
          <Popup>
            <strong>{shop.name}</strong>
            <br />
            <Link to={`/shops/${shop.id}`}>Dükkânı görüntüle</Link>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}

export default ShopMap
