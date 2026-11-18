/** Public page: interactions between two medications (ANSM thesaurus). */
import { html, render, useEffect, useRef, useState } from '../../vendor/preact-htm-standalone.module.js';
import { api } from './api.js';
import { AppBar, Footer } from './shell.js';
import { Icon, useDebouncedEffect } from './ui.js';

// ANSM levels, most serious first. A row may combine several ("CI - ASDEC - PE"): the most serious wins.
const LEVELS = [
  { key: 'ci', tag: 'CI', title: 'Contre-indication', test: (v) => v.includes('CONTRE') || /\bCI\b/.test(v) },
  { key: 'asdec', tag: 'ASDEC', title: 'Association déconseillée', test: (v) => v.includes('DECONSEIL') || v.includes('ASDEC') },
  { key: 'pe', tag: 'PE', title: "Précaution d'emploi", test: (v) => v.includes('PRECAUTION') || /\bPE\b/.test(v) },
  { key: 'apec', tag: 'APEC', title: 'À prendre en compte', test: () => true },
];
const levelOf = (niveau) => {
  const v = (niveau || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase();
  return LEVELS.find((level) => level.test(v));
};
const rank = (it) => LEVELS.indexOf(levelOf(it.niveau));
const titleCase = (text) => (text || '').toLowerCase().replace(/(^|[\s(/-])\S/g, (c) => c.toUpperCase());

const TYPES = { classe: 'Classe', substance: 'Substance', specialite: 'Spécialité' };

function MedField({ label, value, onChange, onPick, onEnter, inputRef, classes = [] }) {
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [hl, setHl] = useState(0);
  const skip = useRef(false);
  useDebouncedEffect(() => {
    if (skip.current) { skip.current = false; return; }
    if (value.trim().length < 2) { setResults([]); return; }
    api(`/autocomplete?q=${encodeURIComponent(value)}`).then((d) => { setResults(d || []); setHl(0); setOpen(true); }).catch(() => {});
  }, [value], 250);
  const pick = (r) => { skip.current = true; onPick(r.resultat); setResults([]); setOpen(false); };
  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !(open && results.length) && onEnter) { e.preventDefault(); onEnter(); return; }
    if (!open || !results.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setHl((h) => Math.min(h + 1, results.length - 1)); }
    if (e.key === 'ArrowUp') { e.preventDefault(); setHl((h) => Math.max(h - 1, 0)); }
    if (e.key === 'Enter') { e.preventDefault(); pick(results[hl]); }
    if (e.key === 'Escape') setOpen(false);
  };
  return html`<div class="field med-field">${label}
    <div class="filter-search"><label class="search"><${Icon} name="search" />
      <input ref=${inputRef} value=${value} placeholder="Spécialité, substance ou classe" autocomplete="off" onKeyDown=${onKeyDown}
        onInput=${(e) => onChange(e.target.value)} onBlur=${() => setTimeout(() => setOpen(false), 150)} /></label>
      ${open && results.length > 0 && html`<div class="suggest" style="top:46px">${results.map((r, i) => html`
        <div key=${r.resultat + r.type} class=${`opt ${i === hl ? 'is-hl' : ''}`} onMouseDown=${(e) => { e.preventDefault(); pick(r); }}>
          <b>${r.resultat}</b><span class="side"><span class="lvl lvl-info">${TYPES[r.type] || r.type}</span></span></div>`)}</div>`}
    </div>
    ${classes.length > 1 && html`<span class="hint">Cette substance appartient à plusieurs classes : ${classes.map(titleCase).join(', ')}.</span>`}
  </div>`;
}

