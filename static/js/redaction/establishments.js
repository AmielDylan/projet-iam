/** Establishments: header, logo and paper format of the ordonnances. */
import { html, render, useEffect, useState } from '../../vendor/preact-htm-standalone.module.js';
import { ApiError, api } from './api.js';
import { AppBar, useSessionLock } from './shell.js';
import { Icon } from './ui.js';

const EMPTY = { name: '', type: '', address: '', phone: '', email: '', identifier_label: '', identifier_value: '',
  secondary_identifier_label: '', secondary_identifier_value: '', free_text: '', paper_format: 'A5' };

function EstablishmentsPage() {
  const [items, setItems] = useState(null);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState('');
  const lock = useSessionLock();
  const load = () => api('/prescriber/establishments').then((d) => setItems(d.results)).catch((e) => setError(e.message));
  useEffect(load, []);

  const deactivate = async (item) => {
    if (!window.confirm(`Désactiver « ${item.name} » ? Les ordonnances déjà émises gardent leur en-tête.`)) return;
    try { await api(`/prescriber/establishments/${item.id}`, { method: 'DELETE' }); load(); } catch (e) { setError(e.message); }
  };

  return html`
    <${AppBar} current="etablissements" />
    <main class="page">
      <div class="page-head">
        <div><h1>Établissements</h1><p class="lead">Le lieu d'exercice choisi sur une ordonnance fournit son en-tête, son logo et son format de papier.</p></div>
        ${!editing && html`<button class="btn btn-primary" onClick=${() => setEditing({ ...EMPTY })}>Ajouter un établissement</button>`}
      </div>
      ${error && html`<p class="form-error" role="alert">${error}</p>`}
      ${editing && html`<${EstablishmentForm} initial=${editing} onDone=${() => { setEditing(null); load(); }} onCancel=${() => setEditing(null)} />`}
      ${items && items.length === 0 && !editing && html`<div class="empty">Aucun établissement : ajoutez celui qui figurera en en-tête de vos ordonnances.</div>`}
      ${items && items.length > 0 && html`<div class="est-list">${items.map((item) => html`
        <article class=${`card est ${item.is_active ? '' : 'is-off'}`} key=${item.id}>
          ${item.has_logo ? html`<img class="est-logo" src=${`/api/v1/prescriber/establishments/${item.id}/logo`} alt="" />`
            : html`<span class="est-logo est-logo-empty">Logo</span>`}
          <div class="est-body">
            <h2>${item.name} <span class="status status-draft">${item.paper_format || 'A5'}</span>
              ${!item.is_active && html`<span class="status status-cancelled">Désactivé</span>`}</h2>
            <p>${[item.type, item.address, item.phone].filter(Boolean).join(' · ') || html`<span class="muted">Coordonnées à compléter</span>`}</p>
          </div>
          <div class="est-actions">
            <button class="btn btn-sm" onClick=${() => setEditing({ ...EMPTY, ...item })}><${Icon} name="pencil" />Modifier</button>
            ${item.is_active && html`<button class="btn btn-sm btn-ghost" onClick=${() => deactivate(item)}>Désactiver</button>`}
          </div>
        </article>`)}</div>`}
    </main>${lock}`;
}

function EstablishmentForm({ initial, onDone, onCancel }) {
  const [form, setForm] = useState(initial);
  const [logo, setLogo] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (name) => (e) => setForm({ ...form, [name]: e.target.value });
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('');
    const body = new FormData();
    Object.keys(EMPTY).forEach((k) => body.append(k, form[k] || ''));
    body.append('is_active', '1');
    if (logo) body.append('logo', logo);
    const url = form.id ? `/api/v1/prescriber/establishments/${form.id}` : '/api/v1/prescriber/establishments';
    try {
      const response = await fetch(url, { method: 'POST', body, credentials: 'same-origin' });
      const data = await response.json();
      if (!response.ok) throw new ApiError(response.status, { error: data.message || data.error });
      onDone();
    } catch (err) { setError(err.message); setBusy(false); }
  };
  const field = (name, label, span, extra = {}) => html`<label class=${`field ${span}`}>${label}
    <input value=${form[name] || ''} onInput=${set(name)} ...${extra} /></label>`;
  return html`<form class="card" onSubmit=${submit}>
    <h2>${form.id ? `Modifier « ${initial.name} »` : 'Nouvel établissement'}</h2>
    ${error && html`<p class="form-error" role="alert">${error}</p>`}
    <div class="grid">
      ${field('name', 'Nom', 'c4', { required: true })}
      <div class="field c2"><span id="pf">Format de papier</span><div class="seg" role="radiogroup" aria-labelledby="pf">
        ${['A5', 'A4'].map((f) => html`<label key=${f}><input type="radio" name="paper" checked=${(form.paper_format || 'A5') === f}
          onChange=${() => setForm({ ...form, paper_format: f })} />${f}</label>`)}</div></div>
      ${field('type', 'Type', 'c3', { placeholder: 'Cabinet, clinique, centre de santé…' })}
      ${field('phone', 'Téléphone', 'c3')}
      <label class="field c6">Adresse<textarea rows="2" value=${form.address || ''} onInput=${set('address')}></textarea></label>
      ${field('email', 'Email', 'c2')}${field('identifier_label', 'Libellé identifiant', 'c2', { placeholder: 'IFU, agrément…' })}${field('identifier_value', 'Identifiant', 'c2')}
      <label class="field c6">Mention libre en en-tête<input value=${form.free_text || ''} onInput=${set('free_text')} placeholder="Horaires, spécialités…" /></label>
      <label class="field c6">Logo (JPG ou PNG, 1 Mo au plus)<input type="file" accept="image/png,image/jpeg" onChange=${(e) => setLogo(e.target.files[0] || null)} />
        ${form.has_logo && html`<span class="hint">Un logo est déjà enregistré ; un nouveau fichier le remplace.</span>`}</label>
    </div>
    <div class="row-end" style="margin-top:18px"><button class="btn btn-ghost" type="button" onClick=${onCancel}>Annuler</button>
      <button class="btn btn-primary" type="submit" aria-disabled=${busy}>Enregistrer</button></div>
  </form>`;
}

render(html`<${EstablishmentsPage} />`, document.getElementById('app'));
