/**
 * Prescription workspace for V3 ordonnance classique.
 */
import Config from './config.js';
import { debounce, escapeHtml, announceToScreenReader } from './utils.js';

const STORAGE_KEY = 'iam-prescriber-profile';

class PrescriptionWorkspace {
    constructor(root) {
        this.root = root;
        this.medications = [];
        this.alerts = [];
        this.draggedId = null;
        this.elements = {
            prescriber: root.querySelector('[data-prescriber-form]'),
            patient: root.querySelector('[data-patient-form]'),
            medicationList: root.querySelector('[data-medication-list]'),
            addMedication: root.querySelector('[data-add-medication]'),
            analyze: root.querySelector('[data-analyze-prescription]'),
            print: root.querySelector('[data-print-prescription]'),
            alerts: root.querySelector('[data-prescription-alerts]'),
            preview: root.querySelector('[data-prescription-preview]')
        };

        this.loadProfile();
        this.bindEvents();
        this.addMedication();
        this.render();
    }

    bindEvents() {
        this.elements.addMedication?.addEventListener('click', () => this.addMedication());
        this.elements.analyze?.addEventListener('click', () => this.analyze());
        this.elements.print?.addEventListener('click', () => this.print());

        this.root.addEventListener('input', (event) => {
            const input = event.target;
            if (!(input instanceof HTMLElement)) return;

            if (input.closest('[data-prescriber-form]')) {
                this.saveProfile();
                this.renderPreview();
            }
            if (input.closest('[data-patient-form]')) {
                this.renderPreview();
            }
            if (input.dataset.medField) {
                this.updateMedication(input);
                this.renderPreview();
            }
        });

        this.root.addEventListener('change', (event) => {
            const input = event.target;
            if (!(input instanceof HTMLElement)) return;
            if (input.closest('[data-prescriber-form]')) this.saveProfile();
            if (input.dataset.medField) {
                this.updateMedication(input);
                this.renderPreview();
            }
        });

        this.root.addEventListener('click', (event) => {
            const button = event.target.closest('[data-med-action]');
            if (!button) return;
            const id = button.closest('[data-med-id]')?.dataset.medId;
            if (!id) return;
            const action = button.dataset.medAction;
            if (action === 'remove') this.removeMedication(id);
            if (action === 'duplicate') this.duplicateMedication(id);
            if (action === 'free') this.forceFreeText(id);
        });

        this.root.addEventListener('dragstart', (event) => {
            const item = event.target.closest('[data-med-id]');
            if (!item) return;
            this.draggedId = item.dataset.medId;
            item.classList.add('is-dragging');
        });

        this.root.addEventListener('dragend', (event) => {
            event.target.closest('[data-med-id]')?.classList.remove('is-dragging');
            this.draggedId = null;
        });

        this.root.addEventListener('dragover', (event) => {
            const item = event.target.closest('[data-med-id]');
            if (!item || !this.draggedId || item.dataset.medId === this.draggedId) return;
            event.preventDefault();
            this.reorderMedication(this.draggedId, item.dataset.medId);
        });
    }

    addMedication(seed = {}) {
        this.medications.push({
            client_id: seed.client_id || `med-${Date.now()}-${Math.random().toString(16).slice(2)}`,
            medication_id: seed.medication_id || null,
            name: seed.name || '',
            dosage: seed.dosage || '',
            form: seed.form || '',
            substances: seed.substances || [],
            posology: seed.posology || '',
            box_count: seed.box_count || '',
            qsp: seed.qsp || '',
            renewal: seed.renewal || '',
            note: seed.note || '',
            is_free_text: Boolean(seed.is_free_text)
        });
        this.render();
    }

    removeMedication(id) {
        if (this.medications.length === 1) {
            this.medications[0] = { ...this.medications[0], name: '', dosage: '', form: '', substances: [], medication_id: null, posology: '', box_count: '', qsp: '', renewal: '', note: '', is_free_text: false };
        } else {
            this.medications = this.medications.filter(item => item.client_id !== id);
        }
        this.render();
    }

    duplicateMedication(id) {
        const item = this.medications.find(med => med.client_id === id);
        if (!item) return;
        this.addMedication({ ...item, client_id: undefined });
    }

    forceFreeText(id) {
        const item = this.medications.find(med => med.client_id === id);
        if (!item) return;
        item.medication_id = null;
        item.substances = [];
        item.is_free_text = true;
        this.render();
    }

    reorderMedication(sourceId, targetId) {
        const sourceIndex = this.medications.findIndex(item => item.client_id === sourceId);
        const targetIndex = this.medications.findIndex(item => item.client_id === targetId);
        if (sourceIndex < 0 || targetIndex < 0) return;
        const [item] = this.medications.splice(sourceIndex, 1);
        this.medications.splice(targetIndex, 0, item);
        this.renderMedicationList();
        this.renderPreview();
    }