function Home({ initial }) {
  const params = new URLSearchParams(location.search);
  const [med1, setMed1] = useState(params.get('med1') || '');
  const [med2, setMed2] = useState(params.get('med2') || '');
  const [result, setResult] = useState(null);
  const [classes, setClasses] = useState([[], []]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const second = useRef(null);
  const search = async (a, b) => {
    if (!a.trim() || !b.trim()) { setError('Indiquez les deux médicaments.'); return; }
    setBusy(true); setError('');
    try {
      // An unknown name finds nothing: say so, rather than "no interaction".
      const checks = await Promise.all([a, b].map((m) => api('/validate', { method: 'POST', body: { medication: m } })));
      setClasses(checks.map((c) => (c.is_substance && c.classes) || []));
      const unknown = checks.filter((c) => !c.is_valid).map((c) => `« ${c.medication} »`);
      if (unknown.length) {
        setResult(null);
        setError(`${unknown.join(' et ')} ${unknown.length > 1 ? 'ne sont pas reconnus' : "n'est pas reconnu"} dans le thésaurus. Choisissez une proposition de la liste.`);
        return;
      }
      setResult(await api('/interactions', { method: 'POST', body: { med_1: a, med_2: b } }));
      history.replaceState(null, '', `?${new URLSearchParams({ med1: a, med2: b })}`);
    }
    catch (err) { setError(err.message); setResult(null); }
    finally { setBusy(false); }
  };
  const submit = (e) => { if (e) e.preventDefault(); search(med1, med2); };
  // A shared link (?med1=…&med2=…) shows its result straight away.
  useEffect(() => { if (med1 && med2) search(med1, med2); }, []);

  const prescriber = initial.user && initial.user.role === 'prescriber';
  return html`
    ${prescriber ? html`<${AppBar} current="interactions" />` : html`<header class="appbar"><div class="appbar-inner">
      <a class="brand" href="/">DigiRemed</a>
      <span class="spacer"></span>
      ${initial.user ? html`<a class="btn-mint btn-mint-sm" href=${initial.user.role === 'admin' ? '/admin' : '/ordonnances'}>${initial.user.role === 'admin' ? 'Administration' : 'Mes ordonnances'}</a>`
        : html`<a class="link-quiet" href="/connexion">Connexion</a><a class="btn-mint btn-mint-sm" href="/inscription">Demander un accès</a>`}
    </div></header>`}
    <main class="page">
      <h1>Interactions entre deux médicaments</h1>
      <p class="lead">Vérifiez si deux médicaments interagissent, selon le thésaurus des interactions médicamenteuses de l'ANSM.</p>
      <form class="card" onSubmit=${submit}>
        <div class="grid">
          <div class="c3"><${MedField} label="Premier médicament" value=${med1} onChange=${(v) => { setMed1(v); setClasses([[], classes[1]]); }} classes=${classes[0]}
            onPick=${(v) => { setMed1(v); if (second.current) second.current.focus(); }} onEnter=${() => second.current && second.current.focus()} /></div>
          <div class="c3"><${MedField} label="Second médicament" value=${med2} onChange=${(v) => { setMed2(v); setClasses([classes[0], []]); }} onPick=${setMed2} inputRef=${second}
            classes=${classes[1]} onEnter=${() => submit()} /></div>
        </div>
        ${error && html`<p class="form-error" role="alert" style="margin-top:14px">${error}</p>`}
        <div class="row-end" style="margin-top:16px"><button class="btn btn-primary" type="submit" aria-disabled=${busy}>${busy ? 'Recherche…' : 'Vérifier'}</button></div>
      </form>
      ${result && html`<${Result} result=${result} />`}
    </main><${Footer} />`;
}

function Result({ result }) {
  const items = [...result.interactions].sort((a, b) => rank(a) - rank(b));
  const med1 = titleCase(result.med_1);
  const med2 = titleCase(result.med_2);
  const present = LEVELS.filter((level) => items.some((it) => levelOf(it.niveau) === level));
  return html`<section class="ix" aria-live="polite">
    <header class="ix-head">
      <h2>Interaction entre <b>${med1}</b> et <b>${med2}</b></h2>
      <div class="ix-actions">
        ${present.map((level) => html`<span class=${`lvl lvl-${level.key}`} key=${level.key} title=${level.title}>${level.tag}</span>`)}
        <${ShareButton} med1=${result.med_1} med2=${result.med_2} />
      </div>
    </header>
    ${items.length === 0 ? html`<p class="ix-none">Aucune interaction connue entre ces deux médicaments.</p>` : html`
      ${items.map((it, i) => {
        const level = levelOf(it.niveau);
        const seeAlso = (it.details || '').startsWith('Voir aussi :');
        return html`<details class=${`ix-item is-${level.key}`} open key=${i}>
          <summary>
            <span class="ix-n">${i + 1}</span>
            <span class="ix-pair">${titleCase(it.class_1)}${titleCase(it.class_1) !== med1 && html` <small>(${med1})</small>`} + ${titleCase(it.class_2)}${titleCase(it.class_2) !== med2 && html` <small>(${med2})</small>`}</span>
            <span class=${`lvl lvl-${level.key}`}>${level.title}</span>
            <svg class="ix-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>
          </summary>
          <div class="ix-body">
            ${it.risques && html`<div><p class="ix-label">Risques</p><p>${it.risques}</p></div>`}
            ${it.actions && html`<div><p class="ix-label">Conduite à tenir</p><p>${it.actions}</p></div>`}
            ${it.details && html`<div class="ix-details"><p class="ix-label">${seeAlso ? 'Voir aussi' : 'Détails des classes'}</p>
              <p>${seeAlso ? it.details.slice('Voir aussi :'.length).trim() : it.details}</p></div>`}
          </div>
        </details>`;
      })}
      <div class="ix-legend"><span>Légende ANSM</span>
        <ul>${LEVELS.map((level) => html`<li key=${level.key}><span class=${`lvl lvl-${level.key}`}>${level.tag}</span>${level.title}</li>`)}</ul></div>
      <${Summary} result=${result} items=${items} />`}
    <p class="ix-foot">Aide à la décision. Elle ne remplace pas le jugement du professionnel de santé.</p>
  </section>`;
}

function Summary({ result, items }) {
  const [state, setState] = useState({ status: 'loading', text: '' });
  useEffect(() => {
    setState({ status: 'loading', text: '' });
    api('/summary', { method: 'POST', body: { med1: result.med_1, med2: result.med_2, interactions: items } })
      .then((d) => setState(d.summary ? { status: 'done', text: d.summary } : { status: 'none', text: '' }))
      .catch(() => setState({ status: 'none', text: '' }));
  }, [result]);
  if (state.status === 'none') return null;
  return html`<div class="ix-summary">
    <p class="ix-summary-title"><${Icon} name="spark" />Résumé</p>
    ${state.status === 'loading' ? html`<p class="muted">Résumé en cours de génération…</p>` : html`
      <p>${state.text}</p>
      <p class="ix-summary-note">Résumé généré par intelligence artificielle à titre indicatif. Il ne remplace pas la lecture du thésaurus ni l'avis d'un professionnel de santé.</p>`}
  </div>`;
}

function ShareButton({ med1, med2 }) {
  const [copied, setCopied] = useState(false);
  const share = async () => {
    const url = location.href;
    if (navigator.share) { try { await navigator.share({ title: `Interaction : ${med1} et ${med2}`, url }); } catch (e) { /* cancelled */ } return; }
    try { await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch (e) { /* no clipboard */ }
  };
  return html`<button type="button" class="btn btn-ghost btn-sm" onClick=${share}>${copied ? 'Lien copié' : 'Copier le lien'}</button>`;
}

const initial = JSON.parse(document.getElementById('initial-data').textContent);
render(html`<${Home} initial=${initial} />`, document.getElementById('app'));
