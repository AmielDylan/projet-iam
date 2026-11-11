/** Patient sheet (ticket 06): clinical data and history of ordonnances. */
import { html, render, useEffect, useState } from '../../vendor/preact-htm-standalone.module.js';
import { Api } from './api.js';
import { AppBar, Footer, OrdonnanceTable, Pager, patientName, useSessionLock } from './shell.js';
import { ageLabel, ageYears, frDate } from './ui.js';

const PREGNANCY = { pregnant: 'Enceinte', breastfeeding: 'Allaitement', none: 'Non concernée' };

function PatientPage({ initial }) {
  const p = initial.patient;
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const lock = useSessionLock();
  const load = () => Api.patientHistory(p.id, page).then((d) => { setData(d); setError(''); }).catch((e) => setError(e.message));
  useEffect(load, [page]);

  const years = ageYears(p.birthdate);
  const facts = [
    ['Date de naissance', p.birthdate ? `${frDate(p.birthdate)} (${ageLabel(p.birthdate)})` : ''],
    ['Sexe', p.sex === 'F' ? 'Féminin' : p.sex === 'M' ? 'Masculin' : ''],
    ['Poids', p.weight_kg ? `${String(p.weight_kg).replace('.', ',')} kg${p.weighed_on ? `, pesé le ${frDate(p.weighed_on)}` : ''}` : ''],
    ['Grossesse ou allaitement', PREGNANCY[p.pregnancy] || ''],
    ['Allergies déclarées', (p.allergies || []).join(', ') || 'Aucune déclarée'],
  ];

  return html`
    <${AppBar} current="ordonnances" />
    <main class="page">
      <p class="small"><a href="/ordonnances">Ordonnances</a> / Patient</p>
      <div class="page-head">
        <div><h1>${[p.title, patientName(p)].filter(Boolean).join(' ')}</h1>
          ${years !== null && years < 15 && html`<p class="lead">Enfant : le poids daté est exigé à chaque ordonnance.</p>`}</div>
        <a class="btn btn-primary" href=${`/ordonnances/nouvelle?patient=${p.id}`}>Nouvelle ordonnance pour ce patient</a>
      </div>
      <dl class="facts">${facts.map(([label, value]) => html`
        <div key=${label}><dt>${label}</dt><dd>${value || html`<span class="muted">Non renseigné</span>`}</dd></div>`)}</dl>
      <p class="muted small">Ces informations se corrigent à l'étape Patient d'une ordonnance ; la correction garde l'historique.</p>

      <p class="group-title">Historique des ordonnances</p>
      ${error && html`<p class="form-error" role="alert">${error}</p>`}
      ${data && data.items.length > 0 && html`
        <${OrdonnanceTable} items=${data.items} showPatient=${false} onChanged=${load} onError=${setError} />
        <${Pager} page=${data.page} pages=${data.pages} onPage=${setPage} />`}
      ${data && data.items.length === 0 && html`<div class="empty">Aucune ordonnance pour ce patient.</div>`}
    </main>
    <${Footer} />${lock}`;
}

const initial = JSON.parse(document.getElementById('initial-data').textContent);
render(html`<${PatientPage} initial=${initial} />`, document.getElementById('app'));
