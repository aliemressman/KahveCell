const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
).replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, statusCode) {
    super(message)
    this.name = 'ApiError'
    this.statusCode = statusCode
  }
}

export async function apiRequest(
  path,
  { method = 'GET', body, auth = true } = {},
) {
  const headers = {}
  const token = localStorage.getItem('kahvecell.accessToken')

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (auth && token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  })

  if (response.status === 204) {
    return null
  }

  const data = await response.json()
  if (!response.ok) {
    const message = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join(', ')
      : data.detail || 'İstek tamamlanamadı.'
    throw new ApiError(message, response.status)
  }

  return data
}
