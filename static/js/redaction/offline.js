/**
 * Offline copy of a draft (ticket 16).
 *
 * When the network drops, the draft is kept on this device, encrypted with AES-GCM under a key
 * that lives in the server session: logging out (or another account logging in) makes every copy
 * unreadable, and copies are deleted at logout anyway. Copies expire after 24 hours and are
 * removed as soon as the server has the draft.
 */
const PREFIX = 'rx-offline:';
const TTL_MS = 24 * 3600 * 1000;

const storage = () => { try { return window.localStorage; } catch { return null; } };
const b64 = (bytes) => btoa(String.fromCharCode(...new Uint8Array(bytes)));
const unb64 = (text) => Uint8Array.from(atob(text), (c) => c.charCodeAt(0));

async function importKey(secret) {
  const raw = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(secret));
  return crypto.subtle.importKey('raw', raw, 'AES-GCM', false, ['encrypt', 'decrypt']);
}

export function offlineStore(secret, ordonnanceId) {
  const name = `${PREFIX}${ordonnanceId}`;
  const keyPromise = secret && window.crypto && crypto.subtle ? importKey(secret) : null;
  return {
    /** Keep `payload` ({content, basedOn}) on this device, encrypted. */
    async save(payload) {
      const store = storage();
      if (!store || !keyPromise) return false;
      const iv = crypto.getRandomValues(new Uint8Array(12));
      const data = new TextEncoder().encode(JSON.stringify(payload));
      const sealed = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, await keyPromise, data);
      store.setItem(name, JSON.stringify({ at: Date.now(), iv: b64(iv), data: b64(sealed) }));
      return true;
    },
    /** The kept copy, or null when absent, expired or sealed by another session. */
    async load() {
      const store = storage();
      const entry = store && store.getItem(name);
      if (!entry || !keyPromise) return null;
      try {
        const { at, iv, data } = JSON.parse(entry);
        if (Date.now() - at > TTL_MS) { store.removeItem(name); return null; }
        const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: unb64(iv) }, await keyPromise, unb64(data));
        return { ...JSON.parse(new TextDecoder().decode(plain)), at };
      } catch {
        store.removeItem(name); // another session's key: never readable here
        return null;
      }
    },
    clear() { const store = storage(); if (store) store.removeItem(name); },
  };
}

/** Delete expired copies; called on every page of the workspace. */
export function purgeExpired() {
  const store = storage();
  if (!store) return;
  for (let i = store.length - 1; i >= 0; i -= 1) {
    const name = store.key(i);
    if (!name || !name.startsWith(PREFIX)) continue;
    try { if (Date.now() - JSON.parse(store.getItem(name)).at > TTL_MS) store.removeItem(name); } catch { store.removeItem(name); }
  }
}

/** Delete every copy on this device (logout). */
export function clearAll() {
  const store = storage();
  if (!store) return;
  for (let i = store.length - 1; i >= 0; i -= 1) {
    const name = store.key(i);
    if (name && name.startsWith(PREFIX)) store.removeItem(name);
  }
}
