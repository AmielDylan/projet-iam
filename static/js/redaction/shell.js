/** Shared pieces of the prescriber pages: top bar, status badge, ordonnance table. */
import { html, useEffect, useRef, useState } from '../../vendor/preact-htm-standalone.module.js';
import { Api, onSessionLocked } from './api.js';
import { Icon, ageLabel, frDate } from './ui.js';

export function AppBar({ current }) {
  return html`<header class="appbar"><div class="appbar-inner">
    <a class="brand" href="/ordonnances">DigiRemed</a>
    <nav class="appnav" aria-label="Navigation principale">
      <a href="/ordonnances" aria-current=${current === 'ordonnances' ? 'page' : undefined}>Ordonnances</a>
      <a href="/interactions" aria-current=${current === 'interactions' ? 'page' : undefined}>Interactions</a>
      <a href="/etablissements" aria-current=${current === 'etablissements' ? 'page' : undefined}>Établissements</a>
      <a href="/reglages" aria-current=${current === 'reglages' ? 'page' : undefined}>Réglages</a>
    </nav>
    <span class="spacer"></span>
    <a class="btn btn-ghost btn-sm" href="/deconnexion">Déconnexion</a>
  </div></header>`;
}

export function Footer() {
  return html`<footer class="site-foot"><div class="site-foot-inner">
    <span><b>DigiRemed</b> · Aide à la prescription</span>
    <span>Analyse fondée sur le thésaurus des interactions médicamenteuses de l'ANSM. Elle ne remplace pas le jugement du prescripteur.</span>
  </div></footer>`;
}

const STATUS = {
  draft: ['Brouillon', 'status-draft'],
  issued: ['Émise', 'status-issued'],
  cancelled: ['Annulée', 'status-cancelled'],
};

export function StatusBadge({ status }) {
  const [label, cls] = STATUS[status] || [status, ''];
  return html`<span class=${`status ${cls}`}>${label}</span>`;
}

export const patientName = (p) => (p ? [p.first_name, p.last_name].filter(Boolean).join(' ') : '');

/** Rows of ordonnances with their actions. `onChanged` reloads the list after an action. */
export function OrdonnanceTable({ items, showPatient = true, onChanged, onError }) {
  const discard = async (item) => {
    if (!window.confirm('Supprimer ce brouillon ? Il ne pourra pas être récupéré.')) return;
    try { await Api.discard(item.id); onChanged(); } catch (error) { onError(error.message); }
  };
  const renew = async (item) => {
    const cancelled = item.status === 'cancelled';
    if (cancelled && !window.confirm('Cette ordonnance a été annulée. La reconduire quand même ?')) return;
    try {
      const data = await Api.renew(item.id, cancelled);
      location.href = `/ordonnances/${data.ordonnance.id}/rediger?etape=2`;
    } catch (error) { onError(error.message); }
  };
  const meds = (list) => (list.length > 3 ? `${list.slice(0, 3).join(', ')} et ${list.length - 3} autre${list.length > 4 ? 's' : ''}` : list.join(', '));

  return html`<div class="table-wrap"><table class="rx-table">
    <thead><tr><th>Date</th><th>Statut</th>${showPatient && html`<th>Patient</th>`}<th>Médicaments</th><th><span class="sr">Actions</span></th></tr></thead>
    <tbody>${items.map((item) => html`<tr key=${item.id}>
      <td class="nowrap">${frDate(item.issued_at || item.updated_at)}</td>
      <td><${StatusBadge} status=${item.status} />${item.number && html`<div class="muted small nowrap">${item.number}</div>`}</td>
      ${showPatient && html`<td>${item.patient_id
        ? html`<a href=${`/patients/${item.patient_id}`}>${patientName(item.patient) || 'Patient'}</a>
          ${item.patient && item.patient.birthdate && html`<div class="muted small">${ageLabel(item.patient.birthdate)}</div>`}`
        : html`<span class="muted">Non renseigné</span>`}</td>`}
      <td>${item.medications.length ? meds(item.medications) : html`<span class="muted">Aucun médicament</span>`}
        ${item.origin_id && html`<div class="muted small">Reconduction</div>`}</td>
      <td class="actions">
        <a class="btn btn-sm" href=${`/ordonnances/${item.id}/rediger`}>${item.status === 'draft' ? 'Reprendre' : 'Consulter'}</a>
        ${item.status !== 'draft' && html`<button class="btn btn-sm btn-ghost" onClick=${() => renew(item)}>Reconduire</button>`}
        ${item.status === 'draft' && html`<button class="icon-btn" aria-label="Supprimer le brouillon" title="Supprimer" onClick=${() => discard(item)}><${Icon} name="trash" /></button>`}
      </td>
    </tr>`)}</tbody>
  </table></div>`;
}

export function Pager({ page, pages, onPage }) {
  if (pages <= 1) return null;
  return html`<nav class="pager" aria-label="Pages">
    <button class="btn btn-sm" aria-disabled=${page <= 1} onClick=${() => page > 1 && onPage(page - 1)}><${Icon} name="left" />Précédentes</button>
    <span class="muted small">Page ${page} sur ${pages}</span>
    <button class="btn btn-sm" aria-disabled=${page >= pages} onClick=${() => page < pages && onPage(page + 1)}>Suivantes<${Icon} name="right" /></button>
  </nav>`;
}

/** Password screen shown when the server locks an idle session; resolves once unlocked. */
export function useSessionLock(idleMinutes = 10) {
  const [locked, setLocked] = useState(null);
  // The server locks the session after 10 idle minutes; mask the screen at the same time (ticket 17).
  useEffect(() => onSessionLocked(() => new Promise((resolve) => setLocked({ resolve }))), []);
  useEffect(() => {
    let timer;
    const reset = () => {
      clearTimeout(timer);
      timer = setTimeout(() => setLocked((current) => current || { resolve: () => {} }), idleMinutes * 60 * 1000);
    };
    const events = ['keydown', 'mousedown', 'touchstart', 'wheel'];
    events.forEach((name) => window.addEventListener(name, reset, { passive: true }));
    reset();
    return () => { clearTimeout(timer); events.forEach((name) => window.removeEventListener(name, reset)); };
  }, []);
  return locked && html`<${LockScreen} onUnlocked=${() => { locked.resolve(); setLocked(null); }} />`;
}

export function LockScreen({ onUnlocked }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const input = useRef(null);
  useEffect(() => { if (input.current) input.current.focus(); }, []);
  const submit = async (e) => {
    e.preventDefault();
    try { await Api.unlock(password); onUnlocked(); } catch (err) { setError(err.message); }
  };
  return html`<div class="lock" role="dialog" aria-modal="true" aria-labelledby="lock-title">
    <form class="lock-card" onSubmit=${submit}>
      <${Icon} name="lock" /><h2 id="lock-title">Session verrouillée</h2>
      <p>Après 10 minutes d'inactivité, les données patient sont masquées. Votre travail est intact.</p>
      <label class="field">Mot de passe<input ref=${input} type="password" value=${password} onInput=${(e) => setPassword(e.target.value)} /></label>
      ${error && html`<p class="form-error">${error}</p>`}
      <div class="row"><a class="btn btn-ghost" href="/deconnexion">Changer d'utilisateur</a><button class="btn btn-primary" type="submit">Déverrouiller</button></div>
    </form></div>`;
}
