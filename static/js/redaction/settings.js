/** Settings: professional profile and security (two-factor authentication), in one page with two tabs. */
import { html, render, useEffect, useState } from '../../vendor/preact-htm-standalone.module.js';
import { api } from './api.js';
import { AppBar, Footer, useSessionLock } from './shell.js';

const TABS = [['profil', 'Profil professionnel'], ['signature', 'Signature et cachet'], ['securite', 'Sécurité']];

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
      ${tab === 'profil' && html`<${ProfilePanel} />`}
      ${tab === 'signature' && html`<${AssetsPanel} />`}
      ${tab === 'securite' && html`<${SecurityPanel} enrollmentRequired=${initial.enrollment_required} />`}
    </main><${Footer} />${lock}`;
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

/* -------------------------- Signature et cachet -------------------------- */

const ASSETS = [
  ['signature', 'Signature', 'Signez au stylo noir ou bleu sur une feuille blanche, puis photographiez-la de près, bien à plat.'],
  ['stamp', 'Cachet', 'Apposez votre cachet sur une feuille blanche, puis photographiez-le de près, bien à plat.'],
];

function AssetsPanel() {
  return html`<p class="lead">Ajoutés automatiquement aux ordonnances exportées en PDF. Sur une ordonnance imprimée, vous signez et tamponnez à la main.</p>
    ${ASSETS.map(([kind, label, help]) => html`<${AssetCard} key=${kind} kind=${kind} label=${label} help=${help} />`)}`;
}

/** Make the white paper transparent, keep the ink with soft edges, crop to the drawing. */
function removeBackground(image, sensitivity) {
  const scale = Math.min(1, 1000 / image.naturalWidth);
  const width = Math.round(image.naturalWidth * scale);
  const height = Math.round(image.naturalHeight * scale);
  const canvas = document.createElement('canvas');
  canvas.width = width; canvas.height = height;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(image, 0, 0, width, height);
  const frame = ctx.getImageData(0, 0, width, height);
  const px = frame.data;

  // Paper and ink tones from the photo itself, so uneven light still works.
  const histogram = new Uint32Array(256);
  for (let i = 0; i < px.length; i += 4) histogram[Math.round(0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2])] += 1;
  const percentile = (p) => { let seen = 0; const goal = (px.length / 4) * p; for (let v = 0; v < 256; v += 1) { seen += histogram[v]; if (seen >= goal) return v; } return 255; };
  const paper = percentile(0.6);
  const ink = Math.min(percentile(0.02), paper - 40);
  const threshold = paper - (paper - ink) * (0.15 + 0.6 * (1 - sensitivity / 100));

  let [minX, minY, maxX, maxY] = [width, height, -1, -1];
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const i = (y * width + x) * 4;
      const lum = 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2];
      const alpha = lum >= threshold ? 0 : Math.min(255, Math.round(((threshold - lum) / Math.max(1, threshold - ink)) * 255 * 1.4));
      px[i + 3] = alpha;
      if (alpha > 24) { minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y); }
    }
  }
  if (maxX < 0) return null;
  ctx.putImageData(frame, 0, 0);
  const pad = 8;
  const crop = document.createElement('canvas');
  crop.width = Math.min(width, maxX - minX + 1 + pad * 2);
  crop.height = Math.min(height, maxY - minY + 1 + pad * 2);
  crop.getContext('2d').drawImage(canvas, Math.max(0, minX - pad), Math.max(0, minY - pad), crop.width, crop.height, 0, 0, crop.width, crop.height);
  return crop;
}

function AssetCard({ kind, label, help }) {
  const [present, setPresent] = useState(null);
  const [version, setVersion] = useState(Date.now());
  const [source, setSource] = useState(null);
  const [sensitivity, setSensitivity] = useState(50);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { api('/prescriber/assets').then((d) => setPresent(d.assets[kind])).catch(() => setPresent(false)); }, []);
  useEffect(() => {
    if (!source) { setPreview(null); return; }
    const result = removeBackground(source, sensitivity);
    if (!result) { setPreview(null); setError("Aucun tracé trouvé : la photo est peut-être trop claire. Augmentez la sensibilité ou reprenez la photo."); return; }
    setError(''); setPreview(result);
  }, [source, sensitivity]);

  const choose = (e) => {
    const file = e.target.files[0];
    e.target.value = '';
    if (!file) return;
    if (!file.type.startsWith('image/')) { setError('Choisissez une photo (JPG, PNG ou HEIC converti).'); return; }
    const image = new Image();
    image.onload = () => { setSource(image); URL.revokeObjectURL(image.src); };
    image.onerror = () => setError("Cette image n'a pas pu être lue. Essayez une photo au format JPG ou PNG.");
    image.src = URL.createObjectURL(file);
  };
  const save = () => {
    setBusy(true);
    preview.toBlob(async (blob) => {
      try {
        await api(`/prescriber/assets/${kind}`, { method: 'POST', raw: blob });
        setPresent(true); setSource(null); setVersion(Date.now());
      } catch (err) { setError(err.message); }
      setBusy(false);
    }, 'image/png');
  };
  const remove = async () => {
    if (!window.confirm(`Supprimer votre ${label.toLowerCase()} ? Les ordonnances déjà émises la gardent.`)) return;
    try { await api(`/prescriber/assets/${kind}`, { method: 'DELETE' }); setPresent(false); } catch (err) { setError(err.message); }
  };

  return html`<section class="card asset">
    <h2>${label} ${present === true && !source && html`<span class="status status-issued">Enregistrée</span>`}</h2>
    ${error && html`<p class="form-error" role="alert">${error}</p>`}
    ${source ? html`
      <div class="checker">${preview && html`<img src=${preview.toDataURL('image/png')} alt=${`Aperçu de la ${label.toLowerCase()} détourée`} />`}</div>
      <label class="field">Sensibilité du détourage
        <input type="range" min="0" max="100" value=${sensitivity} onInput=${(e) => setSensitivity(Number(e.target.value))} />
        <span class="hint">Si des traces du papier restent, baissez la sensibilité. Si le tracé s'efface, augmentez-la.</span></label>
      <div class="row-end"><button class="btn btn-ghost" onClick=${() => setSource(null)}>Annuler</button>
        <button class="btn btn-primary" aria-disabled=${!preview || busy} onClick=${() => preview && !busy && save()}>Enregistrer</button></div>`
    : html`
      ${present && html`<div class="checker"><img src=${`/api/v1/prescriber/assets/${kind}?v=${version}`} alt=${label} /></div>`}
      <p>${help}</p>
      <div class="row">
        <label class="btn ${present ? '' : 'btn-primary'}">${present ? 'Remplacer' : 'Importer une photo'}
          <input class="sr" type="file" accept="image/*" capture="environment" onChange=${choose} /></label>
        ${present && html`<button class="btn btn-ghost" onClick=${remove}>Supprimer</button>`}
      </div>`}
  </section>`;
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
