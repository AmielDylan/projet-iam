/** Account pages: login, account request, password change. Same simple style as the prescriber workspace. */
import { html, render, useState } from '../../vendor/preact-htm-standalone.module.js';
import { ApiError, api } from './api.js';
import { DateInput, parseFrDate } from './ui.js';

const PROFESSIONS = ['Médecin', 'Chirurgien-dentiste', 'Sage-femme', 'Infirmier', 'Pharmacien', 'Autre professionnel autorisé'];
const FIELD_LABELS = {
  last_name: 'Nom', first_name: 'Prénom', birthdate: 'Date de naissance', profession: 'Profession',
  order_number: "Numéro d'inscription à l'ordre", email: 'Email', phone: 'Téléphone', identity_document: "Pièce d'identité",
};

/** Mirror of the server rule (app/web/routes.py, login_destination_for). */
function destinationFor(user, next) {
  const fallback = user.role === 'prescriber' ? '/ordonnances' : '/admin';
  if (!next || !next.startsWith('/') || next.startsWith('//')) return fallback;
  const allowed = user.role === 'prescriber'
    ? ['/ordonnances', '/patients', '/interactions', '/reglages', '/etablissements', '/changer-mot-de-passe'] : ['/admin'];
  return allowed.some((prefix) => next === prefix || next.startsWith(`${prefix}/`) || next.startsWith(`${prefix}?`)) ? next : fallback;
}

function AuthShell({ children, wide }) {
  return html`<div class="auth">
    <a class="brand auth-brand" href="/">DigiRemed</a>
    <main class=${`auth-card ${wide ? 'is-wide' : ''}`}>${children}</main>
    <p class="auth-foot muted small">Aide à la prescription · Analyse des interactions médicamenteuses</p>
  </div>`;
}

function Flashes({ items }) {
  return items.map(([category, message], i) => html`<p key=${i} class=${category === 'danger' ? 'form-error' : 'notice-ok'}>${message}</p>`);
}

function Login({ initial }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      const data = await api('/auth/login', { method: 'POST', body: { email, password } });
      if (data.two_factor_required) { location.href = `/connexion/verification?next=${encodeURIComponent(initial.next || '')}`; return; }
      if (data.two_factor_enrollment_required) { location.href = '/reglages#securite'; return; }
      location.href = data.user.must_change_password ? '/changer-mot-de-passe' : destinationFor(data.user, initial.next);
    } catch (err) {
      setError(err.body.message || err.message);
      setBusy(false);
    }
  };
  return html`<${AuthShell}>
    <h1>Connexion</h1>
    <p class="lead">Accès réservé aux comptes validés.</p>
    <${Flashes} items=${initial.flashes} />
    ${error && html`<p class="form-error" role="alert">${error}</p>`}
    <form class="stack" onSubmit=${submit}>
      <label class="field">Email<input type="email" name="email" autocomplete="email" required value=${email} onInput=${(e) => setEmail(e.target.value)} /></label>
      <label class="field">Mot de passe<input type="password" name="password" autocomplete="current-password" required value=${password} onInput=${(e) => setPassword(e.target.value)} /></label>
      <button class="btn btn-primary btn-block" type="submit" aria-disabled=${busy}>${busy ? 'Connexion…' : 'Se connecter'}</button>
    </form>
    <p class="auth-switch">Pas encore de compte ? <a href="/inscription">Demander un accès</a></p>
  <//>`;
}

