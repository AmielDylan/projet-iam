/** Shared helpers and small components for the prescriber workspace. */
import { html, useEffect, useRef } from '../../vendor/preact-htm-standalone.module.js';

const PATHS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  trash: '<path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  'check-circle': '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
  alert: '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17.5v.01"/>',
  ban: '<circle cx="12" cy="12" r="9"/><path d="m5.6 5.6 12.8 12.8"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/>',
  left: '<path d="m15 18-6-6 6-6"/>',
  right: '<path d="m9 18 6-6-6-6"/>',
  printer: '<path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v7H6z"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>',
  pencil: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>',
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
};

export function Icon({ name }) {
  return html`<svg class="i" viewBox="0 0 24 24" aria-hidden="true" dangerouslySetInnerHTML=${{ __html: PATHS[name] || '' }}></svg>`;
}

/** ISO date (YYYY-MM-DD) to French display (JJ/MM/AAAA). */
export function frDate(iso) {
  if (!iso) return '';
  const [y, m, d] = String(iso).slice(0, 10).split('-');
  return d ? `${d}/${m}/${y}` : iso;
}

export function todayIso() {
  // Benin time (UTC+1, no daylight saving), like the server.
  return new Date(Date.now() + 3600 * 1000).toISOString().slice(0, 10);
}

/** Age label as printed: months before 2 years, years after. */
export function ageLabel(birthIso, onIso = todayIso()) {
  if (!birthIso) return '';
  const [by, bm, bd] = birthIso.split('-').map(Number);
  const [y, m, d] = onIso.split('-').map(Number);
  const months = (y - by) * 12 + (m - bm) - (d < bd ? 1 : 0);
  if (months < 0) return '';
  return months < 24 ? `${months} mois` : `${Math.floor(months / 12)} ans`;
}

export function ageYears(birthIso) {
  const label = ageLabel(birthIso);
  if (!label) return null;
  return label.endsWith('mois') ? Math.floor(parseInt(label, 10) / 12) : parseInt(label, 10);
}

export function newLineId() {
  return Math.random().toString(36).slice(2, 10);
}

/** Run `fn` once `deps` stop changing for `delay` ms. */
export function useDebouncedEffect(fn, deps, delay) {
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return undefined; }
    const timer = setTimeout(fn, delay);
    return () => clearTimeout(timer);
  }, deps);
}

/** Requirement of an alert to its visual class. */
export const kindOf = (alert) => (
  alert.requirement === 'blocking' ? 'ci' : alert.requirement === 'justify' ? 'justify' : 'info'
);

export function alertTag(alert) {
  if (alert.type === 'same_substance') return 'Même DCI';
  if (alert.type === 'allergy') return 'Allergie';
  return alert.level || 'Interaction';
}

export function alertTitle(alert) {
  if (alert.type === 'same_substance') return 'Doublon de substance';
  if (alert.type === 'allergy') return 'Allergie déclarée';
  return {
    CI: 'Contre-indication', ASDEC: 'Association déconseillée',
    PE: "Précaution d'emploi", APEC: 'À prendre en compte',
  }[alert.level] || 'Interaction';
}
