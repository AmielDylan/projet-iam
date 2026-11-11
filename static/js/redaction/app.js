/**
 * Prescribing screen (ticket 11): three steps, autosaved draft, live IAM analysis, issuing.
 * The server holds every rule; this file keeps the screen in step with it.
 */
import { html, render, useCallback, useEffect, useRef, useState } from '../../vendor/preact-htm-standalone.module.js';
import { Api, onSessionLocked } from './api.js';
import { Sheet } from './sheet.js';
import { CheckStep, PatientStep, TreatmentStep } from './steps.js';
import { Icon, frDate, newLineId, useDebouncedEffect } from './ui.js';

const SAVE_DELAY = 700;
const RETRY_DELAY = 5000;

/** DD/MM/YYYY or YYYY-MM-DD to ISO, or null. */
function parseFrDate(text) {
  const value = String(text || '').trim();
  let m = value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (m) return `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`;
  m = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return m ? value : null;
}

const patientToForm = (p) => ({
  title: p.title || '', last_name: p.last_name || '', first_name: p.first_name || '', sex: p.sex || '',
  birthdate: frDate(p.birthdate), birthdate_iso: p.birthdate || null,
  weight_kg: p.weight_kg ? String(p.weight_kg).replace('.', ',') : '', weighed_on: frDate(p.weighed_on),
  pregnancy: p.pregnancy || '', allergies: (p.allergies || []).join(', '),
});
const formToPayload = (f) => ({
  title: f.title, last_name: f.last_name, first_name: f.first_name, sex: f.sex || null,
  birthdate: f.birthdate, weight_kg: f.weight_kg, weighed_on: f.weighed_on,
  pregnancy: f.pregnancy || null, allergies: f.allergies,
});