    updateMedication(input) {
        const item = this.medications.find(med => med.client_id === input.closest('[data-med-id]')?.dataset.medId);
        if (!item) return;
        const field = input.dataset.medField;
        if (field === 'box_count') {
            item[field] = input.value ? Number(input.value) : '';
        } else {
            item[field] = input.value;
        }
        if (field === 'name') {
            item.medication_id = null;
            item.substances = [];
            item.is_free_text = Boolean(input.value.trim());
            this.searchMedication(input, item);
        }
    }

    searchMedication = debounce(async (input, item) => {
        const query = input.value.trim();
        const container = input.closest('.rx-medication-line')?.querySelector('[data-med-suggestions]');
        if (!container || query.length < 2) {
            if (container) container.innerHTML = '';
            return;
        }

        const params = new URLSearchParams({ q: query, limit: '8' });
        const response = await fetch(`${Config.api.medicationSearch}?${params.toString()}`);
        const data = await response.json();
        const results = data.results || [];

        if (!results.length) {
            container.innerHTML = `<button type="button" class="rx-suggestion rx-suggestion--free" data-free-suggestion>Utiliser "${escapeHtml(query)}"</button>`;
            container.querySelector('[data-free-suggestion]')?.addEventListener('click', () => {
                item.name = query;
                item.is_free_text = true;
                container.innerHTML = '';
                this.render();
            });
            return;
        }

        container.innerHTML = results.map(result => `
            <button type="button" class="rx-suggestion" data-med-result="${result.id}">
                <span class="rx-suggestion__name">${escapeHtml([result.name, result.dosage, result.form].filter(Boolean).join(' '))}</span>
                <span class="rx-suggestion__substances">${escapeHtml(result.substances_label || 'Substances non renseignees')}</span>
            </button>
        `).join('');

        container.querySelectorAll('[data-med-result]').forEach(button => {
            button.addEventListener('click', () => {
                const selected = results.find(result => String(result.id) === button.dataset.medResult);
                if (!selected) return;
                item.medication_id = selected.id;
                item.name = selected.name;
                item.dosage = selected.dosage;
                item.form = selected.form;
                item.substances = selected.substances || [];
                item.box_count = selected.box_count || item.box_count || '';
                item.is_free_text = false;
                container.innerHTML = '';
                this.render();
            });
        });
    }, 250);

