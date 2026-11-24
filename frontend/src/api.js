export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

export async function request(path, { method = 'GET', body, signal } = {}) {
  const multipart = body instanceof FormData
  let response
  try {
    response = await fetch(path, {
      method, signal,
      headers: body && !multipart ? { 'Content-Type': 'application/json' } : undefined,
      body: multipart ? body : JSON.stringify(body),
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new ApiError('Could not reach the backend. Check that FastAPI is running.')
  }
  const data = await response.json().catch(() => null)
  if (!response.ok || data === null) {
    const detail = data?.detail
    const message = Array.isArray(detail) ? detail.map(item => item.msg).join('. ') : detail
    throw new ApiError(typeof message === 'string' ? message :
      'The backend could not complete this request (HTTP ' + response.status + '). Check the service and try again.', response.status)
  }
  return data
}

export const knowledgePath = '/api/v1/knowledge'
export const mcpPath = '/api/v1/mcp'

export function readSaved(key) {
  try {
    const value = JSON.parse(localStorage.getItem('omniscience.' + key))
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

export function writeSaved(key, value) {
  try { localStorage.setItem('omniscience.' + key, JSON.stringify(value)) }
  catch { /* The current tab can still hold the session when storage is full or disabled. */ }
}
