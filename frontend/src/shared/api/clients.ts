// TODO CF.4: migrar funciones fetch a hooks de Orval
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

import type {
  ClientRead,
  ClientCreate,
  ClientUpdate,
} from './generated/model'

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function fetchClients(): Promise<ClientRead[]> {
  const res = await fetch(`${API_BASE}/api/v1/hub/clients`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to fetch clients')
  return res.json()
}

export async function createClient(data: ClientCreate): Promise<ClientRead> {
  const res = await fetch(`${API_BASE}/api/v1/hub/clients`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create client')
  return res.json()
}

export async function updateClient(id: string, data: ClientUpdate): Promise<ClientRead> {
  const res = await fetch(`${API_BASE}/api/v1/hub/clients/${id}`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to update client')
  return res.json()
}

export async function deleteClient(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/hub/clients/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to delete client')
}
