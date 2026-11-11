/** Administration: account requests, pharmacist waitlist (ticket 14), catalog gaps (ticket 15), establishments. */
import { html, render, useEffect, useState } from '../../vendor/preact-htm-standalone.module.js';
import { api } from './api.js';
import { useSessionLock } from './shell.js';
import { Icon, useDebouncedEffect } from './ui.js';

/** Dates arrive as ISO strings or HTTP dates ("Sun, 14 Feb 1988 00:00:00 GMT"). */
const frDate = (value) => {
  if (!value) return '';
  const d = new Date(/^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T00:00:00Z` : value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString('fr-FR', { timeZone: 'UTC' });
};

const TABS = [['demandes', 'Demandes de compte'], ['attente', "Liste d'attente"], ['catalogue', 'Catalogue'], ['etablissements', 'Établissements']];
const STATUS = { pending: ['En attente', 'status-draft'], approved: ['Validé', 'status-issued'], rejected: ['Refusé', 'status-cancelled'] };

function AdminPage() {
  const [tab, setTab] = useState(new URLSearchParams(location.search).get('onglet') || 'demandes');
  const lock = useSessionLock();
  useEffect(() => {
    const url = new URL(location.href); url.searchParams.set('onglet', tab); history.replaceState(null, '', url);
  }, [tab]);
  return html`
    <header class="appbar"><div class="appbar-inner">
      <a class="brand" href="/admin">DigiRemed</a><span class="muted small">Administration</span>
      <span class="spacer"></span><a class="btn btn-ghost btn-sm" href="/deconnexion">Déconnexion</a>
    </div></header>
    <main class="page">
      <h1>Administration</h1>
      <div class="tabs" role="tablist">${TABS.map(([key, label]) => html`
        <button role="tab" key=${key} aria-selected=${tab === key} onClick=${() => setTab(key)}>${label}</button>`)}</div>
      ${tab === 'demandes' && html`<${Requests} />`}
      ${tab === 'attente' && html`<${Waitlist} />`}
      ${tab === 'catalogue' && html`<${Catalog} />`}
      ${tab === 'etablissements' && html`<${Establishments} />`}
    </main>${lock}`;
}

function Requests() {
  const [items, setItems] = useState(null);
  const [selected, setSelected] = useState(null);
  const [notice, setNotice] = useState(null);
  const [error, setError] = useState('');
  const load = () => api('/accounts/requests').then((d) => {
    setItems(d.results);
    setSelected((id) => (d.results.some((r) => r.id === id) ? id : (d.results.find((r) => r.status === 'pending') || d.results[0] || {}).id));
  }).catch((e) => setError(e.message));
  useEffect(() => { load(); const t = setInterval(load, 20000); return () => clearInterval(t); }, []);
  const item = items && items.find((r) => r.id === selected);

  const review = async (action) => {
    if (action === 'reject' && !window.confirm('Refuser cette demande ?')) return;
    try {
      const d = await api(`/accounts/${item.id}/review`, { method: 'POST', body: { action } });
      setNotice({ message: d.message, delivery: d.manual_delivery }); load();
    } catch (e) { setError(e.message); }
  };
  const reset2fa = async () => {
    if (!window.confirm('Réinitialiser la double authentification de ce compte ? Il pourra se connecter avec son seul mot de passe, puis la réactiver.')) return;
    try { await api(`/admin/accounts/${item.id}/2fa/reset`, { method: 'POST' }); setNotice({ message: 'Double authentification réinitialisée. Action tracée dans le journal.' }); }
    catch (e) { setError(e.message); }
  };

  if (!items) return error ? html`<p class="form-error">${error}</p>` : html`<p class="muted">Chargement…</p>`;
  const pending = items.filter((r) => r.status === 'pending').length;
  return html`
    ${error && html`<p class="form-error" role="alert">${error}</p>`}
    ${notice && html`<div class="notice"><span>${notice.message}</span><button class="btn btn-sm btn-ghost" onClick=${() => setNotice(null)}>Fermer</button></div>`}
    ${notice && notice.delivery && html`<section class="card"><h2>Message à transmettre à ${notice.delivery.email}</h2>
      <p>L'email n'a pas pu partir. Transmettez ce message par un autre canal ; le mot de passe temporaire expire dans ${notice.delivery.expires_in_hours || 24} h.</p>
      <textarea class="delivery" readonly rows="8" onFocus=${(e) => e.target.select()}>${notice.delivery.text}</textarea>
      <button class="btn" onClick=${() => navigator.clipboard.writeText(notice.delivery.text)}>Copier le message</button></section>`}
    <p class="muted small">${pending} demande${pending > 1 ? 's' : ''} en attente · actualisation automatique</p>
    ${items.length === 0 ? html`<div class="empty">Aucune demande de compte.</div>` : html`<div class="review-layout">
      <div class="request-list">${items.map((r) => html`<button key=${r.id} class=${`request ${r.id === selected ? 'is-selected' : ''}`} onClick=${() => setSelected(r.id)}>
        <b>${[r.last_name, r.first_name].filter(Boolean).join(' ') || r.email}</b>
        <span class="muted small">${r.profession || ''}</span>
        <span class=${`status ${(STATUS[r.status] || [])[1] || ''}`}>${(STATUS[r.status] || [r.status])[0]}</span></button>`)}</div>
      ${item && html`<article class="card">
        <h2>${[item.last_name, item.first_name].filter(Boolean).join(' ')} <span class=${`status ${(STATUS[item.status] || [])[1] || ''}`}>${(STATUS[item.status] || [item.status])[0]}</span></h2>
        <dl class="facts">${[['Email', item.email], ['Téléphone', item.phone], ['Naissance', frDate(item.birthdate)], ['Profession', item.profession],
          ["N° d'ordre", item.order_number], ['Demandé le', frDate(item.requested_at)]].map(([k, v]) => html`<div key=${k}><dt>${k}</dt><dd>${v || '–'}</dd></div>`)}</dl>
        ${item.status === 'pending' && item.has_identity_document ? html`<p class="group-title">Pièce d'identité</p>
          ${(item.identity_document_mime_type || '').startsWith('image/')
            ? html`<img class="id-doc" src=${`/api/v1/accounts/${item.id}/identity-document`} alt="Pièce d'identité" />`
            : html`<iframe class="id-doc" src=${`/api/v1/accounts/${item.id}/identity-document#toolbar=0`} title="Pièce d'identité"></iframe>`}`
          : html`<p class="muted small">Pièce d'identité supprimée après décision.</p>`}
        <div class="row-end" style="margin-top:16px">
          ${item.status === 'approved' && html`<button class="btn btn-ghost" onClick=${reset2fa}>Réinitialiser la double authentification</button>`}
          ${item.status === 'pending' && html`<button class="btn" onClick=${() => review('reject')}>Refuser</button>
            <button class="btn btn-primary" onClick=${() => review('approve')}>Valider le compte</button>`}
        </div>
      </article>`}
    </div>`}`;
}

function Waitlist() {
  const [items, setItems] = useState(null);
  useEffect(() => { api('/admin/waitlist').then((d) => setItems(d.results)).catch(() => setItems([])); }, []);
  return html`<div class="page-head"><p class="lead">Pharmaciens inscrits pour l'offre officine. La rédaction ne leur est jamais ouverte.</p>
      <a class="btn" href="/api/v1/admin/waitlist.csv">Exporter en CSV</a></div>
    ${items && (items.length === 0 ? html`<div class="empty">Aucun pharmacien en attente.</div>` : html`<div class="table-wrap"><table class="rx-table">
      <thead><tr><th>Nom</th><th>Email</th><th>Téléphone</th><th>N° d'ordre</th><th>Inscrit le</th></tr></thead>
      <tbody>${items.map((r) => html`<tr key=${r.email}><td><b>${[r.last_name, r.first_name].filter(Boolean).join(' ')}</b></td>
        <td>${r.email}</td><td>${r.phone}</td><td>${r.order_number}</td><td>${frDate(r.requested_at)}</td></tr>`)}</tbody></table></div>`)}`;
}

function Catalog() {
  const [gaps, setGaps] = useState(null);
  const [creating, setCreating] = useState(null);
  const [notice, setNotice] = useState('');
  const load = () => api('/admin/catalog/gaps').then((d) => setGaps(d.gaps)).catch(() => setGaps([]));
  useEffect(load, []);
  return html`<p class="lead">Médicaments saisis librement ou cherchés sans résultat par les prescripteurs, les plus fréquents d'abord. Aucune donnée patient.</p>
    ${notice && html`<div class="notice"><span>${notice}</span><button class="btn btn-sm btn-ghost" onClick=${() => setNotice('')}>Fermer</button></div>`}
    ${creating && html`<${CatalogEntryForm} gap=${creating} onCancel=${() => setCreating(null)}
      onDone=${(entry) => { setCreating(null); setNotice(`${entry.name} ajouté au catalogue : il est analysé pour tous les prescripteurs.`); load(); }} />`}
    <div class="row-end" style="margin-bottom:12px">${!creating && html`<button class="btn" onClick=${() => setCreating({ label: '' })}>Ajouter un médicament</button>`}</div>
    ${gaps && (gaps.length === 0 ? html`<div class="empty">Aucun manque relevé.</div>` : html`<div class="table-wrap"><table class="rx-table">
      <thead><tr><th>Saisi ou cherché</th><th>Saisies libres</th><th>Recherches sans résultat</th><th>Dernière fois</th><th></th></tr></thead>
      <tbody>${gaps.map((g) => html`<tr key=${g.key}><td><b>${g.label}</b></td><td>${g.free_text_count}</td><td>${g.search_miss_count}</td>
        <td>${frDate(g.last_seen_at)}</td><td class="actions"><button class="btn btn-sm" onClick=${() => setCreating(g)}>Créer l'entrée</button></td></tr>`)}</tbody>
      </table></div>`)}`;
}

function CatalogEntryForm({ gap, onDone, onCancel }) {
  const [form, setForm] = useState({ name: gap.label, dosage: '', form: '', substances: [] });
  const [q, setQ] = useState('');
  const [found, setFound] = useState([]);
  const [error, setError] = useState('');
  useDebouncedEffect(() => {
    if (q.trim().length < 2) { setFound([]); return; }
    api(`/admin/catalog/substances?q=${encodeURIComponent(q)}`).then((d) => setFound(d.results)).catch(() => {});
  }, [q], 250);
  const add = (s) => { if (!form.substances.includes(s)) setForm({ ...form, substances: [...form.substances, s] }); setQ(''); setFound([]); };
  const submit = async (e) => {
    e.preventDefault(); setError('');
    try { const d = await api('/admin/catalog/entries', { method: 'POST', body: { ...form, resolves: gap.label || form.name } }); onDone(d.entry); }
    catch (err) { setError(err.message); }
  };
  return html`<form class="card" onSubmit=${submit}>
    <h2>Nouvelle entrée du catalogue</h2>
    ${error && html`<p class="form-error" role="alert">${error}</p>`}
    <div class="grid">
      <label class="field c3">Nom<input value=${form.name} onInput=${(e) => setForm({ ...form, name: e.target.value })} /></label>
      <label class="field">Dosage<input value=${form.dosage} placeholder="20 mg/120 mg" onInput=${(e) => setForm({ ...form, dosage: e.target.value })} /></label>
      <label class="field c2">Forme<input value=${form.form} placeholder="comprimé" onInput=${(e) => setForm({ ...form, form: e.target.value })} /></label>
      <div class="field c6">Substances du thésaurus
        <div class="chips">${form.substances.map((s) => html`<span class="chip-filter" key=${s}>${s}
          <button type="button" class="icon-btn" aria-label=${`Retirer ${s}`} onClick=${() => setForm({ ...form, substances: form.substances.filter((x) => x !== s) })}>×</button></span>`)}</div>
        <div class="filter-search"><label class="search search-sm"><${Icon} name="search" />
          <input value=${q} placeholder="Chercher une DCI (au moins 2 lettres)" onInput=${(e) => setQ(e.target.value)} /></label>
          ${found.length > 0 && html`<div class="suggest">${found.map((s) => html`<div class="opt" key=${s} onMouseDown=${(e) => { e.preventDefault(); add(s); }}><b>${s}</b></div>`)}</div>`}</div>
        <span class="hint">Seules les substances du thésaurus ANSM sont acceptées : c'est ce qui rend le médicament analysable.</span>
      </div>
    </div>
    <div class="row-end" style="margin-top:18px"><button class="btn btn-ghost" type="button" onClick=${onCancel}>Annuler</button>
      <button class="btn btn-primary" type="submit" aria-disabled=${!form.name || !form.substances.length}>Ajouter au catalogue</button></div>
  </form>`;
}

function Establishments() {
  const [items, setItems] = useState(null);
  useEffect(() => { api('/admin/establishments').then((d) => setItems(d.results)).catch(() => setItems([])); }, []);
  return items && (items.length === 0 ? html`<div class="empty">Aucun établissement enregistré.</div>` : html`<div class="table-wrap"><table class="rx-table">
    <thead><tr><th>Établissement</th><th>Prescripteur</th><th>Format</th><th>Statut</th></tr></thead>
    <tbody>${items.map((e) => html`<tr key=${e.id}><td><b>${e.name}</b><div class="muted small">${[e.type, e.address].filter(Boolean).join(' · ')}</div></td>
      <td>${[e.prescriber.first_name, e.prescriber.last_name].filter(Boolean).join(' ')}<div class="muted small">${e.prescriber.email}</div></td>
      <td>${e.paper_format || 'A5'}</td><td><span class=${`status ${e.is_active ? 'status-issued' : 'status-cancelled'}`}>${e.is_active ? 'Actif' : 'Inactif'}</span></td></tr>`)}</tbody>
  </table></div>`);
}

render(html`<${AdminPage} />`, document.getElementById('app'));
