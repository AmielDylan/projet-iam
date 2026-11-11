/** Security page (ticket 22): enable two-factor authentication, show recovery codes once. */
import { html, render, useEffect, useState } from '../../vendor/preact-htm-standalone.module.js';
import { api } from './api.js';
import { AppBar, useSessionLock } from './shell.js';

/** QR code as SVG markup, drawn by the vendored qrcode-generator (global `qrcode`). */
function qrSvg(text) {
  const qr = window.qrcode(0, 'M');
  qr.addData(text);
  qr.make();
  return qr.createSvgTag({ cellSize: 5, margin: 2, scalable: true });
}

function SecurityPage({ initial }) {
  const [status, setStatus] = useState(null);
  const [setup, setSetup] = useState(null);
  const [code, setCode] = useState('');
  const [codes, setCodes] = useState(null);
  const [error, setError] = useState('');
  const lock = useSessionLock();
  useEffect(() => { api('/auth/2fa').then(setStatus).catch((e) => setError(e.message)); }, []);

  const start = async () => {
    setError('');
    try { setSetup(await api('/auth/2fa/setup', { method: 'POST' })); } catch (e) { setError(e.message); }
  };
  const confirm = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const data = await api('/auth/2fa/confirm', { method: 'POST', body: { code } });
      setCodes(data.recovery_codes); setSetup(null); setStatus({ ...status, enabled: true });
    } catch (err) { setError(err.code === 'wrong_code' ? 'Code incorrect. Vérifiez l’heure du téléphone et réessayez.' : err.message); }
  };

  return html`
    <${AppBar} current="securite" />
    <main class="page page-narrow">
      <h1>Sécurité</h1>
      <p class="lead">La double authentification demande, à chaque connexion, un code à six chiffres affiché par une application de votre téléphone (Google Authenticator, Microsoft Authenticator, FreeOTP…).</p>
      ${initial.enrollment_required && !status?.enabled && html`<div class="notice"><span>Votre organisation exige la double authentification. Activez-la pour continuer.</span></div>`}
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
    </main>
    ${lock}`;
}

const initial = JSON.parse(document.getElementById('initial-data').textContent);
render(html`<${SecurityPage} initial=${initial} />`, document.getElementById('app'));
