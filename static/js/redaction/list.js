/** Ordonnances page (ticket 06): drafts and issued ordonnances, filters, pagination. */
import { html, render, useEffect, useState } from '../../vendor/preact-htm-standalone.module.js';
import { Api } from './api.js';
import { AppBar, Footer, OrdonnanceTable, Pager, patientName, useSessionLock } from './shell.js';
import { Icon, useDebouncedEffect } from './ui.js';

const FILTERS = [['', 'Toutes'], ['draft', 'Brouillons'], ['issued', 'Émises'], ['cancelled', 'Annulées']];

function ListPage() {
  const params = new URLSearchParams(location.search);
  const [status, setStatus] = useState(params.get('statut') || '');
  const [patient, setPatient] = useState(null);
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const lock = useSessionLock();

  const load = () => {
    const query = { page };
    if (status) query.status = status;
    if (patient) query.patient_id = patient.id;
    Api.list(query).then((d) => { setData(d); setError(''); }).catch((e) => setError(e.message));
  };
  useEffect(load, [status, patient, page]);
  useEffect(() => {
    const url = new URL(location.href);
    if (status) url.searchParams.set('statut', status); else url.searchParams.delete('statut');
    history.replaceState(null, '', url);
  }, [status]);

  const filtered = status || patient;
  return html`
    <${AppBar} current="ordonnances" />
    <main class="page">
      <div class="page-head">
        <div><h1>Ordonnances</h1><p class="lead">Brouillons et ordonnances émises, les plus récentes d'abord.</p></div>
        <a class="btn btn-primary" href="/ordonnances/nouvelle">Nouvelle ordonnance</a>
      </div>
      <div class="toolbar">
        <div class="seg seg-inline" role="group" aria-label="Statut">${FILTERS.map(([value, label]) => html`
          <button key=${value} aria-pressed=${status === value} onClick=${() => { setStatus(value); setPage(1); }}>${label}</button>`)}</div>
        <${PatientFilter} patient=${patient} onChange=${(p) => { setPatient(p); setPage(1); }} />
      </div>
      ${error && html`<p class="form-error" role="alert">${error}</p>`}
      ${data && data.items.length > 0 && html`
        <${OrdonnanceTable} items=${data.items} onChanged=${load} onError=${setError} />
        <${Pager} page=${data.page} pages=${data.pages} onPage=${setPage} />
        <p class="muted small">${data.total} ordonnance${data.total > 1 ? 's' : ''}</p>`}
      ${data && data.items.length === 0 && (filtered
        ? html`<div class="empty">Aucune ordonnance ne correspond à ces filtres.</div>`
        : html`<div class="empty-state">
            <h2>Votre première ordonnance</h2>
            <p>Choisissez le patient, ajoutez les médicaments au clavier : l'analyse des interactions se fait pendant la saisie, et le brouillon s'enregistre tout seul.</p>
            <a class="btn btn-primary" href="/ordonnances/nouvelle">Nouvelle ordonnance</a>
            <p class="muted small">Pensez à renseigner <a href="/etablissements">votre établissement</a> : il figure en en-tête de l'ordonnance.</p>
          </div>`)}
      ${!data && !error && html`<p class="muted">Chargement…</p>`}
    </main>
    <${Footer} />${lock}`;
}

function PatientFilter({ patient, onChange }) {
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  useDebouncedEffect(() => {
    if (q.trim().length < 2) { setResults([]); return; }
    Api.searchPatients(q).then((d) => setResults(d.results)).catch(() => {});
  }, [q], 250);

  if (patient) {
    return html`<span class="chip-filter">Patient : <b>${patientName(patient)}</b>
      <button class="icon-btn" aria-label="Retirer le filtre patient" onClick=${() => onChange(null)}>×</button></span>`;
  }
  return html`<div class="filter-search">
    <label class="search search-sm"><${Icon} name="search" /><span class="sr">Filtrer par patient</span>
      <input value=${q} placeholder="Filtrer par patient" onInput=${(e) => setQ(e.target.value)} autocomplete="off" /></label>
    ${results.length > 0 && html`<div class="suggest">${results.map((p) => html`
      <div class="opt" key=${p.id} onMouseDown=${(e) => { e.preventDefault(); setQ(''); setResults([]); onChange(p); }}>
        <b>${patientName(p)}</b></div>`)}</div>`}
  </div>`;
}

render(html`<${ListPage} />`, document.getElementById('app'));
