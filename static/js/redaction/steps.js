/** The three steps of the prescribing flow: patient, treatment, verification. */
import { html, useEffect, useRef, useState } from '../../vendor/preact-htm-standalone.module.js';
import { Api } from './api.js';
import { DateInput, Icon, ageLabel, ageYears, alertTag, alertTitle, frDate, kindOf, useDebouncedEffect } from './ui.js';

const lineLabel = (content, id) => {
  const index = content.lines.findIndex((line) => line.line_id === id);
  return index < 0 ? '' : `${index + 1}. ${content.lines[index].name}`;
};
const linesLabel = (content, ids) => ids.map((id) => lineLabel(content, id)).filter(Boolean).join(' + ');

/* ================================ Patient ================================ */

function PatientSearch({ onPick, onNew }) {
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);
  const [recent, setRecent] = useState([]);
  const input = useRef(null);
  useEffect(() => {
    if (input.current) input.current.focus();
    Api.recentPatients().then((data) => setRecent(data.results)).catch(() => {});
  }, []);
  useDebouncedEffect(() => {
    if (q.trim().length < 2) { setResults([]); setSearched(false); return; }
    Api.searchPatients(q).then((data) => { setResults(data.results); setSearched(true); }).catch(() => {});
  }, [q], 250);

  return html`
    <div class="composer">
      <label class="search"><${Icon} name="search" /><span class="sr">Rechercher un patient</span>
        <input ref=${input} value=${q} onInput=${(e) => setQ(e.target.value)} placeholder="Nom, prénom ou date de naissance" autocomplete="off" /></label>
    </div>
    ${!q.trim() && recent.length > 0 && html`<p class="group-title">Patients récents</p>`}
    ${(q.trim() ? results : recent).length > 0 && html`<div class="picklist">${(q.trim() ? results : recent).map((p) => html`
      <button class="pick" key=${p.id} onClick=${() => onPick(p)}>
        <span class="avatar">${(p.first_name || ' ')[0]}${(p.last_name || ' ')[0]}</span>
        <span><b>${[p.title, p.first_name, p.last_name].filter(Boolean).join(' ')}</b>
          <small>${p.birthdate ? `Né(e) le ${frDate(p.birthdate)} · ${ageLabel(p.birthdate)}` : 'Date de naissance non renseignée'}</small></span>
      </button>`)}</div>`}
    ${searched && !results.length && html`<p class="muted">Aucun patient trouvé pour « ${q} ».</p>`}
    <button class="btn btn-soft" onClick=${() => onNew(q)}>Nouveau patient</button>`;
}

