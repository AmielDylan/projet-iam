/** Live A5/A4 preview of the ordonnance, built from the draft. The printed sheet comes from the server snapshot. */
import { html } from '../../vendor/preact-htm-standalone.module.js';
import { ageLabel, frDate, todayIso } from './ui.js';

export function Sheet({ content, patient, establishment, prescriber, number, focusLineId }) {
  const p = patient || {};
  const e = establishment || {};
  const dci = (line) => (line.substances && line.substances.length ? ` (${line.substances.join(', ').toLowerCase()})` : '');
  const lines = content.lines.filter((line) => line.name);
  const facts = [
    ageLabel(p.birthdate, content.prescribed_on || todayIso()),
    p.sex === 'F' ? 'Féminin' : p.sex === 'M' ? 'Masculin' : '',
    p.weight_kg ? `${String(p.weight_kg).replace('.', ',')} kg` : '',
    p.pregnancy === 'pregnant' ? 'Enceinte' : p.pregnancy === 'breastfeeding' ? 'Allaitement' : '',
  ].filter(Boolean).join(' · ');

  return html`
    <div class="reading-title"><span>Aperçu ${e.paper_format || 'A5'}</span><span>${number ? `N° ${number}` : 'Brouillon'}</span></div>
    <div class="sheet" aria-label="Aperçu de l'ordonnance">
      ${!number && html`<div class="wm" aria-hidden="true">BROUILLON</div>`}
      <div class="h">
        <div><strong>${e.name || 'Établissement à choisir'}</strong>${e.type}${e.type && html`<br />`}${e.address}${e.address && html`<br />`}${e.phone}</div>
        <div style="text-align:right"><strong>${[prescriber.title, prescriber.first_name, prescriber.last_name].filter(Boolean).join(' ')}</strong>
          ${prescriber.profession}${prescriber.order_number && html`<br />N° d'ordre ${prescriber.order_number}`}</div>
      </div>
      <div class="pat">
        <span>${p.last_name ? html`<b>${[p.title, p.first_name, p.last_name].filter(Boolean).join(' ')}</b>${facts && `, ${facts}`}` : html`<i class="muted">Patient à choisir</i>`}</span>
        <span>Le ${frDate(content.prescribed_on || todayIso())}</span>
      </div>
      ${lines.map((line) => html`
        <div class=${`m ${focusLineId === line.line_id ? 'is-hl' : ''}`} key=${line.line_id}>
          <b>${line.name}${line.dosage && ` ${line.dosage}`}${dci(line)}</b><span class="q">${line.quantity}</span>
          <span class="x">${line.posology || html`<i class="muted">Posologie à préciser</i>`}${line.duration && ` · pendant ${line.duration}`}</span>
        </div>`)}
      ${(content.duration || content.renewal) && html`<div class="glob">
        ${content.duration && `Traitement pour ${content.duration}`}${content.duration && content.renewal && ', '}${content.renewal && `renouvellement ${content.renewal}`}</div>`}
      ${content.lab_results && html`<div class="bio">Bilan biologique : ${content.lab_results}</div>`}
      ${content.general_note && html`<div class="bio">${content.general_note}</div>`}
      <div class="foot"><div class="cachet">Cachet</div>
        <div class="sign"><div class="l"></div>${[prescriber.first_name, prescriber.last_name].filter(Boolean).join(' ')}
          <div class="no">${number ? `Ordonnance n° ${number}` : "Numéro attribué à l'émission"}</div></div></div>
    </div>`;
}