function App({ initial }) {
  const [ord, setOrd] = useState(initial.ordonnance);
  const [content, setContent] = useState(initial.ordonnance.content);
  const [step, setStep] = useState(initial.step);
  const [saveState, setSaveState] = useState('saved');
  const [savedAt, setSavedAt] = useState(null);
  const [savedVersion, setSavedVersion] = useState(initial.ordonnance.version);
  const [notice, setNotice] = useState('');
  const version = useRef(initial.ordonnance.version);
  const savedJson = useRef(JSON.stringify(initial.ordonnance.content));
  const saving = useRef(false);
  const latest = useRef(initial.ordonnance.content);

  const [patient, setPatient] = useState(initial.patient);
  const [patientForm, setPatientForm] = useState(initial.patient ? patientToForm(initial.patient) : null);
  const [patientSaving, setPatientSaving] = useState(false);
  const [patientError, setPatientError] = useState('');
  const creatingPatient = useRef(false);

  const [analysis, setAnalysis] = useState(null);
  const [analysisError, setAnalysisError] = useState('');
  const [check, setCheck] = useState(null);
  const [checkError, setCheckError] = useState('');
  const [focusLineId, setFocusLineId] = useState(null);
  const [dialog, setDialog] = useState(null);
  const [locked, setLocked] = useState(null);
  const narrow = window.matchMedia('(max-width: 1180px)').matches;
  const [preview, setPreview] = useState(() => {
    try { const v = localStorage.getItem('rx-preview'); return v === null ? !narrow : v === '1' && !narrow; } catch { return !narrow; }
  });

  const editable = ord.status === 'draft';
  const dirty = editable && JSON.stringify(content) !== savedJson.current;
  const establishment = initial.establishments.find((e) => e.id === content.establishment_id);

  /* ---------- session lock ---------- */
  useEffect(() => onSessionLocked(() => new Promise((resolve) => setLocked({ resolve }))), []);

  /* ---------- step in the address, so a reload comes back here ---------- */
  useEffect(() => {
    const url = new URL(location.href);
    url.searchParams.set('etape', String(step));
    history.replaceState(null, '', url);
    window.scrollTo(0, 0);
  }, [step]);

  /* ---------- autosave with versions ---------- */
  latest.current = content;
  const save = useCallback(async () => {
    if (saving.current || !editable) return;
    const payload = latest.current;
    const json = JSON.stringify(payload);
    if (json === savedJson.current) return;
    saving.current = true;
    setSaveState('saving');
    try {
      const data = await Api.save(ord.id, version.current, payload);
      version.current = data.ordonnance.version;
      savedJson.current = json;
      setSaveState('saved');
      setSavedAt(new Date());
      setSavedVersion(data.ordonnance.version);
      // Typed during the request: send the rest.
      if (JSON.stringify(latest.current) !== json) setTimeout(() => save(), 0);
    } catch (error) {
      if (error.code === 'version_conflict') {
        const current = error.body.current;
        version.current = current.version;
        savedJson.current = JSON.stringify(current.content);
        setContent(current.content);
        setSavedVersion(current.version);
        setSaveState('saved');
        setNotice('Ce brouillon a été modifié dans un autre onglet : la version la plus récente est affichée.');
      } else if (error.code === 'not_editable') {
        location.reload();
      } else if (error.code === 'network') {
        setSaveState('offline');
        setTimeout(() => { saving.current = false; save(); }, RETRY_DELAY);
        return;
      } else {
        setSaveState('error');
        setNotice(error.message);
      }
    }
    saving.current = false;
  }, [ord.id, editable]);

  useDebouncedEffect(() => { if (dirty) save(); }, [content], SAVE_DELAY);
  useEffect(() => {
    const warn = (e) => { if (dirty) { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  const updateContent = (patch) => setContent((c) => ({ ...c, ...patch }));
  const onContentField = (field, value) => {
    if (field === 'prescribed_on_text') { updateContent({ prescribed_on: parseFrDate(value) }); return; }
    updateContent({ [field]: value });
  };

  /* ---------- patient ---------- */
  const onPatientField = (field, value) => {
    setPatientForm((f) => {
      const next = { ...f, [field]: value };
      if (field === 'birthdate') next.birthdate_iso = parseFrDate(value);
      return next;
    });
  };
  useDebouncedEffect(async () => {
    if (!patientForm || !patientForm.last_name.trim() || creatingPatient.current) return;
    setPatientSaving(true);
    try {
      if (patient) {
        const data = await Api.updatePatient(patient.id, formToPayload(patientForm));
        setPatient(data.patient);
      } else {
        creatingPatient.current = true;
        const data = await Api.createPatient(formToPayload(patientForm));
        setPatient(data.patient);
        updateContent({ patient_id: data.patient.id });
      }
      setPatientError('');
    } catch (error) {
      setPatientError(error.message);
    } finally {
      creatingPatient.current = false;
      setPatientSaving(false);
    }
  }, [patientForm], 800);

  const onPickPatient = (p) => { setPatient(p); setPatientForm(patientToForm(p)); setPatientError(''); updateContent({ patient_id: p.id }); };
  const onNewPatient = (q) => {
    setPatient(null);
    setPatientForm({ ...patientToForm({}), last_name: /\d/.test(q) ? '' : q.trim() });
  };
  const onChangePatient = () => { setPatient(null); setPatientForm(null); updateContent({ patient_id: null }); };

  /* ---------- lines ---------- */
  const onAdd = (item) => {
    const id = newLineId();
    const line = item.id ? {
      line_id: id, medication_id: item.id, name: item.name, dosage: item.dosage || '', form: item.form || '',
      substances: item.substances || [], posology: '', duration: '', renewal: '', quantity: '', note: '',
    } : {
      line_id: id, medication_id: null, name: item.name, dosage: '', form: '', substances: [],
      posology: '', duration: '', renewal: '', quantity: '', note: '',
    };
    setContent((c) => ({ ...c, lines: [...c.lines, line] }));
    setFocusLineId(id);
  };
  const onLineField = (id, field, value) => setContent((c) => ({
    ...c, lines: c.lines.map((line) => (line.line_id === id ? { ...line, [field]: value } : line)),
  }));
  const onRemoveLine = (id) => setContent((c) => ({ ...c, lines: c.lines.filter((line) => line.line_id !== id) }));
  const onDerogation = (alertId, text) => setContent((c) => {
    const derogations = { ...c.derogations };
    if (text) derogations[alertId] = text; else delete derogations[alertId];
    return { ...c, derogations };
  });

  /* ---------- live analysis (step 2) ---------- */
  const analysisKey = JSON.stringify([content.lines, content.patient_id, content.derogations, patient && patient.allergies]);
  useEffect(() => {
    if (!editable || step !== 2) return undefined;
    const lines = content.lines.filter((line) => line.name);
    if (!lines.length) { setAnalysis(null); return undefined; }
    const timer = setTimeout(() => {
      Api.analyze(lines, content.patient_id, content.derogations)
        .then((data) => { setAnalysis(data); setAnalysisError(''); })
        .catch((error) => setAnalysisError(error.code === 'analysis_unavailable' ? error.message
          : "L'analyse n'a pas pu être relancée. Elle le sera à la prochaine modification."));
    }, 400);
    return () => clearTimeout(timer);
  }, [analysisKey, step]);

  /* ---------- verification (step 3), on the saved version ---------- */
  useEffect(() => {
    if (!editable || step !== 3 || dirty) return;
    setCheckError('');
    Api.check(ord.id).then((data) => setCheck(data.check))
      .catch((error) => { setCheck(null); setCheckError(error.message); });
  }, [step, savedVersion, dirty]);

  /* ---------- issuing ---------- */
  const canIssue = editable && check && check.can_issue && !dirty && saveState === 'saved' && check.version === version.current;
  const issue = async (popup) => {
    setDialog(null);
    try {
      const data = await Api.issue(ord.id, version.current);
      setOrd(data.ordonnance);
      popup.location.href = `${data.print_url}?print=1`;
    } catch (error) {
      popup.close();
      setNotice(error.code === 'issue_refused' ? "L'ordonnance ne peut pas encore être émise : voir les points ci-dessous." : error.message);
      Api.check(ord.id).then((d) => setCheck(d.check)).catch(() => {});
    }
  };
  const reprint = () => window.open(`/ordonnances/${ord.id}/impression?print=1`, '_blank');
  const cancelAndCorrect = async (reason) => {
    try {
      const data = await Api.cancelAndCorrect(ord.id, reason);
      location.href = `/ordonnances/${data.ordonnance.id}/rediger?etape=2`;
    } catch (error) { setNotice(error.message); setDialog(null); }
  };

  /* ---------- layout ---------- */
  const togglePreview = () => {
    setPreview((v) => { try { localStorage.setItem('rx-preview', v ? '0' : '1'); } catch { /* private mode */ } return !v; });
  };
  const blocking = check ? check.reasons.filter((r) => r.code === 'alert_blocking').length : 0;
  const unjustified = check ? check.reasons.filter((r) => r.code === 'alert_unjustified').length : 0;
  const stepCount = (check && step === 3 ? check.reasons.length
    : analysis ? analysis.summary.blocking_count + analysis.summary.unjustified_count : 0);
  const patientName = patient ? [patient.title, patient.first_name, patient.last_name].filter(Boolean).join(' ') : '';
  const crumb = ord.number ? `N° ${ord.number}${patientName ? ` · ${patientName}` : ''}` : `Brouillon${patientName ? ` · ${patientName}` : ''}`;

  return html`
    <header class="appbar">
      <a class="brand" href="/">DigiRemed</a>
      <nav class="crumbs" aria-label="Fil d'Ariane"><a href="/ordonnances">Ordonnances</a><span aria-hidden="true">/</span><b>${crumb}</b></nav>
      <span class="spacer"></span>
      <${SaveStatus} state=${editable ? (dirty && saveState === 'saved' ? 'pending' : saveState) : 'issued'} savedAt=${savedAt} ord=${ord} />
      <button class="btn btn-sm btn-ghost preview-toggle" onClick=${togglePreview}>
        <span class="long">${preview ? 'Masquer' : 'Afficher'} l'aperçu</span><span class="short">Aperçu</span></button>
    </header>

    <div class=${`desk ${preview ? '' : 'no-preview'}`}>
      <section class="work" aria-label="Rédaction">
        <div class="work-inner">
          <${Stepper} step=${step} setStep=${setStep} count=${editable ? stepCount : 0} blocking=${blocking > 0} issued=${!editable} />
          ${notice && html`<div class="notice" role="status"><span>${notice}</span><button class="btn btn-sm btn-ghost" onClick=${() => setNotice('')}>Fermer</button></div>`}
          ${step === 1 && html`<${PatientStep} content=${content} patient=${patient} form=${patientForm} onField=${onPatientField}
            onPick=${onPickPatient} onNew=${onNewPatient} onChange=${onChangePatient} saving=${patientSaving} error=${patientError}
            establishments=${initial.establishments} onContentField=${onContentField} />`}
          ${step === 2 && html`<${TreatmentStep} content=${content} analysis=${analysis} analysisError=${analysisError}
            patientId=${content.patient_id} onAdd=${onAdd} onLineField=${onLineField} onRemoveLine=${onRemoveLine}
            onContentField=${onContentField} focusLineId=${focusLineId} goStep=${setStep} />`}
          ${step === 3 && html`<${CheckStep} content=${content} check=${check} checkError=${checkError} ordonnance=${ord}
            onDerogation=${onDerogation} onEditLine=${(id) => { setFocusLineId(id); setStep(2); }} goStep=${setStep}
            onReprint=${reprint} onCancelCorrect=${() => setDialog({ kind: 'cancel' })} />`}
        </div>
        <div class="footbar"><div class="footbar-inner">
          ${step > 1 && html`<button class="btn btn-ghost" onClick=${() => setStep(step - 1)} aria-label="Retour"><${Icon} name="left" /><span class="long">Retour</span></button>`}
          ${step < 3 ? html`<span class="gate"></span><button class="btn btn-primary" onClick=${() => setStep(step + 1)}>
              ${step === 1 ? 'Continuer vers le traitement' : "Vérifier l'ordonnance"}<${Icon} name="right" /></button>`
            : editable && html`<${Gate} saveState=${saveState} dirty=${dirty} check=${check} blocking=${blocking} unjustified=${unjustified} />
              <button class="btn" aria-disabled=${!canIssue} onClick=${() => canIssue && setDialog({ kind: 'issue', pdf: true })}><${Icon} name="file" /><span class="long">Exporter en </span>PDF</button>
              <button class="btn btn-primary" aria-disabled=${!canIssue} onClick=${() => canIssue && setDialog({ kind: 'issue' })}><${Icon} name="printer" />Imprimer</button>`}
        </div></div>
        <button class="seam" onClick=${togglePreview} aria-label=${preview ? "Masquer l'aperçu" : "Afficher l'aperçu"}><${Icon} name=${preview ? 'right' : 'left'} /></button>
      </section>
      <aside class="reading" aria-label="Aperçu">
        <${Sheet} content=${content} patient=${patient} establishment=${establishment} prescriber=${initial.prescriber}
          number=${ord.number} focusLineId=${step === 2 ? focusLineId : null} />
      </aside>
    </div>

    ${dialog && dialog.kind === 'issue' && html`<${IssueDialog} patientName=${patientName} pdf=${dialog.pdf}
      onCancel=${() => setDialog(null)} onConfirm=${(popup) => issue(popup)} />`}
    ${dialog && dialog.kind === 'cancel' && html`<${CancelDialog} onCancel=${() => setDialog(null)} onConfirm=${cancelAndCorrect} />`}
    ${locked && html`<${LockScreen} onUnlocked=${() => { locked.resolve(); setLocked(null); }} />`}`;
}

function SaveStatus({ state, savedAt, ord }) {
  const time = savedAt ? savedAt.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '';
  const text = {
    saved: savedAt ? `Enregistré à ${time}` : 'Brouillon enregistré',
    pending: 'Modifications en cours',
    saving: 'Enregistrement…',
    offline: 'Hors ligne · nouvel essai automatique',
    error: "Échec de l'enregistrement",
    issued: ord.status === 'cancelled' ? 'Annulée' : `Émise le ${frDate(ord.issued_at)}`,
  }[state];
  const cls = { saved: 'is-fresh', issued: 'is-fresh', offline: 'is-offline', error: 'is-error' }[state] || '';
  return html`<span class=${`saved ${cls}`} role="status"><span class="dot"></span><span>${text}</span></span>`;
}

function Stepper({ step, setStep, count, blocking, issued }) {
  const items = [['01', 'Patient'], ['02', 'Traitement'], ['03', 'Vérification']];
  return html`<ol class="steps">${items.map(([no, label], i) => {
    const n = i + 1;
    const done = issued || n < step;
    return html`
      ${i > 0 && html`<li class="sep" aria-hidden="true"></li>`}
      <li key=${n}><button class=${done ? 'is-done' : ''} aria-current=${step === n ? 'step' : undefined} onClick=${() => setStep(n)}>
        <span class="no">${done && step !== n ? html`<${Icon} name="check" />` : no}</span><span class="label">${label}</span>
        ${n === 3 && count > 0 && html`<span class=${`count ${blocking ? 'is-ci' : ''}`}>${count}</span>`}
      </button></li>`;
  })}</ol>`;
}

function Gate({ saveState, dirty, check, blocking, unjustified }) {
  let text;
  if (saveState === 'offline') text = html`<b>Hors ligne.</b> L'émission reprendra au retour du réseau : l'analyse se fait sur le serveur.`;
  else if (dirty || saveState === 'saving' || !check) text = html`Vérification en cours…`;
  else if (blocking) text = html`<b>Émission impossible.</b> ${blocking} contre-indication : retirez ou remplacez une ligne.`;
  else if (!check.can_issue) {
    const missing = check.reasons.length - unjustified;
    text = unjustified && !missing ? html`<b>${unjustified} alerte${unjustified > 1 ? 's' : ''} à justifier</b> par un motif écrit.`
      : html`<b>${check.reasons.length} point${check.reasons.length > 1 ? 's' : ''} à compléter</b> avant l'émission.`;
  } else text = html`<b>Prête.</b> La première impression ou le premier PDF émet l'ordonnance.`;
  return html`<span class="gate" aria-live="polite">${text}</span>`;
}

function IssueDialog({ patientName, pdf, onCancel, onConfirm }) {
  const ref = useRef(null);
  useEffect(() => { ref.current.showModal(); }, []);
  // The print window opens inside the click, so that popup blockers let it through.
  const confirm = () => onConfirm(window.open('', '_blank'));
  return html`<dialog ref=${ref} onCancel=${onCancel} aria-labelledby="issue-title">
    <h2 id="issue-title">Émettre l'ordonnance${patientName ? ` de ${patientName}` : ''} ?</h2>
    <p>Elle reçoit un numéro et ne peut plus être modifiée. En cas d'erreur, vous pourrez l'annuler et la corriger.</p>
    ${pdf && html`<p class="small" style="margin-top:8px">Dans la fenêtre d'impression, choisissez « Enregistrer au format PDF ».</p>`}
    <div class="row"><button class="btn" onClick=${onCancel}>Continuer la rédaction</button>
      <button class="btn btn-primary" onClick=${confirm}>${pdf ? 'Émettre et exporter' : 'Imprimer et émettre'}</button></div>
  </dialog>`;
}

function CancelDialog({ onCancel, onConfirm }) {
  const ref = useRef(null);
  const [reasons, setReasons] = useState([]);
  const [reason, setReason] = useState('');
  const [other, setOther] = useState('');
  useEffect(() => {
    ref.current.showModal();
    Api.cancelReasons().then((d) => { setReasons(d.reasons); setReason(d.reasons[0] || ''); }).catch(() => {});
  }, []);
  const text = reason === 'autre' ? other.trim() : reason;
  return html`<dialog ref=${ref} onCancel=${onCancel} aria-labelledby="cancel-title">
    <h2 id="cancel-title">Annuler et corriger</h2>
    <p>L'ordonnance reste dans l'historique, marquée annulée. Un nouveau brouillon prérempli s'ouvre.</p>
    <label class="field" style="margin-top:14px">Motif
      <select value=${reason} onChange=${(e) => setReason(e.target.value)}>
        ${reasons.map((r) => html`<option key=${r} value=${r}>${r}</option>`)}<option value="autre">Autre motif…</option>
      </select></label>
    ${reason === 'autre' && html`<label class="field" style="margin-top:10px">Précisez<input value=${other} onInput=${(e) => setOther(e.target.value)} /></label>`}
    <div class="row"><button class="btn" onClick=${onCancel}>Retour</button>
      <button class="btn btn-primary" aria-disabled=${!text} onClick=${() => text && onConfirm(text)}>Annuler et corriger</button></div>
  </dialog>`;
}

function LockScreen({ onUnlocked }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const submit = async (e) => {
    e.preventDefault();
    try { await Api.unlock(password); onUnlocked(); } catch (err) { setError(err.message); }
  };
  return html`<div class="lock" role="dialog" aria-modal="true" aria-labelledby="lock-title">
    <form class="lock-card" onSubmit=${submit}>
      <${Icon} name="lock" /><h2 id="lock-title">Session verrouillée</h2>
      <p>Après 10 minutes d'inactivité, les données patient sont masquées. Votre brouillon est intact.</p>
      <label class="field">Mot de passe<input type="password" value=${password} onInput=${(e) => setPassword(e.target.value)} autofocus /></label>
      ${error && html`<p class="form-error">${error}</p>`}
      <div class="row"><a class="btn btn-ghost" href="/deconnexion">Changer d'utilisateur</a><button class="btn btn-primary" type="submit">Déverrouiller</button></div>
    </form></div>`;
}

const initial = JSON.parse(document.getElementById('initial-data').textContent);
render(html`<${App} initial=${initial} />`, document.getElementById('app'));