export function PatientStep({ content, patient, form, onField, onPick, onNew, onChange, saving, error,
  establishments, onContentField }) {
  if (!content.patient_id && !form) {
    return html`<h1>Patient</h1>
      <p class="lead">Retrouvez le patient par son nom ou sa date de naissance, ou créez-le.</p>
      <${PatientSearch} onPick=${onPick} onNew=${onNew} />`;
  }
  const f = form || {};
  const years = ageYears(f.birthdate_iso);
  const child = years !== null && years < 15;
  return html`
    <h1>Patient</h1>
    <p class="lead">Ces informations s'impriment sur l'ordonnance et servent à l'analyse. Avant 15 ans, le poids daté est obligatoire.</p>
    ${patient && html`<div class="patient-pick"><span class="avatar">${(patient.first_name || ' ')[0]}${(patient.last_name || ' ')[0]}</span>
      <div style="flex:1"><b>${[patient.title, patient.first_name, patient.last_name].filter(Boolean).join(' ')}</b>
        <small>${patient.birthdate ? `Né(e) le ${frDate(patient.birthdate)}` : ''}</small></div>
      <button class="btn btn-sm btn-ghost" onClick=${onChange}>Changer de patient</button></div>`}
    ${error && html`<p class="form-error" role="alert">${error}</p>`}
    <div class="grid">
      <label class="field c2">Nom<input value=${f.last_name} onInput=${(e) => onField('last_name', e.target.value)} /></label>
      <label class="field c2">Prénom<input value=${f.first_name} onInput=${(e) => onField('first_name', e.target.value)} /></label>
      <div class="field c2"><span id="sex-l">Sexe</span>
        <div class="seg" role="radiogroup" aria-labelledby="sex-l">
          ${[['F', 'Féminin'], ['M', 'Masculin']].map(([value, label]) => html`
            <label key=${value}><input type="radio" name="sex" checked=${f.sex === value} onChange=${() => onField('sex', value)} />${label}</label>`)}
        </div></div>
      <label class="field c2">Date de naissance<${DateInput} value=${f.birthdate} onText=${(v) => onField('birthdate', v)} />
        <span class="hint">${ageLabel(f.birthdate_iso)}</span></label>
      <label class="field">Poids, kg<input value=${f.weight_kg} inputmode="decimal" onInput=${(e) => onField('weight_kg', e.target.value)} />
        ${child && !f.weight_kg && html`<span class="hint is-warn">Obligatoire avant 15 ans</span>`}</label>
      <label class="field">Pesée le<${DateInput} value=${f.weighed_on} onText=${(v) => onField('weighed_on', v)} /></label>
      <label class="field c2">Grossesse ou allaitement
        <select value=${f.pregnancy || ''} onChange=${(e) => onField('pregnancy', e.target.value)}>
          <option value="">Non renseigné</option><option value="none">Non concernée</option>
          <option value="pregnant">Enceinte</option><option value="breastfeeding">Allaitement</option>
        </select></label>
      <label class="field c4">Allergies déclarées<input value=${f.allergies} placeholder="DCI séparées par des virgules"
        onInput=${(e) => onField('allergies', e.target.value)} /><span class="hint">Comparées aux DCI de chaque ligne, dès la recherche.</span></label>
      <span class="field c2 save-state" aria-live="polite">${saving ? 'Enregistrement…' : patient ? 'Patient enregistré' : ''}</span>
    </div>
    <p class="group-title">En-tête</p>
    <div class="grid">
      <label class="field c4">Établissement
        <select value=${content.establishment_id || ''} onChange=${(e) => onContentField('establishment_id', e.target.value ? Number(e.target.value) : null)}>
          <option value="">Choisir…</option>
          ${establishments.map((est) => html`<option key=${est.id} value=${est.id}>${est.name} · ${est.paper_format || 'A5'}</option>`)}
        </select><span class="hint"><a href="/etablissements">Gérer mes établissements</a></span></label>
      <label class="field c2">Date de prescription<${DateInput} value=${content.prescribed_on ? frDate(content.prescribed_on) : ''}
        placeholder="Aujourd'hui" onDate=${(iso) => onContentField('prescribed_on', iso)} /></label>
    </div>`;
}

/* =============================== Traitement =============================== */

