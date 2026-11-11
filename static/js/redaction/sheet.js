/**
 * Live preview of the ordonnance. Same markup and stylesheet (static/css/sheet.css) as the
 * printed view (templates/print/ordonnance.html): the real sheet, scaled down to the panel width.
 */
import { html, useLayoutEffect, useRef, useState } from '../../vendor/preact-htm-standalone.module.js';
import { ageLabel, frDate, todayIso } from './ui.js';

const join = (parts, sep = ' ') => parts.filter(Boolean).join(sep);

export function Sheet({ content, patient, establishment, prescriber, number, focusLineId }) {
  const p = patient || {};
  const e = establishment || {};
  const a4 = e.paper_format === 'A4';
  const lines = content.lines.filter((line) => line.name);
  const facts = [
    ageLabel(p.birthdate, content.prescribed_on || todayIso()),
    p.sex === 'F' ? 'Féminin' : p.sex === 'M' ? 'Masculin' : '',
    p.weight_kg ? `${String(p.weight_kg).replace('.', ',')} kg${p.weighed_on ? ` (pesé le ${frDate(p.weighed_on)})` : ''}` : '',
    p.pregnancy === 'pregnant' ? 'Enceinte' : p.pregnancy === 'breastfeeding' ? 'Allaitement' : '',
  ];

  // Scale the real-size sheet to the panel, keeping its proportions.
  const frame = useRef(null);
  const sheet = useRef(null);
  const [fit, setFit] = useState({ scale: 1, height: 0 });
  useLayoutEffect(() => {
    const measure = () => {
      if (!frame.current || !sheet.current) return;
      const scale = Math.min(1, frame.current.clientWidth / sheet.current.offsetWidth);
      setFit({ scale, height: sheet.current.offsetHeight * scale });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(frame.current);
    observer.observe(sheet.current);
    return () => observer.disconnect();
  }, [a4]);

  return html`
    <div class="reading-title"><span>Aperçu ${a4 ? 'A4' : 'A5'}</span><span>${number ? `N° ${number}` : 'Brouillon'}</span></div>
    <div class="sheet-frame" ref=${frame} style=${{ height: `${fit.height}px` }}>
      <article class=${`rx-sheet ${a4 ? 'is-a4' : ''}`} ref=${sheet} style=${{ transform: `scale(${fit.scale})` }} aria-label="Aperçu de l'ordonnance">
        ${!number && html`<div class="rx-watermark" aria-hidden="true">BROUILLON</div>`}
        <header class="rx-head">
          <div class="rx-who">
            <strong>${join([prescriber.title, prescriber.first_name, prescriber.last_name])}</strong>
            ${prescriber.profession && html`<span class="rx-line-text">${prescriber.profession}</span>`}
            ${prescriber.order_number && html`<span class="rx-line-text">N° d'ordre : ${prescriber.order_number}</span>`}
            ${prescriber.identifier_value && html`<span class="rx-line-text">${prescriber.identifier_label || 'Identifiant'} : ${prescriber.identifier_value}</span>`}
            ${(prescriber.phone || e.phone) && html`<span class="rx-line-text">Tél. ${prescriber.phone || e.phone}</span>`}
          </div>
          <div class="rx-where">
            ${e.has_logo && html`<img src=${`/api/v1/prescriber/establishments/${e.id}/logo`} alt="" />`}
            <strong>${e.name || html`<span class="rx-placeholder">Établissement à choisir</span>`}</strong>
            ${e.type && html`<span class="rx-line-text">${e.type}</span>`}
            ${e.address && html`<span class="rx-line-text">${e.address}</span>`}
            ${e.identifier_value && html`<span class="rx-line-text">${e.identifier_label} : ${e.identifier_value}</span>`}
            ${e.free_text && html`<span class="rx-line-text">${e.free_text}</span>`}
          </div>
        </header>

        <div class="rx-meta"><span>Ordonnance n° <strong>${number || '…'}</strong></span>
          <span>Le ${frDate(content.prescribed_on || todayIso())}</span></div>

        <section class="rx-patient">
          <span class="rx-label">Patient</span>
          ${p.last_name ? html`<span class="rx-patient-name">${join([p.title, p.first_name, p.last_name])}</span>
            ${join(facts, ' · ') && html`<span class="rx-line-text rx-patient-facts">${join(facts, ' · ')}</span>`}`
          : html`<span class="rx-placeholder">Patient à choisir</span>`}
        </section>

        <span class="rx-label">Prescription</span>
        <ol class="rx-lines">
          ${lines.length === 0 && html`<li class="rx-placeholder" style="padding:2mm 0">Aucun médicament</li>`}
          ${lines.map((line) => {
            const parts = [
              (line.duration || content.duration) && `Durée : ${line.duration || content.duration}`,
              line.quantity && `Quantité : ${line.quantity}`,
              (line.renewal || content.renewal) && `Renouvellement : ${line.renewal || content.renewal}`,
            ];
            return html`<li class=${`rx-item ${focusLineId === line.line_id ? 'is-highlight' : ''}`} key=${line.line_id}><div>
              <span class="rx-med">${line.name}${line.dosage && ` ${line.dosage}`}${line.form && `, ${line.form.toLowerCase()}`}</span>
              ${line.substances && line.substances.length > 0 && html` <span class="rx-dci">(${line.substances.join(' + ').toLowerCase()})</span>`}
              <div class="rx-posology">${line.posology || html`<span class="rx-placeholder">Posologie à préciser</span>`}</div>
              ${join(parts, ' · ') && html`<div class="rx-small">${join(parts, ' · ')}</div>`}
              ${line.note && html`<div class="rx-small">${line.note}</div>`}
            </div></li>`;
          })}
        </ol>

        ${content.lab_results && html`<section class="rx-block"><span class="rx-label">Bilan biologique</span><div>${content.lab_results}</div></section>`}
        ${content.general_note && html`<section class="rx-block"><span class="rx-label">Recommandations</span><div>${content.general_note}</div></section>`}

        <div class="rx-sign">
          <div class="rx-stamp">Signature et cachet</div>
          <div class="rx-signer">${join([prescriber.title, prescriber.first_name, prescriber.last_name])}
            ${prescriber.profession && html`<small>${prescriber.profession}</small>`}</div>
        </div>
        <footer class="rx-foot"><span>${number ? `N° ${number}` : "Numéro attribué à l'émission"}</span>
          <span>${number ? 'Émise' : 'Brouillon'}</span></footer>
      </article>
    </div>`;
}
