/** Settings: professional profile and security (two-factor authentication), in one page with two tabs. */
import { html, render, useEffect, useState } from '../../vendor/preact-htm-standalone.module.js';
import { api } from './api.js';
import { AppBar, useSessionLock } from './shell.js';

const TABS = [['profil', 'Profil professionnel'], ['securite', 'Sécurité']];

function SettingsPage({ initial }) {
  const start = location.hash.slice(1) || initial.tab || 'profil';
  const [tab, setTab] = useState(TABS.some(([k]) => k === start) ? start : 'profil');
  const lock = useSessionLock();
  useEffect(() => { history.replaceState(null, '', `#${tab}`); }, [tab]);
  return html`
    <${AppBar} current="reglages" />
    <main class="page page-narrow">
      <h1>Réglages</h1>
      <div class="tabs" role="tablist">${TABS.map(([key, label]) => html`
        <button role="tab" key=${key} aria-selected=${tab === key} onClick=${() => setTab(key)}>${label}</button>`)}</div>
      ${tab === 'profil' ? html`<${ProfilePanel} />` : html`<${SecurityPanel} enrollmentRequired=${initial.enrollment_required} />`}
    </main>${lock}`;
}

/* ------------------------------- Profil ------------------------------- */

const FIELDS = [
  ['title', 'Civilité', 'c2', 'Dr, Pr, Mme…'], ['first_name', 'Prénom', 'c2'], ['last_name', 'Nom', 'c2'],
  ['profession', 'Profession', 'c3', 'Médecin généraliste'], ['organization', 'Organisme', 'c3'],
  ['phone', 'Téléphone', 'c3'], ['email', 'Email professionnel', 'c3'],
  ['identifier_label', 'Libellé identifiant', 'c3', "N° d'ordre…"], ['identifier_value', 'Identifiant', 'c3'],
  ['secondary_identifier_label', 'Second libellé', 'c3'], ['secondary_identifier_value', 'Second identifiant', 'c3'],
  ['country', 'Pays', 'c3', 'Bénin'],
];

function ProfilePanel() {
  const [form, setForm] = useState(null);
  const [state, setState] = useState('');
  const [error, setError] = useState('');
  useEffect(() => { api('/prescriber/profile').then((d) => setForm(d.profile)).catch((e) => setError(e.message)); }, []);
  const set = (name) => (e) => { setForm({ ...form, [name]: e.target.value }); setState(''); };
  const submit = async (e) => {
    e.preventDefault(); setError(''); setState('saving');
    try { const d = await api('/prescriber/profile', { method: 'POST', body: form }); setForm(d.profile); setState('saved'); }
    catch (err) { setError(err.message); setState(''); }
  };
  return html`
    <p class="lead">Ces informations figurent en en-tête de vos ordonnances. Une modification ne change jamais une ordonnance déjà émise.</p>
    ${error && html`<p class="form-error" role="alert">${error}</p>`}
    ${form && html`<form class="card" onSubmit=${submit}>
      <div class="grid">
        ${FIELDS.map(([name, label, span, placeholder]) => html`<label class=${`field ${span}`} key=${name}>${label}
          <input value=${form[name] || ''} placeholder=${placeholder || ''} onInput=${set(name)} /></label>`)}
        <label class="field c6">Adresse<textarea rows="2" value=${form.address || ''} onInput=${set('address')}></textarea></label>
        <label class="field c6">Mentions complémentaires<textarea rows="2" value=${form.extra_details || ''} onInput=${set('extra_details')}></textarea></label>
      </div>
      <div class="row-end" style="margin-top:18px">
        <span class="muted small" aria-live="polite">${state === 'saved' ? 'Profil enregistré' : ''}</span>
        <button class="btn btn-primary" type="submit" aria-disabled=${state === 'saving'}>Enregistrer</button></div>
    </form>`}`;
}

/* ------------------------------ Sécurité ------------------------------ */

/** QR code as SVG markup, drawn by the vendored qrcode-generator (global `qrcode`). */
function qrSvg(text) {
  const qr = window.qrcode(0, 'M');
  qr.addData(text);
  qr.make();
  return qr.createSvgTag({ cellSize: 5, margin: 2, scalable: true });
}

