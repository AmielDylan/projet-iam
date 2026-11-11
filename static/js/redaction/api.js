/**
 * API client for the prescriber workspace.
 * Every error carries `status`, `code` and a French `message` ready to show.
 * A locked session (423) waits for the lock screen, then the call is retried.
 */
export class ApiError extends Error {
  constructor(status, body) {
    super((body && body.error) || 'Erreur réseau');
    this.status = status;
    this.code = (body && body.code) || (status === 0 ? 'network' : 'error');
    this.body = body || {};
  }
}

let unlockHandler = null;
/** The app registers how to ask for the password when the session locks. */
export function onSessionLocked(handler) { unlockHandler = handler; }

export async function api(path, { method = 'GET', body } = {}) {
  let response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
      credentials: 'same-origin',
    });
  } catch {
    throw new ApiError(0, { error: 'Connexion au serveur impossible' });
  }
  const data = await response.json().catch(() => ({}));
  if (response.ok) return data;

  if (response.status === 423 && unlockHandler) {
    await unlockHandler();
    return api(path, { method, body });
  }
  if (response.status === 401 && data.code !== 'wrong_password' && data.code !== 'wrong_code') {
    window.location.href = `/connexion?next=${encodeURIComponent(location.pathname)}`;
  }
  throw new ApiError(response.status, data);
}

export const Api = {
  ordonnance: (id) => api(`/ordonnances/${id}`),
  save: (id, version, content) => api(`/ordonnances/${id}`, { method: 'PUT', body: { version, content } }),
  check: (id) => api(`/ordonnances/${id}/check`),
  issue: (id, version) => api(`/ordonnances/${id}/issue`, { method: 'POST', body: { version } }),
  cancelReasons: () => api('/ordonnances/cancel-reasons'),
  cancelAndCorrect: (id, reason) => api(`/ordonnances/${id}/cancel-and-correct`, { method: 'POST', body: { reason } }),
  analyze: (lines, patientId, derogations) =>
    api('/prescriptions/analyze', { method: 'POST', body: { lines, patient_id: patientId, derogations } }),
  searchMedications: (q, patientId) =>
    api(`/medications/search?q=${encodeURIComponent(q)}&limit=8${patientId ? `&patient_id=${patientId}` : ''}`),
  searchPatients: (q) => api(`/patients?q=${encodeURIComponent(q)}`),
  createPatient: (data) => api('/patients', { method: 'POST', body: data }),
  updatePatient: (id, data) => api(`/patients/${id}`, { method: 'PUT', body: data }),
  unlock: (password) => api('/auth/unlock', { method: 'POST', body: { password } }),
};
