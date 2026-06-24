/**
 * Protected prescription workspace for V3.1 ordonnance classique.
 */
import Config from './config.js';
import { debounce, escapeHtml, announceToScreenReader } from './utils.js';

const LAYOUT_STORAGE_KEY = 'iam-prescription-layout-width';

class PrescriptionWorkspace {
    constructor(root) {
        this.root = root;
        this.medications = [];
        this.alerts = [];
        this.analysis = { can_print: false, blocking_alerts_count: 0 };
        this.draggedId = null;
        this.analysisSeq = 0;
        this.latestAppliedSeq = 0;
        this.prescriber = this.readInitialProfile();
        this.establishments = this.readInitialEstablishments();
        this.selectedEstablishment = this.establishments.find(item => item.is_active) || null;
        this.elements = {
            layout: root.querySelector('[data-prescription-layout]'),
            establishment: root.querySelector('[data-establishment-form]'),
            establishmentSelect: root.querySelector('[data-establishment-select]'),
            establishmentStatus: root.querySelector('[data-establishment-status]'),
            saveEstablishment: root.querySelector('[data-save-establishment]'),
            patient: root.querySelector('[data-patient-form]'),
            patientSearch: root.querySelector('[data-patient-search]'),
            patientSuggestions: root.querySelector('[data-patient-suggestions]'),
            medicationList: root.querySelector('[data-medication-list]'),
            addMedication: root.querySelector('[data-add-medication]'),
            print: root.querySelector('[data-print-prescription]'),
            alerts: root.querySelector('[data-prescription-alerts]'),
            preview: root.querySelector('[data-prescription-preview]'),
            printMessage: root.querySelector('[data-print-message]'),
            analysisStatus: root.querySelector('[data-analysis-status]'),
            resizer: root.querySelector('[data-rx-resizer]')
        };

        this.scheduleAnalysis = debounce(() => this.analyze(), 450);
        this.searchPatient = debounce(() => this.fetchPatients(), 250);
        this.bindEvents();
        this.restoreLayout();
        this.addMedication();
        this.setDefaultDate();
        this.render();
    }

    readInitialProfile() {
        try {
            return JSON.parse(this.root.dataset.prescriberProfile || '{}') || {};
        } catch {
            return {};
        }
    }

    readInitialEstablishments() {
        try {
            return JSON.parse(this.root.dataset.establishments || '[]') || [];
        } catch {
            return [];
        }
    }

    bindEvents() {
        this.elements.addMedication?.addEventListener('click', () => this.addMedication());
        this.elements.print?.addEventListener('click', () => this.print());
        this.elements.resizer?.addEventListener('pointerdown', (event) => this.startResize(event));
        this.elements.saveEstablishment?.addEventListener('click', () => this.saveEstablishment());
        this.elements.establishmentSelect?.addEventListener('change', () => this.applyEstablishmentSelection());

        this.root.addEventListener('input', (event) => {
            const input = event.target;
            if (!(input instanceof HTMLElement)) return;

            if (input.dataset.establishmentField !== undefined) {
                this.selectedEstablishment = this.formData(this.elements.establishment);
                this.renderPreview();
            }

            if (input.closest('[data-patient-form]')) {
                if (input.name === 'patient_birthdate') this.updateAge();
                if (input.dataset.patientSearch !== undefined) this.searchPatient();
                this.renderPreview();
            }
            if (input.dataset.medField) {
                this.updateMedication(input);
                this.renderPreview();
                this.scheduleAnalysis();
            }
        });

        this.root.addEventListener('change', (event) => {
            const input = event.target;
            if (!(input instanceof HTMLElement)) return;
            if (input.dataset.medField) {
                this.updateMedication(input);
                this.renderPreview();
                this.scheduleAnalysis();
            }
            if (input.name === 'patient_birthdate') this.updateAge();
        });

        this.root.addEventListener('click', (event) => {
            const patientButton = event.target.closest('[data-patient-result]');
            if (patientButton) {
                this.applyPatient(patientButton.dataset.patientResult);
                return;
            }

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
        this.updatePrintState();
    }

    removeMedication(id) {
        if (this.medications.length === 1) {
            this.medications[0] = this.emptyMedication(id);
        } else {
            this.medications = this.medications.filter(item => item.client_id !== id);
        }
        this.render();
        this.scheduleAnalysis();
    }

    emptyMedication(id) {
        return {
            client_id: id,
            medication_id: null,
            name: '',
            dosage: '',
            form: '',
            substances: [],
            posology: '',
            box_count: '',
            qsp: '',
            renewal: '',
            note: '',
            is_free_text: false
        };
    }

    duplicateMedication(id) {
        const item = this.medications.find(med => med.client_id === id);
        if (!item) return;
        this.addMedication({ ...item, client_id: undefined });
        this.scheduleAnalysis();
    }

    forceFreeText(id) {
        const item = this.medications.find(med => med.client_id === id);
        if (!item) return;
        item.medication_id = null;
        item.substances = [];
        item.is_free_text = true;
        this.render();
        this.scheduleAnalysis();
    }

    reorderMedication(sourceId, targetId) {
        const sourceIndex = this.medications.findIndex(item => item.client_id === sourceId);
        const targetIndex = this.medications.findIndex(item => item.client_id === targetId);
        if (sourceIndex < 0 || targetIndex < 0) return;
        const [item] = this.medications.splice(sourceIndex, 1);
        this.medications.splice(targetIndex, 0, item);
        this.renderMedicationList();
        this.renderPreview();
        this.scheduleAnalysis();
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

        const params = new URLSearchParams({ q: query, limit: '10' });
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
                this.scheduleAnalysis();
            });
            return;
        }