function SecurityPanel({ enrollmentRequired }) {
  const [status, setStatus] = useState(null);
  const [setup, setSetup] = useState(null);
  const [code, setCode] = useState('');
  const [codes, setCodes] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => { api('/auth/2fa').then(setStatus).catch((e) => setError(e.message)); }, []);

  const start = async () => {
    setError('');
    try { setSetup(await api('/auth/2fa/setup', { method: 'POST' })); } catch (e) { setError(e.message); }
  };
  const confirm = async (e) => {
    e.preventDefault(); setError('');
    try {
      const data = await api('/auth/2fa/confirm', { method: 'POST', body: { code } });
      setCodes(data.recovery_codes); setSetup(null); setStatus({ ...status, enabled: true });
    } catch (err) { setError(err.code === 'wrong_code' ? "Code incorrect. Vérifiez l'heure du téléphone et réessayez." : err.message); }
  };

  return html`
    <p class="lead">La double authentification demande, à chaque connexion, un code à six chiffres affiché par une application de votre téléphone (Google Authenticator, Microsoft Authenticator, FreeOTP…).</p>
    ${enrollmentRequired && !(status && status.enabled) && html`<div class="notice"><span>Votre organisation exige la double authentification. Activez-la pour continuer.</span></div>`}
    ${error && html`<p class="form-error" role="alert">${error}</p>`}
    ${status && status.enabled && !codes && html`<section class="card">
      <h2><span class="status status-issued">Activée</span> Double authentification</h2>
      <p>Chaque connexion demande votre mot de passe puis un code de votre application. Téléphone perdu : utilisez un code de secours, puis demandez à l'administrateur de réinitialiser la double authentification.</p>
    </section>`}
    ${status && !status.enabled && !setup && html`<section class="card">
      <h2><span class="status status-draft">Désactivée</span> Double authentification</h2>
      <p>${status.required ? 'Elle est obligatoire pour votre compte.' : 'Recommandée : elle protège les données de vos patients si votre mot de passe est découvert.'}</p>
      <button class="btn btn-primary" onClick=${start}>Activer la double authentification</button>
    </section>`}
    ${setup && html`<section class="card">
      <h2>1. Scannez ce code avec votre application</h2>
      <div class="qr" dangerouslySetInnerHTML=${{ __html: qrSvg(setup.otpauth_uri) }}></div>
      <p class="small">Impossible de scanner ? Saisissez cette clé dans l'application : <code class="secret">${setup.secret.match(/.{1,4}/g).join(' ')}</code></p>
      <h2>2. Saisissez le code affiché</h2>
      <form class="inline-form" onSubmit=${confirm}>
        <label class="field">Code à six chiffres<input value=${code} inputmode="numeric" maxlength="6" autocomplete="one-time-code"
          onInput=${(e) => setCode(e.target.value.replace(/\D/g, ''))} /></label>
        <button class="btn btn-primary" type="submit" aria-disabled=${code.length !== 6}>Confirmer</button>
      </form>
    </section>`}
    ${codes && html`<section class="card">
      <h2><span class="status status-issued">Activée</span> Notez vos codes de secours</h2>
      <p>Chaque code permet une seule connexion sans téléphone. Ils ne seront plus affichés : imprimez-les ou recopiez-les, et gardez-les à part.</p>
      <ol class="recovery">${codes.map((c) => html`<li key=${c}><code>${c}</code></li>`)}</ol>
      <div class="row"><button class="btn" onClick=${() => window.print()}>Imprimer</button>
        <a class="btn btn-primary" href="/ordonnances">J'ai noté mes codes</a></div>
    </section>`}
    <section class="card">
      <h2>Mot de passe</h2>
      <p>Changez votre mot de passe à tout moment.</p>
      <a class="btn" href="/changer-mot-de-passe">Changer le mot de passe</a>
    </section>`;
}

const initial = JSON.parse(document.getElementById('initial-data').textContent);
render(html`<${SettingsPage} initial=${initial} />`, document.getElementById('app'));
