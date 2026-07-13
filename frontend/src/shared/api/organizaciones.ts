// TODO CF.4: migrar funciones fetch a hooks de Orval
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

import type {
  OrganizacionRead,
  OrganizacionCreate,
  OrganizacionUpdate,
} from './generated/model'

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function fetchOrganizaciones(): Promise<OrganizacionRead[]> {
  const res = await fetch(`${API_BASE}/api/v1/hub/organizaciones`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to fetch organizaciones')
  return res.json()
}

export async function createOrganizacion(data: OrganizacionCreate): Promise<OrganizacionRead> {
  const res = await fetch(`${API_BASE}/api/v1/hub/organizaciones`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create organizacion')
  return res.json()
}

export async function updateOrganizacion(id: string, data: OrganizacionUpdate): Promise<OrganizacionRead> {
  const res = await fetch(`${API_BASE}/api/v1/hub/organizaciones/${id}`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to update organizacion')
  return res.json()
}

export async function deleteOrganizacion(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/hub/organizaciones/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to delete organizacion')
}
