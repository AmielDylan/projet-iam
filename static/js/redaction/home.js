/** Public page: interactions between two medications (ANSM thesaurus). */
import { html, render, useRef, useState } from '../../vendor/preact-htm-standalone.module.js';
import { api } from './api.js';
import { AppBar, Footer } from './shell.js';
import { Icon, useDebouncedEffect } from './ui.js';

const LEVEL = (niveau) => {
  const v = (niveau || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase();
  if (v.includes('CONTRE')) return ['CI', 'ci', 'Contre-indication'];
  if (v.includes('DECONSEIL')) return ['ASDEC', 'justify', 'Association déconseillée'];
  if (v.includes('PRECAUTION')) return ['PE', 'pe', "Précaution d'emploi"];
  return ['APEC', 'info', 'À prendre en compte'];
};
const TYPES = { classe: 'Classe', substance: 'Substance', specialite: 'Spécialité' };

function MedField({ label, value, onChange, onPick, onEnter, inputRef }) {
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
    </div></div>`;
}

function Home({ initial }) {
  const [med1, setMed1] = useState('');
  const [med2, setMed2] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const second = useRef(null);
  const submit = async (e) => {
    if (e) e.preventDefault();
    if (!med1.trim() || !med2.trim()) { setError('Indiquez les deux médicaments.'); return; }
    setBusy(true); setError('');
    try {
      // An unknown name finds nothing: say so, rather than "no interaction".
      const checks = await Promise.all([med1, med2].map((m) => api('/validate', { method: 'POST', body: { medication: m } })));
      const unknown = checks.filter((c) => !c.is_valid).map((c) => `« ${c.medication} »`);
      if (unknown.length) {
        setResult(null);
        setError(`${unknown.join(' et ')} ${unknown.length > 1 ? 'ne sont pas reconnus' : "n'est pas reconnu"} dans le thésaurus. Choisissez une proposition de la liste.`);
        return;
      }
      setResult(await api('/interactions', { method: 'POST', body: { med_1: med1, med_2: med2 } }));
    }
    catch (err) { setError(err.message); setResult(null); }
    finally { setBusy(false); }
  };
  const prescriber = initial.user && initial.user.role === 'prescriber';
  return html`
    ${prescriber ? html`<${AppBar} current="interactions" />` : html`<header class="appbar"><div class="appbar-inner">
      <a class="brand" href="/">DigiRemed</a><span class="spacer"></span>
      ${initial.user ? html`<a class="btn btn-primary btn-sm" href=${initial.user.role === 'admin' ? '/admin' : '/ordonnances'}>${initial.user.role === 'admin' ? 'Administration' : 'Mes ordonnances'}</a>`
        : html`<a class="btn btn-ghost btn-sm" href="/inscription">Demander un accès</a><a class="btn btn-primary btn-sm" href="/connexion">Connexion</a>`}
    </div></header>`}
    <main class="page">
      <h1>Interactions entre deux médicaments</h1>
      <p class="lead">Vérifiez si deux médicaments interagissent, selon le thésaurus des interactions médicamenteuses de l'ANSM.</p>
      <form class="card" onSubmit=${submit}>
        <div class="grid">
          <div class="c3"><${MedField} label="Premier médicament" value=${med1} onChange=${setMed1}
            onPick=${(v) => { setMed1(v); if (second.current) second.current.focus(); }} onEnter=${() => second.current && second.current.focus()} /></div>
          <div class="c3"><${MedField} label="Second médicament" value=${med2} onChange=${setMed2} onPick=${setMed2} inputRef=${second}
            onEnter=${() => submit()} /></div>
        </div>
        ${error && html`<p class="form-error" role="alert" style="margin-top:14px">${error}</p>`}
        <div class="row-end" style="margin-top:16px"><button class="btn btn-primary" type="submit" aria-disabled=${busy}>${busy ? 'Recherche…' : 'Vérifier'}</button></div>
      </form>
      ${result && html`<section class="review">
        <h2 class="result-title">${result.count === 0 ? `Aucune interaction connue entre ${result.med_1} et ${result.med_2}` : `${result.count} interaction${result.count > 1 ? 's' : ''} entre ${result.med_1} et ${result.med_2}`}</h2>
        ${result.interactions.map((it, i) => {
          const [tag, kind, title] = LEVEL(it.niveau);
          return html`<article class=${`section ${kind === 'ci' ? 'ci' : kind === 'justify' ? 'justify' : ''}`} key=${i}>
            <div class="section-head"><${Icon} name=${kind === 'ci' ? 'ban' : kind === 'justify' ? 'alert' : 'info'} /><h3>${tag} · ${title}</h3></div>
            <div class="section-body"><div class="who">${it.class_1} + ${it.class_2}</div>
              ${it.risques && html`<p>${it.risques}</p>`}${it.actions && html`<p style="margin-top:6px"><b>Conduite à tenir :</b> ${it.actions}</p>`}
              ${it.details && html`<p class="small" style="margin-top:6px">${it.details}</p>`}</div></article>`;
        })}
        <p class="muted small">Aide à la décision. Elle ne remplace pas le jugement du professionnel de santé.</p>
      </section>`}
    </main><${Footer} />`;
}

const initial = JSON.parse(document.getElementById('initial-data').textContent);
render(html`<${Home} initial=${initial} />`, document.getElementById('app'));