        container.innerHTML = results.map(result => `
            <button type="button" class="rx-suggestion" data-med-result="${result.id}">
                <span class="rx-suggestion__name">${this.highlightPrefix(result.name, query)}</span>
                <span class="rx-suggestion__meta">
                    ${result.dosage ? `<span class="rx-suggestion__badge rx-suggestion__badge--dose">${escapeHtml(result.dosage)}</span>` : ''}
                    ${result.form ? `<span class="rx-suggestion__badge rx-suggestion__badge--form">${escapeHtml(result.form)}</span>` : ''}
                </span>
                <span class="rx-suggestion__substances">${escapeHtml(result.substances_label || 'Substances non renseignées')}</span>
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
                this.scheduleAnalysis();
            });
        });
    }, 250);

    highlightPrefix(value, query) {
        const text = String(value || '');
        const normalized = text.toLocaleLowerCase('fr-FR');
        const prefix = String(query || '').toLocaleLowerCase('fr-FR');
        if (!prefix || !normalized.startsWith(prefix)) return escapeHtml(text);
        return `<strong>${escapeHtml(text.slice(0, query.length))}</strong>${escapeHtml(text.slice(query.length))}`;
    }

    async fetchPatients() {
        const query = this.elements.patientSearch?.value?.trim() || '';
        const container = this.elements.patientSuggestions;
        if (!container || query.length < 2) {
            if (container) container.innerHTML = '';
            return;
        }
        const params = new URLSearchParams({ q: query });
        const response = await fetch(`${Config.api.patientSearch}?${params.toString()}`);
        const data = await response.json();
        this.patientResults = data.results || [];
        if (!this.patientResults.length) {
            container.innerHTML = '';
            return;
        }
        container.innerHTML = this.patientResults.map(patient => `
            <button type="button" class="rx-suggestion" data-patient-result="${patient.id}">
                <span class="rx-suggestion__name">${escapeHtml([patient.patient_last_name, patient.patient_first_name].filter(Boolean).join(' '))}</span>
                <span class="rx-suggestion__substances">${escapeHtml([patient.patient_birthdate, patient.patient_address].filter(Boolean).join(' · '))}</span>
            </button>
        `).join('');
    }

    applyPatient(id) {
        const patient = (this.patientResults || []).find(item => String(item.id) === String(id));
        if (!patient || !this.elements.patient) return;
        Object.entries(patient).forEach(([key, value]) => {
            const input = this.elements.patient.querySelector(`[name="${key}"]`);
            if (input) input.value = value ?? '';
        });
        this.elements.patientSuggestions.innerHTML = '';
        this.updateAge();
        this.renderPreview();
    }

    async analyze() {
        const items = this.medications.filter(item => item.name.trim());
        if (!items.length) {
            this.alerts = [];
            this.analysis = { can_print: false, blocking_alerts_count: 0 };
            this.renderAlerts();
            this.updatePrintState('Ajoutez au moins deux médicaments pour déclencher l’analyse IAM.');
            return null;
        }
        if (items.length === 1) {
            this.alerts = items[0].medication_id ? [] : [{
                type: 'unknown_medication',
                severity: 'info',
                message: `${items[0].name} n'est pas sélectionné dans le catalogue IAM.`
            }];
            this.analysis = { can_print: true, blocking_alerts_count: 0 };
            this.renderAlerts();
            this.updatePrintState('Un seul médicament saisi: aucune paire IAM à analyser.');
            this.setAnalysisStatus(this.alerts.length ? 'Info' : 'OK');
            return { success: true, alerts: this.alerts, summary: this.analysis };
        }

        const seq = ++this.analysisSeq;
        this.setAnalysisStatus('Analyse...');
        try {
            const response = await fetch(Config.api.prescriptionAnalyze, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({ items })
            });
            const result = await response.json();
            if (seq < this.latestAppliedSeq) return result;
            this.latestAppliedSeq = seq;
            this.alerts = result.alerts || [];
            this.analysis = result.summary || { can_print: false, blocking_alerts_count: 0 };
            this.renderAlerts();
            this.updatePrintState();
            this.setAnalysisStatus(this.alerts.length ? `${this.alerts.length} alerte(s)` : 'OK');
            announceToScreenReader(`${this.alerts.length} alerte(s) sur l'ordonnance.`);
            return result;
        } catch {
            if (seq < this.latestAppliedSeq) return null;
            this.analysis = { can_print: false, blocking_alerts_count: 1 };
            this.setAnalysisStatus('Erreur');
            this.updatePrintState("Analyse IAM indisponible. L'impression est bloquée.");
            return null;
        }
    }

    async print() {
        const result = await this.analyze();
        if (!result || !this.analysis.can_print) return;
        await this.savePatient();
        window.print();
    }

    async savePatient() {
        const patient = this.formData(this.elements.patient);
        if (!patient.patient_first_name && !patient.patient_last_name) return;
        await fetch(Config.api.patients, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify(patient)
        });
    }

    setAnalysisStatus(text) {
        if (this.elements.analysisStatus) this.elements.analysisStatus.textContent = text;
    }

    updatePrintState(customMessage = '') {
        const items = this.medications.filter(item => item.name.trim());
        const canPrint = items.length >= 1 && Boolean(this.analysis.can_print);
        if (this.elements.print) this.elements.print.disabled = !canPrint;
        if (!this.elements.printMessage) return;
        if (customMessage) {
            this.elements.printMessage.textContent = customMessage;
        } else if (items.length < 2) {
            this.elements.printMessage.textContent = 'Ajoutez au moins deux médicaments pour déclencher l’analyse IAM.';
        } else if (!this.analysis.can_print) {
            this.elements.printMessage.textContent = 'Corrigez les contre-indications ou associations déconseillées avant impression.';
        } else {
            this.elements.printMessage.textContent = 'Analyse IAM compatible avec l’impression.';
        }
    }

    render() {
        this.renderMedicationList();
        this.renderEstablishmentSelect();
        this.renderAlerts();
        this.renderPreview();
    }

    renderEstablishmentSelect() {
        const select = this.elements.establishmentSelect;
        if (!select) return;
        const current = String(this.selectedEstablishment?.id || '');
        select.innerHTML = [
            '<option value="">Nouvel établissement</option>',
            ...this.establishments.map(item => `<option value="${item.id}" ${String(item.id) === current ? 'selected' : ''}>${escapeHtml(item.name)}</option>`)
        ].join('');
        if (current) select.value = current;
        this.fillEstablishmentForm(this.selectedEstablishment || {});
    }

    applyEstablishmentSelection() {
        const value = this.elements.establishmentSelect?.value || '';
        this.selectedEstablishment = this.establishments.find(item => String(item.id) === value) || null;
        this.fillEstablishmentForm(this.selectedEstablishment || {});
        this.renderPreview();
    }

    fillEstablishmentForm(establishment) {
        if (!this.elements.establishment) return;
        ['name', 'type', 'address', 'phone', 'email', 'identifier_value', 'free_text'].forEach((field) => {
            const input = this.elements.establishment.querySelector(`[name="${field}"]`);
            if (input) input.value = establishment?.[field] || '';
        });
    }

    async saveEstablishment() {
        const payload = this.formData(this.elements.establishment);
        const id = payload.establishment_id;
        if (!payload.name?.trim()) {
            this.setEstablishmentStatus("Nom d'établissement requis.", false);
            return;
        }
        const response = await fetch(id ? `${Config.api.prescriberEstablishments}/${id}` : Config.api.prescriberEstablishments, {
            method: id ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok || data.success === false) {
            this.setEstablishmentStatus(data.message || data.error || "Établissement non enregistré.", false);
            return;
        }
        const saved = data.establishment;
        const index = this.establishments.findIndex(item => String(item.id) === String(saved.id));
        if (index >= 0) this.establishments[index] = saved;
        else this.establishments.push(saved);
        this.selectedEstablishment = saved;
        this.setEstablishmentStatus('Établissement enregistré.', true);
        this.render();
    }

    setEstablishmentStatus(message, success) {
        if (!this.elements.establishmentStatus) return;
        this.elements.establishmentStatus.textContent = message;
        this.elements.establishmentStatus.classList.toggle('is-error', !success);
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
                        <input type="text" data-med-field="name" value="${escapeHtml(item.name)}" placeholder="Nom commercial ou DCI" autocomplete="off">
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
                    <button type="button" data-med-action="duplicate" title="Dupliquer" aria-label="Dupliquer">Copier</button>
                    <button type="button" data-med-action="free" title="Saisie libre" aria-label="Saisie libre">Libre</button>
                    <button type="button" class="rx-icon-button" data-med-action="remove" title="Supprimer" aria-label="Supprimer">
                        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M9 3h6l1 2h4v2H4V5h4l1-2Zm-2 6h10l-.7 11H7.7L7 9Zm3 2v7h2v-7h-2Zm4 0v7h2v-7h-2Z"/></svg>
                    </button>
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
        const prescriber = this.prescriber || {};
        const establishment = this.selectedEstablishment || this.formData(this.elements.establishment) || {};
        const patient = this.formData(this.elements.patient);
        const patientLine = [patient.patient_title, patient.patient_first_name, patient.patient_last_name].filter(Boolean).join(' ');
        const age = this.formatAge(patient.patient_birthdate);
        const weight = patient.patient_weight ? `${patient.patient_weight} kg` : '';

        preview.innerHTML = `
            <div class="rx-prescription-page">
                <header class="rx-prescription-head">
                    <div>
                        <strong>${escapeHtml(establishment.name || prescriber.organization || 'Nom du cabinet')}</strong>
                        <p>${escapeHtml(establishment.type || prescriber.profession || '')}</p>
                        <p>${escapeHtml(establishment.address || prescriber.address || '')}</p>
                        <p>${escapeHtml([establishment.phone || prescriber.phone, establishment.email || prescriber.email].filter(Boolean).join(' - '))}</p>
                        <p>${escapeHtml(establishment.free_text || '')}</p>
                    </div>
                    <div>
                        <p>${escapeHtml([prescriber.title, prescriber.first_name, prescriber.last_name].filter(Boolean).join(' '))}</p>
                        <p>${escapeHtml(this.identifierLine(establishment.identifier_label || prescriber.identifier_label, establishment.identifier_value || prescriber.identifier_value))}</p>
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

    formData(form) {
        const data = {};
        if (!form) return data;
        new FormData(form).forEach((value, key) => { data[key] = String(value); });
        return data;
    }

    setDefaultDate() {
        const date = this.root.querySelector('[name="prescription_date"]');
        if (date && !date.value) date.valueAsDate = new Date();
    }

    updateAge() {
        const ageInput = this.root.querySelector('[name="patient_age"]');
        const birth = this.root.querySelector('[name="patient_birthdate"]');
        if (ageInput) ageInput.value = this.formatAge(birth?.value || '');
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

    restoreLayout() {
        const width = Number(localStorage.getItem(LAYOUT_STORAGE_KEY));
        if (this.elements.layout && width >= 35 && width <= 72) {
            this.elements.layout.style.setProperty('--rx-form-width', `${width}%`);
        }
    }

    startResize(event) {
        if (!this.elements.layout) return;
        event.preventDefault();
        this.elements.resizer.setPointerCapture?.(event.pointerId);
        const move = (moveEvent) => {
            const rect = this.elements.layout.getBoundingClientRect();
            const percent = ((moveEvent.clientX - rect.left) / rect.width) * 100;
            const clamped = Math.max(35, Math.min(72, percent));
            this.elements.layout.style.setProperty('--rx-form-width', `${clamped}%`);
            localStorage.setItem(LAYOUT_STORAGE_KEY, String(Math.round(clamped)));
        };
        const stop = () => {
            window.removeEventListener('pointermove', move);
            window.removeEventListener('pointerup', stop);
        };
        window.addEventListener('pointermove', move);
        window.addEventListener('pointerup', stop);
    }
}

export default PrescriptionWorkspace;
