(function () {
    const h = React.createElement;

    const api = {
        session: '/api/v1/auth/session',
        login: '/api/v1/auth/login',
        register: '/api/v1/auth/register',
        changePassword: '/api/v1/auth/change-password',
        requests: '/api/v1/accounts/requests',
        profile: '/api/v1/prescriber/profile',
        establishments: '/api/v1/prescriber/establishments',
        adminEstablishments: '/api/v1/admin/establishments',
        professions: '/api/v1/professions'
    };

    function cx(...parts) {
        return parts.filter(Boolean).join(' ');
    }

    const registerFieldLabels = {
        last_name: 'Noms',
        first_name: 'Prénoms',
        birthdate: 'Date de naissance',
        profession: 'Profession',
        order_number: "Numéro d'inscription à l'ordre",
        email: 'Email',
        phone: 'Téléphone',
        identity_document: "Pièce d'identité"
    };

    const errorSourceLabels = {
        missing_required_fields: 'Champs obligatoires manquants',
        duplicate_email: 'Email déjà utilisé',
        profession: 'Profession',
        identity_document: "Pièce d'identité",
        invalid_characters: 'Caractères ou fichier invalides',
        database_schema: 'Configuration de la base de données',
        database_connection: 'Connexion base de données',
        database: 'Base de données'
    };

    function formatApiError(error) {
        const body = error?.body || {};
        const source = body.error_source ? (errorSourceLabels[body.error_source] || body.error_source) : '';
        const fields = Array.isArray(body.fields)
            ? body.fields.map((field) => registerFieldLabels[field] || field).join(', ')
            : '';
        const details = body.details ? `Détail: ${body.details}` : '';
        return [source, fields, details].filter(Boolean).join(' · ') || error.message || 'Une erreur est survenue.';
    }

    async function jsonFetch(url, options = {}) {
        const isFormData = options.body instanceof FormData;
        const response = await fetch(url, {
            ...options,
            headers: {
                'Accept': 'application/json',
                ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
                ...(options.headers || {})
            }
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            const msg = data.message || data.error || 'Une erreur est survenue.';
            const err = new Error(msg);
            err.status = response.status;
            err.body = data;
            throw err;
        }
        return data;
    }

    function Button({ children, variant = 'primary', type = 'button', disabled, onClick }) {
        return h('button', {
            type,
            disabled,
            onClick,
            className: cx('account-button', `account-button--${variant}`)
        }, children);
    }

    function Badge({ children, tone = 'neutral' }) {
        return h('span', { className: cx('account-badge', `account-badge--${tone}`) }, children);
    }

    function Icon({ name }) {
        const paths = {
            shield: 'M12 3 5 6v5c0 4.4 2.8 8.3 7 9.8 4.2-1.5 7-5.4 7-9.8V6l-7-3Zm0 2.2 5 2.1V11c0 3.1-1.8 6-5 7.4C8.8 17 7 14.1 7 11V7.3l5-2.1Z',
            user: 'M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm0 2c-4.4 0-8 2.2-8 5v1h16v-1c0-2.8-3.6-5-8-5Z',
            userPlus: 'M10 11a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm0 2c-3.9 0-7 2-7 4.5V19h9.2a6.9 6.9 0 0 1-.2-1.5 6.4 6.4 0 0 1 1-3.4A9 9 0 0 0 10 13Zm7-1v3h3v2h-3v3h-2v-3h-3v-2h3v-3h2Z',
            clipboard: 'M9 3h6l1 2h3v16H5V5h3l1-2Zm1.2 2-.4 1h4.4l-.4-1h-3.6ZM7 7v12h10V7H7Zm2 3h6v2H9v-2Zm0 4h5v2H9v-2Z',
            home: 'M12 4 3 11h2v9h5v-6h4v6h5v-9h2l-9-7Z',
            fileText: 'M6 3h9l3 3v15H6V3Zm8 2H8v14h8V7h-2V5Zm-4 6h4v2h-4v-2Zm0 4h4v2h-4v-2Z',
            logout: 'M5 4h8v2H7v12h6v2H5V4Zm10.6 4.4 1.4-1.4 5 5-5 5-1.4-1.4L18.2 13H10v-2h8.2l-2.6-2.6Z',
            check: 'M9.5 16.8 4.7 12l1.4-1.4 3.4 3.4 8.4-8.4L19.3 7 9.5 16.8Z',
        };
        return h('svg', { className: 'account-icon', viewBox: '0 0 24 24', 'aria-hidden': 'true', focusable: 'false' },
            h('path', { d: paths[name] || paths.shield })
        );
    }

    function Field({ label, name, type = 'text', value, onChange, placeholder, required, children, rows }) {
        const Control = rows ? 'textarea' : 'input';
        return h('label', { className: cx('account-field', rows && 'account-field--wide') }, [
            h('span', { key: 'label' }, [label, required ? h('span', { key: 'req', className: 'account-required' }, ' *') : null]),
            children || h(Control, {
                key: 'control',
                name,
                type: rows ? undefined : type,
                value: value || '',
                rows,
                required,
                placeholder,
                onChange: (event) => onChange(name, event.target.value)
            })
        ]);
    }

    function Notice({ message, tone = 'info' }) {
        if (!message) return null;
        return h('div', { className: cx('account-notice', `account-notice--${tone}`) }, message);
    }

    function loginDestinationFor(user, requestedNext) {
        const role = user?.role;
        const fallback = role === 'prescriber' ? '/ordonnances' : '/admin';
        if (!requestedNext || !requestedNext.startsWith('/') || requestedNext.startsWith('//')) {
            return fallback;
        }
        let path = requestedNext;
        try {
            path = new URL(requestedNext, window.location.origin).pathname.replace(/\/$/, '') || '/';
        } catch (error) {
            return fallback;
        }
        const allowedPrefixes = {
            prescriber: ['/ordonnances', '/prescripteur', '/etablissements', '/changer-mot-de-passe'],
            admin: ['/admin', '/changer-mot-de-passe']
        }[role] || [];
        if (path === '/' || path === '/changelog') return requestedNext;
        return allowedPrefixes.some((prefix) => path === prefix || path.startsWith(`${prefix}/`))
            ? requestedNext
            : fallback;
    }

    function AuthShell({ children }) {
        return h('div', { className: 'account-auth-shell' }, [
            h('section', { key: 'form', className: 'account-auth-content' }, children)
        ]);
    }

    function AccountSidebar({ user, active }) {
        const role = user?.role || 'guest';
        const items = [
            ['/', 'home', 'Interactions', true],
            ['/ordonnances', 'fileText', 'Ordonnances', role === 'prescriber'],
            ['/prescripteur', 'user', 'Prescripteur', role === 'prescriber'],
            ['/etablissements', 'home', 'Établissements', role === 'prescriber'],
            ['/admin', 'clipboard', 'Demandes', role === 'admin'],
        ].filter((item) => item[3]);

        return h('aside', { className: 'account-sidebar' }, [
            h('div', { key: 'head', className: 'account-sidebar__head' }, [
                h('span', { className: 'account-auth-mark' }, 'IAM'),
                h('div', null, [
                    h('strong', null, user?.first_name || user?.email || 'Compte'),
                    h('small', null, role === 'admin' ? 'Admin' : 'Prescripteur')
                ])
            ]),
            h('nav', { key: 'nav', className: 'account-sidebar__nav', 'aria-label': 'Navigation compte' }, items.map(([href, icon, label]) => (
                h('a', { key: href, href, className: cx('account-sidebar__link', active === href && 'is-active') }, [
                    h(Icon, { name: icon }),
                    h('span', null, label)
                ])
            ))),
            h('a', { key: 'logout', className: 'account-sidebar__logout', href: '/deconnexion' }, [
                h(Icon, { name: 'logout' }),
                h('span', null, 'Déconnexion')
            ])
        ]);
    }

    function WorkspaceShell({ title, eyebrow, description, children, user, active }) {
        return h('div', { className: 'account-dashboard container' }, [
            h(AccountSidebar, { key: 'sidebar', user, active }),
            h('section', { key: 'main', className: 'account-dashboard__main' }, [
                h('header', { key: 'header', className: 'account-header account-header--dashboard' }, [
                    h('span', { key: 'eyebrow', className: 'workspace-kicker' }, eyebrow),
                    h('h1', { key: 'title', className: 'workspace-title' }, title),
                    description ? h('p', { key: 'description', className: 'account-description' }, description) : null
                ]),
                children
            ])
        ]);
    }

    function Login({ next }) {
        const [form, setForm] = React.useState({ email: '', password: '' });
        const [message, setMessage] = React.useState('');
        const [busy, setBusy] = React.useState(false);

        function update(name, value) {
            setForm((current) => ({ ...current, [name]: value }));
        }

        async function submit(event) {
            event.preventDefault();
            setBusy(true);
            setMessage('');
            // Capture the real form element before any await — React pools synthetic events
            const formEl = event.currentTarget;
            const formData = new FormData(formEl);
            const payload = {
                email: String(formData.get('email') || form.email || '').trim(),
                password: String(formData.get('password') || form.password || '')
            };
            try {
                const data = await jsonFetch(api.login, { method: 'POST', body: JSON.stringify(payload) });
                const user = data.user || {};
                window.location.assign(user.must_change_password ? '/changer-mot-de-passe' : loginDestinationFor(user, next));
            } catch (error) {
                setMessage(error.message);
            } finally {
                setBusy(false);
            }
        }

        return h(AuthShell, {
            eyebrow: 'Compte IAM',
            title: 'Connexion',
            description: 'Accès réservé aux comptes validés.',
            active: 'login'
        }, h('form', { className: 'account-panel account-form', onSubmit: submit }, [
            h('div', { key: 'head', className: 'account-form-head' }, [
                h('h2', null, 'Se connecter'),
                h('p', null, 'Utilisez le compte validé par l’administrateur global.')
            ]),
            h(Notice, { key: 'notice', message, tone: 'danger' }),
            h(Field, { key: 'email', label: 'Email', name: 'email', type: 'email', value: form.email, onChange: update, required: true }),
            h(Field, { key: 'password', label: 'Mot de passe', name: 'password', type: 'password', value: form.password, onChange: update, required: true }),
            h('div', { key: 'actions', className: 'account-actions' }, [
                h('a', { key: 'register', className: 'account-link-button', href: '/inscription' }, 'Demander un compte'),
                h(Button, { key: 'submit', type: 'submit', disabled: busy }, busy ? 'Connexion...' : 'Se connecter')
            ])
        ]));
    }

    function Register() {
        const professionOptions = ['Médecin', 'Pharmacien', 'Chirurgien-dentiste', 'Sage-femme', 'Infirmier', 'Autre professionnel autorisé'];
        const [form, setForm] = React.useState({
            first_name: '',
            last_name: '',
            birthdate: '',
            profession: professionOptions[0],
            order_number: '',
            email: '',
            phone: ''
        });
        const [message, setMessage] = React.useState('');
        const [tone, setTone] = React.useState('info');
        const [busy, setBusy] = React.useState(false);
        const [isValid, setIsValid] = React.useState(false);
        const formRef = React.useRef(null);

        function updateValidity() {
            const formElement = formRef.current;
            setIsValid(Boolean(formElement && formElement.checkValidity()));
        }

        function update(name, value) {
            setForm((current) => ({ ...current, [name]: value }));
            window.setTimeout(updateValidity, 0);
        }

        async function submit(event) {
            event.preventDefault();
            const formEl = event.currentTarget;
            if (!formEl.checkValidity()) {
                formEl.reportValidity();
                setTone('danger');
                setMessage('Formulaire incomplet. Renseignez tous les champs obligatoires marqués par une étoile.');
                updateValidity();
                return;
            }
            setBusy(true);
            setMessage('');
            const formData = new FormData(formEl);
            try {
                const data = await jsonFetch(api.register, { method: 'POST', body: formData });
                setTone('success');
                setMessage(data.message);
                // Use captured DOM node to reset; synthetic event may be null after await
                try { formEl.reset(); } catch (e) {}
                setForm({
                    first_name: '',
                    last_name: '',
                    birthdate: '',
                    profession: professionOptions[0],
                    order_number: '',
                    email: '',
                    phone: ''
                });
                setIsValid(false);
                window.setTimeout(() => {
                    window.location.assign('/connexion');
                }, 1200);
            } catch (error) {
                setTone('danger');
                setMessage(`${error.message || 'Une erreur est survenue.'}${error?.body ? ` — ${formatApiError(error)}` : ''}`);
            } finally {
                setBusy(false);
            }
        }

        return h(AuthShell, {
            eyebrow: 'Demande de compte',
            title: 'Demande prescripteur',
            description: 'Votre demande est vérifiée par l’administrateur du site.',
            active: 'register'
        }, h('form', { ref: formRef, className: 'account-panel account-form account-form--wide', onSubmit: submit, encType: 'multipart/form-data' }, [
            h('div', { key: 'head', className: 'account-form-head' }, [
                h('h2', null, 'Demander un accès'),
                h('p', null, 'Renseignez les informations dans l’ordre de votre pièce d’identité.')
            ]),
            h(Notice, { key: 'notice', message, tone }),
            h(Field, { key: 'last', label: 'Noms', name: 'last_name', value: form.last_name, onChange: update, required: true, placeholder: 'Ex. ADJOVI' }),
            h(Field, { key: 'first', label: 'Prénoms', name: 'first_name', value: form.first_name, onChange: update, required: true, placeholder: 'Ex. Jean Marc' }),
            h(Field, { key: 'birthdate', label: 'Date de naissance', name: 'birthdate', type: 'date', value: form.birthdate, onChange: update, required: true }),
            h(Field, { key: 'profession', label: 'Profession', name: 'profession', value: form.profession, onChange: update, required: true }, h('select', {
                name: 'profession',
                value: form.profession,
                required: true,
                onChange: (event) => update('profession', event.target.value)
            }, professionOptions.map((option) => h('option', { key: option, value: option }, option)))),
            h(Field, { key: 'order', label: "Numéro d'inscription à l'ordre", name: 'order_number', value: form.order_number, onChange: update, required: true }),
            h(Field, { key: 'email', label: 'Email', name: 'email', type: 'email', value: form.email, onChange: update, required: true }),
            h(Field, { key: 'phone', label: 'Téléphone', name: 'phone', type: 'tel', value: form.phone, onChange: update, required: true }),
            h(Field, { key: 'document', label: "Pièce d'identité", name: 'identity_document', required: true }, h('input', {
                name: 'identity_document',
                type: 'file',
                accept: 'application/pdf,image/jpeg,image/png',
                required: true,
                onChange: updateValidity
            })),
            h('p', { key: 'privacy', className: 'account-help account-form-toolbar' }, "La pièce est utilisée uniquement pour la vérification du profil. Elle est supprimée après acceptation ou refus et n’est pas conservée."),
            h('div', { key: 'actions', className: 'account-actions' }, [
                h('a', { key: 'login', className: 'account-link-button', href: '/connexion' }, 'J’ai déjà un compte'),
                h(Button, { key: 'submit', type: 'submit', disabled: busy || !isValid }, busy ? 'Envoi...' : 'Envoyer la demande')
            ]),
            !isValid ? h('p', { key: 'required-help', className: 'account-help account-form-toolbar' }, 'Tous les champs marqués par une étoile rouge sont obligatoires.') : null
        ]));
    }

    function AdminRequests() {
        const [session, setSession] = React.useState(null);
        const [requests, setRequests] = React.useState([]);
        const [establishments, setEstablishments] = React.useState([]);
        const [message, setMessage] = React.useState('');
        const [tone, setTone] = React.useState('info');
        const [manualDelivery, setManualDelivery] = React.useState(null);

        async function load() {
            const sessionData = await jsonFetch(api.session);
            setSession(sessionData.user);
            const requestData = await jsonFetch(api.requests);
            setRequests(requestData.results || []);
            const establishmentData = await jsonFetch(api.adminEstablishments);
            setEstablishments(establishmentData.results || []);
        }

        React.useEffect(() => {
            load().catch((error) => {
                setTone('danger');
                setMessage(error.message);
            });
        }, []);

        async function review(item, action) {
            try {
                setManualDelivery(null);
                const data = await jsonFetch(`/api/v1/accounts/${item.id}/review`, {
                    method: 'POST',
                    body: JSON.stringify({ action })
                });
                setTone('success');
                setMessage(data.message);
                if (data.manual_delivery) {
                    setManualDelivery(data.manual_delivery);
                }
                await load();
            } catch (error) {
                setTone('danger');
                setMessage(error.message);
            }
        }

        async function copyManualMessage() {
            if (!manualDelivery?.text) return;
            try {
                await navigator.clipboard.writeText(manualDelivery.text);
                setTone('success');
                setMessage('Message copié. Il peut être transmis au prescripteur par le canal choisi.');
            } catch (error) {
                setTone('danger');
                setMessage('Copie automatique impossible. Sélectionnez le texte et copiez-le manuellement.');
            }
        }

        return h(WorkspaceShell, {
            eyebrow: 'Modération',
            title: 'Demandes prescripteurs',
            description: 'Validation globale des comptes prescripteurs et consultation des établissements.',
            user: session,
            active: '/admin'
        }, [
            h('section', { key: 'requests', className: 'account-panel' }, [
                h('div', { key: 'toolbar', className: 'account-panel-toolbar' }, [
                    h('div', null, [
                        h('strong', null, 'Files de demandes'),
                        h('p', null, requests.length ? `${requests.length} demande(s) visible(s)` : 'Aucune demande active')
                    ]),
                    h(Badge, { tone: 'warning' }, 'Admin')
                ]),
                h(Notice, { key: 'notice', message, tone }),
                manualDelivery ? h('div', { key: 'manual-delivery', className: 'account-manual-delivery' }, [
                    h('div', { key: 'head', className: 'account-panel-toolbar' }, [
                        h('div', null, [
                            h('strong', null, 'Transmission manuelle'),
                            h('p', null, `SMTP indisponible. Envoyer ce texte à ${manualDelivery.email}.`)
                        ]),
                        h(Button, { variant: 'outline', onClick: copyManualMessage }, [
                            h(Icon, { key: 'icon', name: 'clipboard' }),
                            'Copier'
                        ])
                    ]),
                    h('textarea', {
                        key: 'text',
                        className: 'account-manual-delivery__text',
                        readOnly: true,
                        value: manualDelivery.text,
                        rows: 9,
                        onFocus: (event) => event.target.select()
                    }),
                    h('p', { key: 'help' }, `Mot de passe temporaire valable ${manualDelivery.expires_in_hours || 24}h. Ce message n’est affiché qu’immédiatement après acceptation.`)
                ]) : null,
                requests.length
                    ? h('div', { key: 'list', className: 'account-request-list' }, requests.map((item) => (
                        h('article', { key: item.id, className: 'account-request-row' }, [
                            h('div', { key: 'identity' }, [
                                h('strong', null, [item.last_name, item.first_name].filter(Boolean).join(' ') || item.email),
                                h('p', null, [item.email, item.phone].filter(Boolean).join(' · ')),
                                h('p', null, [item.birthdate, item.profession, item.order_number].filter(Boolean).join(' · ')),
                                h('div', { className: 'account-row-badges' }, [
                                    h(Badge, { key: 'role', tone: 'info' }, 'Prescripteur'),
                                    h(Badge, { key: 'status', tone: item.status === 'approved' ? 'success' : item.status === 'rejected' ? 'danger' : 'neutral' }, item.status),
                                    item.has_identity_document ? h('a', {
                                        key: 'doc',
                                        className: 'account-link-button account-link-button--small',
                                        href: `/api/v1/accounts/${item.id}/identity-document`
                                    }, 'Pièce') : null
                                ])
                            ]),
                            h('div', { key: 'actions', className: 'account-row-actions' }, [
                                h(Button, { key: 'approve', variant: 'primary', disabled: item.status !== 'pending', onClick: () => review(item, 'approve') }, 'Accepter'),
                                h(Button, { key: 'reject', variant: 'outline', disabled: item.status !== 'pending', onClick: () => review(item, 'reject') }, 'Refuser')
                            ])
                        ])
                    )))
                    : h('p', { key: 'empty', className: 'account-empty' }, 'Aucune demande à traiter.')
            ]),
            h('section', { key: 'establishments', className: 'account-panel account-panel--stacked' }, [
                h('div', { key: 'toolbar', className: 'account-panel-toolbar' }, [
                    h('div', null, [
                        h('strong', null, 'Établissements des prescripteurs'),
                        h('p', null, establishments.length ? `${establishments.length} établissement(s)` : 'Aucun établissement enregistré')
                    ])
                ]),
                establishments.length
                    ? h('div', { className: 'account-request-list' }, establishments.map((item) => (
                        h('article', { key: item.id, className: 'account-request-row' }, [
                            h('div', null, [
                                h('strong', null, item.name),
                                h('p', null, [item.type, item.address].filter(Boolean).join(' · ')),
                                h('p', null, [item.prescriber?.last_name, item.prescriber?.first_name, item.prescriber?.email].filter(Boolean).join(' · '))
                            ]),
                            h(Badge, { tone: item.is_active ? 'success' : 'neutral' }, item.is_active ? 'Actif' : 'Inactif')
                        ])
                    )))
                    : h('p', { className: 'account-empty' }, 'Aucun établissement à afficher.')
            ])
        ]);
    }

    function Profile() {
        const fields = [
            ['title', 'Civilité'],
            ['first_name', 'Prénom'],
            ['last_name', 'Nom'],
            ['profession', 'Profession'],
            ['organization', 'Organisme'],
            ['country', 'Pays'],
            ['phone', 'Téléphone'],
            ['email', 'Email professionnel'],
            ['identifier_label', 'Libellé identifiant'],
            ['identifier_value', 'Valeur identifiant'],
            ['secondary_identifier_label', 'Libellé secondaire'],
            ['secondary_identifier_value', 'Valeur secondaire']
        ];
        const [form, setForm] = React.useState({});
        const [message, setMessage] = React.useState('');
        const [tone, setTone] = React.useState('info');
        const [busy, setBusy] = React.useState(false);

        React.useEffect(() => {
            jsonFetch(api.profile)
                .then((data) => setForm(data.profile || {}))
                .catch((error) => {
                    setTone('danger');
                    setMessage(error.message);
                });
        }, []);

        function update(name, value) {
            setForm((current) => ({ ...current, [name]: value }));
        }

        async function submit(event) {
            event.preventDefault();
            setBusy(true);
            try {
                const data = await jsonFetch(api.profile, { method: 'POST', body: JSON.stringify(form) });
                setForm(data.profile || form);
                setTone('success');
                setMessage('Profil prescripteur enregistré.');
            } catch (error) {
                setTone('danger');
                setMessage(error.message);
            } finally {
                setBusy(false);
            }
        }

        return h(WorkspaceShell, {
            eyebrow: 'Prescripteur',
            title: 'Profil professionnel',
            description: 'Ces informations préremplissent automatiquement les ordonnances.',
            user: { role: 'prescriber', first_name: form.first_name, email: form.email },
            active: '/prescripteur'
        }, h('form', { className: 'account-panel account-form account-form--wide', onSubmit: submit }, [
            h('div', { key: 'toolbar', className: 'account-panel-toolbar account-form-toolbar' }, [
                h('div', null, [
                    h('strong', null, 'Identité et coordonnées'),
                    h('p', null, 'Un compte prescripteur correspond à ce profil.')
                ]),
                h(Badge, { tone: 'info' }, 'Préremplissage ordonnance')
            ]),
            h(Notice, { key: 'notice', message, tone }),
            ...fields.map(([name, label]) => h(Field, { key: name, label, name, value: form[name], onChange: update })),
            h(Field, { key: 'address', label: 'Adresse', name: 'address', value: form.address, onChange: update, rows: 3 }),
            h(Field, { key: 'extra', label: 'Détails complémentaires', name: 'extra_details', value: form.extra_details, onChange: update, rows: 3 }),
            h('div', { key: 'actions', className: 'account-actions account-actions--end' }, [
                h('a', { key: 'rx', className: 'account-link-button', href: '/ordonnances' }, 'Retour ordonnance'),
                h(Button, { key: 'submit', type: 'submit', disabled: busy }, busy ? 'Enregistrement...' : 'Enregistrer')
            ])
        ]));
    }

    function ChangePassword() {
        const [form, setForm] = React.useState({ current_password: '', new_password: '', confirm_password: '' });
        const [message, setMessage] = React.useState('');
        const [tone, setTone] = React.useState('info');
        const [busy, setBusy] = React.useState(false);

        function update(name, value) {
            setForm((current) => ({ ...current, [name]: value }));
        }

        async function submit(event) {
            event.preventDefault();
            setBusy(true);
            setMessage('');
            if (form.new_password !== form.confirm_password) {
                setTone('danger');
                setMessage('Les deux mots de passe ne correspondent pas.');
                setBusy(false);
                return;
            }
            try {
                const data = await jsonFetch(api.changePassword, { method: 'POST', body: JSON.stringify(form) });
                setTone('success');
                setMessage(data.message);
                window.setTimeout(() => window.location.assign('/ordonnances'), 700);
            } catch (error) {
                setTone('danger');
                setMessage(error.message);
            } finally {
                setBusy(false);
            }
        }

        return h(AuthShell, null, h('form', { className: 'account-panel account-form', onSubmit: submit }, [
            h('div', { key: 'head', className: 'account-form-head' }, [
                h('h2', null, 'Changer le mot de passe'),
                h('p', null, 'Votre mot de passe temporaire doit être remplacé avant de continuer.')
            ]),
            h(Notice, { key: 'notice', message, tone }),
            h(Field, { key: 'current', label: 'Mot de passe temporaire', name: 'current_password', type: 'password', value: form.current_password, onChange: update, required: true }),
            h(Field, { key: 'new', label: 'Nouveau mot de passe', name: 'new_password', type: 'password', value: form.new_password, onChange: update, required: true }),
            h(Field, { key: 'confirm', label: 'Confirmer', name: 'confirm_password', type: 'password', value: form.confirm_password, onChange: update, required: true }),
            h('div', { key: 'actions', className: 'account-actions account-actions--end' }, [
                h(Button, { key: 'submit', type: 'submit', disabled: busy }, busy ? 'Enregistrement...' : 'Enregistrer')
            ])
        ]));
    }

    function Establishments() {
        const empty = {
            id: '',
            name: '',
            type: '',
            address: '',
            phone: '',
            email: '',
            identifier_label: '',
            identifier_value: '',
            secondary_identifier_label: '',
            secondary_identifier_value: '',
            free_text: '',
            is_active: true
        };
        const [session, setSession] = React.useState(null);
        const [items, setItems] = React.useState([]);
        const [form, setForm] = React.useState(empty);
        const [message, setMessage] = React.useState('');
        const [tone, setTone] = React.useState('info');
        const [busy, setBusy] = React.useState(false);

        async function load() {
            const sessionData = await jsonFetch(api.session);
            setSession(sessionData.user);
            const data = await jsonFetch(api.establishments);
            setItems(data.results || []);
        }

        React.useEffect(() => {
            load().catch((error) => {
                setTone('danger');
                setMessage(error.message);
            });
        }, []);

        function update(name, value) {
            setForm((current) => ({ ...current, [name]: value }));
        }

        async function submit(event) {
            event.preventDefault();
            setBusy(true);
            setMessage('');
            const formData = new FormData(event.currentTarget);
            formData.set('is_active', form.is_active ? '1' : '0');
            try {
                const url = form.id ? `${api.establishments}/${form.id}` : api.establishments;
                const data = await jsonFetch(url, { method: form.id ? 'PUT' : 'POST', body: formData });
                setTone('success');
                setMessage(data.message);
                setForm(empty);
                // Capture the form element before await above, reset using it
                try { formEl.reset(); } catch (e) {}
                await load();
            } catch (error) {
                setTone('danger');
                setMessage(error.message);
            } finally {
                setBusy(false);
            }
        }

        async function deactivate(item) {
            await jsonFetch(`${api.establishments}/${item.id}`, { method: 'DELETE' });
            await load();
        }

        const fields = [
            ['name', 'Nom'],
            ['type', 'Type'],
            ['phone', 'Téléphone'],
            ['email', 'Email'],
            ['identifier_label', 'Libellé identifiant'],
            ['identifier_value', 'Valeur identifiant'],
            ['secondary_identifier_label', 'Libellé secondaire'],
            ['secondary_identifier_value', 'Valeur secondaire']
        ];

        return h(WorkspaceShell, {
            eyebrow: 'Prescripteur',
            title: 'Établissements',
            description: 'Créez les structures utilisées dans l’en-tête des ordonnances.',
            user: session,
            active: '/etablissements'
        }, [
            h('form', { key: 'form', className: 'account-panel account-form account-form--wide', onSubmit: submit }, [
                h('div', { key: 'toolbar', className: 'account-panel-toolbar account-form-toolbar' }, [
                    h('div', null, [
                        h('strong', null, form.id ? 'Modifier un établissement' : 'Nouvel établissement'),
                        h('p', null, 'Ces informations seront proposées dans la liste déroulante de l’ordonnance.')
                    ]),
                    form.id ? h(Button, { variant: 'outline', onClick: () => setForm(empty) }, 'Nouveau') : null
                ]),
                h(Notice, { key: 'notice', message, tone }),
                ...fields.map(([name, label]) => h(Field, { key: name, label, name, value: form[name], onChange: update, required: name === 'name' })),
                h(Field, { key: 'address', label: 'Adresse', name: 'address', value: form.address, onChange: update, rows: 3 }),
                h(Field, { key: 'free', label: 'Mentions libres', name: 'free_text', value: form.free_text, onChange: update, rows: 3 }),
                h(Field, { key: 'logo', label: 'Logo', name: 'logo' }, h('input', { name: 'logo', type: 'file', accept: 'image/jpeg,image/png' })),
                h('label', { key: 'active', className: 'account-check account-form-toolbar' }, [
                    h('input', { type: 'checkbox', checked: form.is_active, onChange: (event) => update('is_active', event.target.checked) }),
                    h('span', null, 'Établissement actif')
                ]),
                h('div', { key: 'actions', className: 'account-actions account-actions--end' }, [
                    h(Button, { key: 'submit', type: 'submit', disabled: busy }, busy ? 'Enregistrement...' : 'Enregistrer')
                ])
            ]),
            h('section', { key: 'list', className: 'account-panel account-panel--stacked' }, [
                h('div', { className: 'account-panel-toolbar' }, [
                    h('div', null, [
                        h('strong', null, 'Liste des établissements'),
                        h('p', null, items.length ? `${items.length} établissement(s)` : 'Aucun établissement enregistré')
                    ])
                ]),
                items.length ? h('div', { className: 'account-request-list' }, items.map((item) => (
                    h('article', { key: item.id, className: 'account-request-row' }, [
                        h('div', null, [
                            h('strong', null, item.name),
                            h('p', null, [item.type, item.address].filter(Boolean).join(' · ')),
                            h('div', { className: 'account-row-badges' }, [
                                h(Badge, { tone: item.is_active ? 'success' : 'neutral' }, item.is_active ? 'Actif' : 'Inactif'),
                                item.has_logo ? h(Badge, { tone: 'info' }, 'Logo') : null
                            ])
                        ]),
                        h('div', { className: 'account-row-actions' }, [
                            h(Button, { variant: 'outline', onClick: () => setForm({ ...empty, ...item }) }, 'Modifier'),
                            h(Button, { variant: 'outline', disabled: !item.is_active, onClick: () => deactivate(item) }, 'Désactiver')
                        ])
                    ])
                ))) : h('p', { className: 'account-empty' }, 'Aucun établissement à afficher.')
            ])
        ]);
    }

    function App({ page, next }) {
        if (page === 'register') return h(Register);
        if (page === 'admin') return h(AdminRequests);
        if (page === 'profile') return h(Profile);
        if (page === 'change-password') return h(ChangePassword);
        if (page === 'establishments') return h(Establishments);
        return h(Login, { next });
    }

    document.addEventListener('DOMContentLoaded', () => {
        const root = document.getElementById('account-app');
        if (!root) return;
        ReactDOM.createRoot(root).render(h(App, {
            page: root.dataset.page || 'login',
            next: root.dataset.next || ''
        }));
    });
})();