    async analyze() {
        const items = this.medications.filter(item => item.name.trim());
        const response = await fetch(Config.api.prescriptionAnalyze, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({ items })
        });
        const result = await response.json();
        this.alerts = result.alerts || [];
        this.renderAlerts();
        announceToScreenReader(`${this.alerts.length} alerte(s) sur l'ordonnance.`);
        return result;
    }

    async print() {
        await this.analyze();
        window.print();
    }

    render() {
        this.renderMedicationList();
        this.renderAlerts();
        this.renderPreview();
    }

    renderMedicationList() {
        const list = this.elements.medicationList;
        if (!list) return;
        list.innerHTML = this.medications.map((item, index) => `
            <div class="rx-medication-line" data-med-id="${item.client_id}" draggable="true">
                <div class="rx-medication-line__index">${index + 1}</div>
                <div class="rx-medication-line__main">
                    <label class="rx-field">
                        <span>Médicament</span>
                        <input type="text" data-med-field="name" value="${escapeHtml(item.name)}" placeholder="Nom commercial ou DCI">
                    </label>
                    <div class="rx-suggestions" data-med-suggestions></div>
                    <div class="rx-medication-line__grid">
                        <label class="rx-field">
                            <span>Dosage</span>
                            <input type="text" data-med-field="dosage" value="${escapeHtml(item.dosage)}">
                        </label>
                        <label class="rx-field">
                            <span>Forme</span>
                            <input type="text" data-med-field="form" value="${escapeHtml(item.form)}">
                        </label>
                        <label class="rx-field">
                            <span>Boîtes</span>
                            <input type="number" min="0" step="1" data-med-field="box_count" value="${item.box_count || ''}">
                        </label>
                    </div>
                    <label class="rx-field">
                        <span>Posologie</span>
                        <textarea data-med-field="posology" rows="2" placeholder="Texte libre">${escapeHtml(item.posology)}</textarea>
                    </label>
                    <div class="rx-medication-line__grid">
                        <label class="rx-field">
                            <span>QSP</span>
                            <input type="text" data-med-field="qsp" value="${escapeHtml(item.qsp)}" placeholder="1 mois">
                        </label>
                        <label class="rx-field">
                            <span>AR</span>
                            <input type="text" data-med-field="renewal" value="${escapeHtml(item.renewal)}" placeholder="1 fois">
                        </label>
                        <label class="rx-field">
                            <span>Note</span>
                            <input type="text" data-med-field="note" value="${escapeHtml(item.note)}">
                        </label>
                    </div>
                    <div class="rx-line-status">${this.renderMedicationStatus(item)}</div>
                </div>
                <div class="rx-medication-line__actions">
                    <button type="button" data-med-action="duplicate" title="Dupliquer">Copier</button>
                    <button type="button" data-med-action="free" title="Saisie libre">Libre</button>
                    <button type="button" data-med-action="remove" title="Supprimer">Suppr.</button>
                </div>
            </div>
        `).join('');
    }

    renderMedicationStatus(item) {
        if (!item.name) return '';
        if (item.is_free_text) return '<span class="rx-status rx-status--info">Saisie libre</span>';
        if (item.medication_id) return '<span class="rx-status rx-status--ok">Catalogue</span>';
        return '<span class="rx-status rx-status--info">Non sélectionné</span>';
    }

    renderAlerts() {
        const container = this.elements.alerts;
        if (!container) return;
        if (!this.alerts.length) {
            container.innerHTML = '<p class="rx-empty">Aucune alerte pour le moment.</p>';
            return;
        }
        container.innerHTML = this.alerts.map(alert => `
            <div class="rx-alert rx-alert--${escapeHtml(alert.severity || 'info')}">
                <span class="rx-alert__type">${escapeHtml(this.alertLabel(alert.type))}</span>
                <p>${escapeHtml(alert.message || '')}</p>
            </div>
        `).join('');
    }

    renderPreview() {
        const preview = this.elements.preview;
        if (!preview) return;
        const prescriber = this.formData(this.elements.prescriber);
        const patient = this.formData(this.elements.patient);
        const patientLine = [patient.patient_title, patient.patient_first_name, patient.patient_last_name].filter(Boolean).join(' ');
        const age = this.formatAge(patient.patient_birthdate);
        const weight = patient.patient_weight ? `${patient.patient_weight} kg` : '';

        preview.innerHTML = `
            <div class="rx-prescription-page">
                <header class="rx-prescription-head">
                    <div>
                        <strong>${escapeHtml(prescriber.organization || 'Nom du cabinet')}</strong>
                        <p>${escapeHtml(prescriber.profession || '')}</p>
                        <p>${escapeHtml(prescriber.address || '')}</p>
                        <p>${escapeHtml([prescriber.phone, prescriber.email].filter(Boolean).join(' - '))}</p>
                    </div>
                    <div>
                        <p>${escapeHtml([prescriber.title, prescriber.first_name, prescriber.last_name].filter(Boolean).join(' '))}</p>
                        <p>${escapeHtml(this.identifierLine(prescriber.identifier_label, prescriber.identifier_value))}</p>
                        <p>${escapeHtml(this.identifierLine(prescriber.secondary_identifier_label, prescriber.secondary_identifier_value))}</p>
                    </div>
                </header>
                <div class="rx-prescription-patient">
                    <span>Patient : ${escapeHtml([patientLine, age, weight].filter(Boolean).join(', '))}</span>
                    <span>Date : ${escapeHtml(patient.prescription_date || new Date().toLocaleDateString('fr-FR'))}</span>
                </div>
                <section class="rx-prescription-meds">
                    ${this.medications.filter(item => item.name.trim()).map(item => `
                        <article>
                            <div>
                                <strong>${escapeHtml(item.name.toUpperCase())}</strong>
                                <span>${escapeHtml([item.dosage, item.form].filter(Boolean).join(' '))}</span>
                            </div>
                            <p>${escapeHtml(item.posology || '')}</p>
                            <span>${item.box_count ? escapeHtml(`${item.box_count} boîte(s)`) : ''}</span>
                            <small>${escapeHtml([item.qsp ? `QSP ${item.qsp}` : '', item.renewal ? `AR ${item.renewal}` : '', item.note].filter(Boolean).join(' - '))}</small>
                        </article>
                    `).join('')}
                </section>
                <footer class="rx-prescription-foot">
                    <p>${escapeHtml(patient.clinical_notes || '')}</p>
                    <strong>${escapeHtml([prescriber.title, prescriber.last_name].filter(Boolean).join(' '))}</strong>
                </footer>
            </div>
        `;
    }

    loadProfile() {
        try {
            const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
            Object.entries(data).forEach(([name, value]) => {
                const input = this.root.querySelector(`[name="${name}"]`);
                if (input) input.value = value;
            });
        } catch {
            // Ignore corrupted local storage.
        }
        const date = this.root.querySelector('[name="prescription_date"]');
        if (date && !date.value) date.valueAsDate = new Date();
    }

    saveProfile() {
        const data = this.formData(this.elements.prescriber);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }

    formData(form) {
        const data = {};
        if (!form) return data;
        new FormData(form).forEach((value, key) => { data[key] = String(value); });
        return data;
    }

    formatAge(value) {
        if (!value) return '';
        const birth = new Date(value);
        if (Number.isNaN(birth.getTime())) return '';
        const today = new Date();
        let months = (today.getFullYear() - birth.getFullYear()) * 12 + today.getMonth() - birth.getMonth();
        if (today.getDate() < birth.getDate()) months -= 1;
        if (months < 24) return `${Math.max(months, 0)} mois`;
        return `${Math.floor(months / 12)} ans`;
    }

    identifierLine(label, value) {
        if (!label && !value) return '';
        return `${label || 'Identifiant'} : ${value || ''}`;
    }

    alertLabel(type) {
        return {
            interaction: 'Interaction',
            therapeutic_duplicate: 'Doublon',
            unknown_medication: 'Information'
        }[type] || 'Alerte';
    }
}

export default PrescriptionWorkspace;