function Register() {
  const [form, setForm] = useState({ profession: 'Médecin' });
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [fields, setFields] = useState([]);
  const [done, setDone] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (name) => (e) => setForm({ ...form, [name]: e.target.value });
  const pharmacist = form.profession === 'Pharmacien';

  const submit = async (e) => {
    e.preventDefault();
    const missing = ['last_name', 'first_name', 'birthdate', 'profession', 'order_number', 'email', 'phone']
      .filter((name) => !String(form[name] || '').trim());
    if (!pharmacist && !file) missing.push('identity_document');
    if (form.birthdate && !parseFrDate(form.birthdate)) missing.push('birthdate');
    if (missing.length) { setFields(missing); setError(`À compléter : ${missing.map((m) => FIELD_LABELS[m]).join(', ')}.`); return; }
    setBusy(true); setError(''); setFields([]);
    const body = new FormData();
    Object.entries(form).forEach(([k, v]) => body.append(k, k === 'birthdate' ? parseFrDate(v) : v));
    if (file) body.append('identity_document', file);
    try {
      const response = await fetch('/api/v1/auth/register', { method: 'POST', body, credentials: 'same-origin' });
      const data = await response.json();
      if (!response.ok) throw new ApiError(response.status, { error: data.message, ...data });
      setDone(data);
    } catch (err) {
      setError(err.message);
      setFields(err.body.fields || []);
    } finally { setBusy(false); }
  };
  const bad = (name) => (fields.includes(name) ? 'is-invalid' : '');

  if (done) {
    return html`<${AuthShell}>
      <h1>${done.code === 'waitlist' ? "Liste d'attente" : 'Demande envoyée'}</h1>
      <p class="lead">${done.message}</p>
      ${done.code !== 'waitlist' && html`<p class="muted">Vous recevrez votre mot de passe temporaire par email après vérification de votre pièce d'identité.</p>`}
      <a class="btn btn-primary btn-block" href="/connexion">Retour à la connexion</a>
    <//>`;
  }
  return html`<${AuthShell} wide>
    <h1>Demander un accès</h1>
    <p class="lead">Chaque demande est vérifiée par l'administrateur avant ouverture du compte.</p>
    ${error && html`<p class="form-error" role="alert">${error}</p>`}
    <form class="grid" onSubmit=${submit} novalidate>
      <label class=${`field c3 ${bad('last_name')}`}>Nom<input value=${form.last_name || ''} onInput=${set('last_name')} autocomplete="family-name" /></label>
      <label class=${`field c3 ${bad('first_name')}`}>Prénom<input value=${form.first_name || ''} onInput=${set('first_name')} autocomplete="given-name" /></label>
      <label class=${`field c3 ${bad('birthdate')}`}>Date de naissance<${DateInput} value=${form.birthdate || ''} onText=${(v) => setForm((f) => ({ ...f, birthdate: v }))} /></label>
      <label class=${`field c3 ${bad('profession')}`}>Profession
        <select onChange=${set('profession')}>${PROFESSIONS.map((p) => html`<option key=${p} value=${p} selected=${p === form.profession}>${p}</option>`)}</select></label>
      ${pharmacist && html`<p class="notice c6"><span>La rédaction d'ordonnances n'est pas ouverte aux pharmaciens. Votre demande rejoindra la liste d'attente de l'offre officine.</span></p>`}
      <label class=${`field c3 ${bad('order_number')}`}>N° d'inscription à l'ordre<input value=${form.order_number || ''} onInput=${set('order_number')} /></label>
      <label class=${`field c3 ${bad('phone')}`}>Téléphone<input type="tel" value=${form.phone || ''} onInput=${set('phone')} autocomplete="tel" /></label>
      <label class=${`field c6 ${bad('email')}`}>Email<input type="email" value=${form.email || ''} onInput=${set('email')} autocomplete="email" /></label>
      ${!pharmacist && html`<label class=${`field c6 ${bad('identity_document')}`}>Pièce d'identité (PDF, JPG ou PNG)
        <input type="file" accept="application/pdf,image/jpeg,image/png" onChange=${(e) => setFile(e.target.files[0] || null)} />
        <span class="hint">Utilisée seulement pour vérifier votre profil, puis supprimée après la décision.</span></label>`}
      <div class="c6 row-end"><a class="btn btn-ghost" href="/connexion">J'ai déjà un compte</a>
        <button class="btn btn-primary" type="submit" aria-disabled=${busy}>${busy ? 'Envoi…' : 'Envoyer la demande'}</button></div>
    </form>
  <//>`;
}

function ChangePassword({ initial }) {
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm_password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (name) => (e) => setForm({ ...form, [name]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    if (form.new_password !== form.confirm_password) { setError('Les deux mots de passe ne correspondent pas.'); return; }
    setBusy(true); setError('');
    try {
      await api('/auth/change-password', { method: 'POST', body: form });
      location.href = initial.role === 'admin' ? '/admin' : '/ordonnances';
    } catch (err) { setError(err.body.message || err.message); setBusy(false); }
  };
  return html`<${AuthShell}>
    <h1>Nouveau mot de passe</h1>
    <p class="lead">${initial.must_change ? 'Remplacez le mot de passe temporaire reçu par email avant de continuer.' : 'Choisissez un nouveau mot de passe.'}</p>
    ${error && html`<p class="form-error" role="alert">${error}</p>`}
    <form class="stack" onSubmit=${submit}>
      <label class="field">${initial.must_change ? 'Mot de passe temporaire' : 'Mot de passe actuel'}<input type="password" autocomplete="current-password" value=${form.current_password} onInput=${set('current_password')} /></label>
      <label class="field">Nouveau mot de passe<input type="password" autocomplete="new-password" value=${form.new_password} onInput=${set('new_password')} /></label>
      <label class="field">Confirmer<input type="password" autocomplete="new-password" value=${form.confirm_password} onInput=${set('confirm_password')} /></label>
      <button class="btn btn-primary btn-block" type="submit" aria-disabled=${busy}>Enregistrer</button>
    </form>
  <//>`;
}

const initial = JSON.parse(document.getElementById('initial-data').textContent);
const Page = { login: Login, register: Register, 'change-password': ChangePassword }[initial.page];
render(html`<${Page} initial=${initial} />`, document.getElementById('app'));