function Composer({ patientId, onAdd }) {
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [hl, setHl] = useState(0);
  const loading = useRef(false);
  const enterWhileLoading = useRef(false);
  const input = useRef(null);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === '/' && !e.target.closest('input, textarea, select')) { e.preventDefault(); input.current && input.current.focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);
  useDebouncedEffect(() => {
    if (q.trim().length < 2) { setResults([]); loading.current = false; return; }
    const asked = q;
    Api.searchMedications(asked, patientId).then((data) => {
      if (input.current && input.current.value !== asked) return; // a newer search is on its way
      const found = data.results || [];
      setResults(found); setHl(0); setOpen(true); loading.current = false;
      // Enter pressed before the results: take the first catalog result, not free text.
      if (enterWhileLoading.current) {
        enterWhileLoading.current = false;
        choose(found.length ? { kind: 'catalog', item: found[0] } : { kind: 'free', name: asked.trim() });
      }
    }).catch(() => { loading.current = false; });
  }, [q], 200);

  const options = [...results.map((r) => ({ kind: 'catalog', item: r })), ...(q.trim() ? [{ kind: 'free', name: q.trim() }] : [])];
  const choose = (option) => {
    if (!option) return;
    onAdd(option.kind === 'catalog' ? option.item : { name: option.name });
    setQ(''); setResults([]); setOpen(false); loading.current = false;
  };
  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setHl((h) => Math.min(h + 1, options.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setHl((h) => Math.max(h - 1, 0)); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      if (loading.current) enterWhileLoading.current = true; else choose(options[hl]);
    }
    else if (e.key === 'Escape') { setOpen(false); }
  };

  return html`
    <div class="composer">
      <label class="search"><${Icon} name="search" /><span class="sr">Ajouter un médicament</span>
        <input ref=${input} value=${q} autocomplete="off" placeholder="Nom commercial ou DCI" role="combobox"
          aria-expanded=${open && options.length > 0} aria-controls="suggest"
          onInput=${(e) => {
            // Mark the search as pending right away: an Enter typed before the results waits for them.
            loading.current = e.target.value.trim().length >= 2;
            setQ(e.target.value); setOpen(true);
          }} onKeyDown=${onKeyDown}
          onBlur=${() => setTimeout(() => setOpen(false), 150)} />
        <span class="kbd">/</span></label>
      ${open && options.length > 0 && html`
        <div class="suggest" id="suggest" role="listbox" aria-label="Suggestions">
          ${results.length > 0 && html`<h3>Catalogue</h3>`}
          ${options.map((option, i) => html`
            ${option.kind === 'free' && html`<h3>Hors catalogue</h3>`}
            <div class=${`opt ${i === hl ? 'is-hl' : ''}`} role="option" aria-selected=${i === hl} key=${i}
              onMouseDown=${(e) => { e.preventDefault(); choose(option); }} onMouseEnter=${() => setHl(i)}>
              ${option.kind === 'catalog' ? html`
                <b>${option.item.name}${option.item.dosage && ` ${option.item.dosage}`}
                  ${option.item.substances.length > 0 && html` <span class="dci">(${option.item.substances.join(', ').toLowerCase()})</span>`}</b>
                <span class="meta">${[option.item.form, option.item.presentation].filter(Boolean).join(' · ')}</span>
                ${option.item.allergy_warning && option.item.allergy_warning.length > 0
                  && html`<span class="side"><span class="lvl lvl-justify">Allergie déclarée</span></span>`}`
              : html`<b>Utiliser « ${option.name} » en saisie libre</b><span class="meta">Ne sera pas vérifié par l'analyse</span>`}
            </div>`)}
          <footer><span><span class="kbd">↑</span><span class="kbd">↓</span>Naviguer</span>
            <span><span class="kbd">↵</span>Ajouter</span><span><span class="kbd">Échap</span>Fermer</span></footer>
        </div>`}
    </div>`;
}

export function TreatmentStep({ content, analysis, analysisError, patientId, onAdd, onLineField, onRemoveLine,
  onContentField, focusLineId, goStep }) {
  const alerts = (analysis && analysis.alerts) || [];
  const free = new Set(((analysis && analysis.scope.free_text_lines) || []));
  const focusRef = useRef(null);
  useEffect(() => { focusRef.current && focusRef.current.focus(); }, [focusLineId]);

  return html`
    <h1>Traitement</h1>
    <p class="lead">Tapez un nom ou une DCI puis Entrée. L'analyse se relance à chaque modification.</p>
    <${Composer} patientId=${patientId} onAdd=${onAdd} />
    ${analysisError && html`<p class="form-error" role="alert">${analysisError}</p>`}
    ${content.lines.length === 0 ? html`<div class="empty">Aucun médicament pour l'instant.</div>` : html`
      <div class="lines">${content.lines.map((line, i) => {
        const own = alerts.filter((a) => a.line_ids[0] === line.line_id);
        return html`<div class=${`line ${focusLineId === line.line_id ? 'is-focus' : ''}`} key=${line.line_id}>
          <span class="n">${i + 1}</span>
          <div>
            <div class="drug">${line.name}${line.dosage && ` ${line.dosage}`}
              ${line.substances && line.substances.length > 0 && html` <span class="dci">(${line.substances.join(', ').toLowerCase()})</span>`}</div>
            <div class="drug-sub">${line.medication_id ? (line.form || 'Catalogue') : 'Saisie libre'}</div>
            <div class="line-fields">
              <input aria-label=${`Posologie, ligne ${i + 1}`} placeholder="Posologie" value=${line.posology}
                ref=${focusLineId === line.line_id ? focusRef : null} onInput=${(e) => onLineField(line.line_id, 'posology', e.target.value)} />
              <input aria-label=${`Durée, ligne ${i + 1}`} placeholder=${content.duration || 'Durée'} value=${line.duration}
                onInput=${(e) => onLineField(line.line_id, 'duration', e.target.value)} />
              <input aria-label=${`Quantité, ligne ${i + 1}`} placeholder="Quantité" value=${line.quantity}
                onInput=${(e) => onLineField(line.line_id, 'quantity', e.target.value)} />
            </div>
            ${own.map((a) => html`<div class=${`line-alert ${kindOf(a)}`} key=${a.id}>
              <span class=${`lvl lvl-${kindOf(a)}`}>${alertTag(a)}</span>
              <p><b>${linesLabel(content, a.line_ids)}</b> : ${a.details && a.details.risks ? a.details.risks : a.message}</p>
              ${a.requirement === 'blocking' ? html`<span class="muted small">Retirez ou remplacez une ligne</span>`
                : a.requirement === 'justify' ? html`<button class="btn btn-sm btn-ghost" onClick=${() => goStep(3)}>${a.derogation ? 'Motif saisi' : 'Justifier'}</button>` : ''}
            </div>`)}
            ${free.has(line.name) && html`<div class="line-alert info"><span class="lvl lvl-info">Saisie libre</span>
              <p>Hors catalogue : non vérifié par l'analyse.</p></div>`}
          </div>
          <button class="icon-btn" aria-label=${`Retirer la ligne ${i + 1}`} onClick=${() => onRemoveLine(line.line_id)}><${Icon} name="trash" /></button>
        </div>`;
      })}</div>`}
    <p class="group-title">Pour toute l'ordonnance</p>
    <div class="grid">
      <label class="field c2">Durée de traitement<input value=${content.duration} onInput=${(e) => onContentField('duration', e.target.value)} />
        <span class="hint">Sauf lignes précisées</span></label>
      <label class="field c2">Renouvellement<input value=${content.renewal} onInput=${(e) => onContentField('renewal', e.target.value)} /></label>
      <label class="field c6">Bilan biologique<textarea rows="2" value=${content.lab_results} onInput=${(e) => onContentField('lab_results', e.target.value)}></textarea></label>
      <label class="field c6">Mention pour le patient<textarea rows="2" value=${content.general_note} onInput=${(e) => onContentField('general_note', e.target.value)}></textarea></label>
    </div>`;
}

/* ============================== Vérification ============================== */

const REASON_STEP = {
  patient_missing: 1, sex_missing: 1, birthdate_missing: 1, weight_missing: 1,
  establishment_missing: 1, no_lines: 2, posology_missing: 2,
};

export function CheckStep({ content, check, checkError, ordonnance, onDerogation, onEditLine, goStep, onReprint, onCancelCorrect }) {
  const issued = ordonnance.status !== 'draft';
  const frozen = ordonnance.snapshot;
  const analysis = issued ? frozen.analysis : check && check.analysis;
  if (!issued && !check) {
    return html`<h1>Vérification</h1>${checkError ? html`<p class="form-error" role="alert">${checkError}</p>` : html`<p class="lead">Analyse en cours…</p>`}`;
  }
  const missing = issued ? [] : check.reasons.filter((r) => REASON_STEP[r.code]);
  const alerts = analysis.alerts;
  const concerned = new Set(alerts.flatMap((a) => a.line_ids));
  const clean = content.lines.filter((l) => l.medication_id && !concerned.has(l.line_id));
  const warnings = issued ? frozen.warnings : check.warnings;
  const refs = issued ? frozen.referentials : check.referentials;

  return html`
    <h1>${issued ? (ordonnance.status === 'cancelled' ? 'Ordonnance annulée' : 'Ordonnance émise') : 'Vérification'}</h1>
    ${!issued && html`<p class="lead">Une contre-indication bloque toujours. Une association déconseillée, un doublon de substance ou une allergie demande un motif écrit, conservé avec l'ordonnance.</p>`}
    ${issued && html`<div class="issued">
      <h2><${Icon} name="check-circle" />Ordonnance n° ${ordonnance.number} ${ordonnance.status === 'cancelled' ? 'annulée' : 'émise'}</h2>
      <p>${ordonnance.status === 'cancelled' ? `Annulée : ${ordonnance.cancel_reason}.` : 'Figée avec son analyse, ses motifs et les versions des référentiels.'}</p>
      <div class="row"><button class="btn" onClick=${onReprint}><${Icon} name="printer" />Réimprimer</button>
        ${ordonnance.status === 'issued' && html`<button class="btn btn-ghost" onClick=${onCancelCorrect}><${Icon} name="undo" />Annuler et corriger</button>`}</div>
      <${AccessLogPanel} id=${ordonnance.id} />
    </div>`}
    ${checkError && html`<p class="form-error" role="alert">${checkError}</p>`}
    <div class="review">
      ${missing.length > 0 && html`<article class="section justify"><div class="section-head"><${Icon} name="alert" /><h3>À compléter</h3></div>
        <div class="section-body ok-list">${missing.map((r) => html`<div class="ok-row" key=${r.code}>
          <span style="flex:1">${r.message}${r.line_ids && ` (${linesLabel(content, r.line_ids)})`}</span>
          <button class="btn btn-sm" onClick=${() => goStep(REASON_STEP[r.code])}>Compléter</button></div>`)}</div></article>`}
      ${alerts.filter((a) => a.requirement !== 'info').map((a) => html`
        <article class=${`section ${kindOf(a)}`} key=${a.id}>
          <div class="section-head"><${Icon} name=${a.requirement === 'blocking' ? 'ban' : 'alert'} />
            <h3>${alertTag(a)} · ${alertTitle(a)}</h3>
            ${a.requirement === 'blocking' && !issued && html`<button class="btn btn-sm" onClick=${() => onEditLine(a.line_ids[0])}><${Icon} name="pencil" />Modifier la ligne</button>`}</div>
          <div class="section-body"><div class="who">${linesLabel(content, a.line_ids) || a.message}</div>
            <p>${[a.details && a.details.risks, a.details && a.details.conduct].filter(Boolean).join(' ') || a.message}</p>
            ${a.requirement === 'blocking' && html`<p class="small">Aucune dérogation possible. Retirez ou remplacez une des lignes.</p>`}
            ${a.requirement === 'justify' && !issued && html`<div class=${`reason ${(content.derogations[a.id] || '').trim() ? 'is-ok' : ''}`}>
              <label class="sr" for=${`r-${a.id}`}>Motif bénéfice-risque</label>
              <textarea id=${`r-${a.id}`} rows="2" value=${content.derogations[a.id] || ''} onInput=${(e) => onDerogation(a.id, e.target.value)}
                placeholder="Motif bénéfice-risque : pourquoi maintenez-vous cette prescription ?"></textarea>
              <div class="state">${(content.derogations[a.id] || '').trim() ? 'Motif retenu, enregistré avec le brouillon' : 'Obligatoire pour émettre'}</div></div>`}
            ${a.requirement === 'justify' && issued && a.derogation && html`<p style="margin-top:8px"><b>Motif :</b> ${a.derogation}</p>`}
          </div></article>`)}
      ${alerts.filter((a) => a.requirement === 'info').map((a) => html`
        <article class="section" key=${a.id}><div class="section-head"><${Icon} name="info" /><h3>${alertTag(a)} · ${alertTitle(a)}</h3></div>
          <div class="section-body"><div class="who">${linesLabel(content, a.line_ids)}</div><p>${[a.details && a.details.risks, a.details && a.details.conduct].filter(Boolean).join(' ') || a.message}</p></div></article>`)}
      ${warnings.map((w) => html`<article class="section" key=${w.code}><div class="section-head"><${Icon} name="info" /><h3>${w.message}</h3></div></article>`)}
      ${clean.length > 0 && html`<article class="section ok"><div class="section-head"><${Icon} name="check-circle" /><h3>Sans alerte</h3></div>
        <div class="section-body ok-list">${clean.map((l) => html`<div class="ok-row" key=${l.line_id}><${Icon} name="check" />${l.name} : aucune interaction connue avec les autres lignes.</div>`)}</div></article>`}
    </div>
    <div class="scope"><b>Ce que l'analyse ne vérifie pas</b>
      <ul>${analysis.scope.not_checked.map((item) => html`<li key=${item}>${item}</li>`)}</ul>
      ${analysis.scope.free_text_lines.length > 0 && html`<p class="small">Lignes en saisie libre, non vérifiées : ${analysis.scope.free_text_lines.join(', ')}.</p>`}
      <small>${analysis.scope.disclaimer}${refs && refs.thesaurus ? ` Thésaurus : ${refs.thesaurus.label}.` : ''}${refs && refs.catalog ? ` Catalogue : ${refs.catalog.label}.` : ''}</small>
    </div>`;
}

const ACTION_LABELS = {
  read: 'Consultée', update: 'Modifiée', create: 'Créée', check: 'Vérifiée', issue: 'Émise', print: 'Imprimée',
  cancel: 'Annulée', renew: 'Reconduite', discard: 'Supprimée',
};

/** Who consulted or changed this ordonnance (ticket 20); loaded when opened. */
function AccessLogPanel({ id }) {
  const [entries, setEntries] = useState(null);
  const onToggle = (e) => {
    if (e.target.open && entries === null) Api.accessLog(id).then((d) => setEntries(d.entries)).catch(() => setEntries([]));
  };
  return html`<details class="access-log" onToggle=${onToggle}>
    <summary>Qui a consulté cette ordonnance</summary>
    ${entries === null ? html`<p class="muted small">Chargement…</p>` : html`<ul>${entries.map((entry, i) => html`
      <li key=${i}><span>${ACTION_LABELS[entry.action] || entry.action}</span>
        <span>${[entry.user.first_name, entry.user.last_name].filter(Boolean).join(' ') || entry.user.email}</span>
        <span class="muted">${new Date(entry.at.endsWith('Z') ? entry.at : `${entry.at}Z`).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })}</span></li>`)}</ul>`}
  </details>`;
}
