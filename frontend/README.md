# KahveCell Frontend

React 19 and Vite application with React Router, Leaflet maps, and a shared
`fetch` API client for the FastAPI backend.

## Run on Windows

Open PowerShell in this folder and run:

```powershell
npm install
npm run dev
```

Open the address printed by Vite, usually `http://localhost:5173`.

The backend should be running at `http://localhost:8000`. The default API URL
is `http://localhost:8000/api/v1`; to change it, copy `.env.example` to
`.env.local`, edit `VITE_API_BASE_URL`, and restart Vite.

## Main folders

- `src/api/`: shared requests and API error handling.
- `src/components/`: reusable layout and map components.
- `src/pages/`: phone/password login, OTP-verified registration, welcome, shop,
  order, QR, history, and subscription screens.
