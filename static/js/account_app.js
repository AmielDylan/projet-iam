(function () {
    const h = React.createElement;

    const api = {
        session: '/api/v1/auth/session',
        login: '/api/v1/auth/login',
        register: '/api/v1/auth/register',
        requests: '/api/v1/accounts/requests',
        profile: '/api/v1/prescriber/profile'
    };

    function cx(...parts) {
        return parts.filter(Boolean).join(' ');
    }

    async function jsonFetch(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                ...(options.headers || {})
            }
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            throw new Error(data.message || data.error || 'Une erreur est survenue.');
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
            h('span', { key: 'label' }, label),
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
            ['/admin', 'clipboard', 'Demandes', role === 'admin' || role === 'pharmacy'],
        ].filter((item) => item[3]);

        return h('aside', { className: 'account-sidebar' }, [
            h('div', { key: 'head', className: 'account-sidebar__head' }, [
                h('span', { className: 'account-auth-mark' }, 'IAM'),
                h('div', null, [
                    h('strong', null, user?.first_name || user?.email || 'Compte'),
                    h('small', null, role === 'pharmacy' ? 'Pharmacie' : role === 'admin' ? 'Admin' : 'Prescripteur')
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
            const formData = new FormData(event.currentTarget);
            const payload = {
                email: String(formData.get('email') || form.email || '').trim(),
                password: String(formData.get('password') || form.password || '')
            };
            try {
                const data = await jsonFetch(api.login, { method: 'POST', body: JSON.stringify(payload) });
                const user = data.user || {};
                const destination = next || (user.role === 'prescriber' ? '/ordonnances' : '/admin');
                window.location.assign(destination);
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
                h('p', null, 'Utilisez le compte validé par votre administrateur ou votre pharmacie.')
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
        const [form, setForm] = React.useState({ first_name: '', last_name: '', email: '', password: '', role: 'prescriber' });
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
            const formData = new FormData(event.currentTarget);
            const payload = {
                first_name: String(formData.get('first_name') || form.first_name || '').trim(),
                last_name: String(formData.get('last_name') || form.last_name || '').trim(),
                email: String(formData.get('email') || form.email || '').trim(),
                password: String(formData.get('password') || form.password || ''),
                role: form.role
            };
            try {
                const data = await jsonFetch(api.register, { method: 'POST', body: JSON.stringify(payload) });
                setTone('success');
                setMessage(data.message);
                setForm({ first_name: '', last_name: '', email: '', password: '', role: form.role });
            } catch (error) {
                setTone('danger');
                setMessage(error.message);
            } finally {
                setBusy(false);
            }
        }

        return h(AuthShell, {
            eyebrow: 'Demande de compte',
            title: 'Choisir le bon accès',
            description: 'La pharmacie est validée par l’admin. Les prescripteurs sont validés par la pharmacie modératrice.',
            active: 'register'
        }, h('form', { className: 'account-panel account-form', onSubmit: submit }, [
            h('div', { key: 'head', className: 'account-form-head' }, [
                h('h2', null, 'Demander un accès'),
                h('p', null, 'Sélectionnez le type de compte avant l’envoi.')
            ]),
            h(Notice, { key: 'notice', message, tone }),
            h('div', { key: 'role', className: 'account-toggle', role: 'radiogroup', 'aria-label': 'Type de compte' }, [
                h('button', {
                    key: 'prescriber',
                    type: 'button',
                    className: cx('account-toggle__item', form.role === 'prescriber' && 'is-active'),
                    onClick: () => update('role', 'prescriber')
                }, 'Prescripteur'),
                h('button', {
                    key: 'pharmacy',
                    type: 'button',
                    className: cx('account-toggle__item', form.role === 'pharmacy' && 'is-active'),
                    onClick: () => update('role', 'pharmacy')
                }, 'Pharmacie')
            ]),
            h(Field, { key: 'first', label: 'Prénom', name: 'first_name', value: form.first_name, onChange: update, required: true }),
            h(Field, { key: 'last', label: 'Nom', name: 'last_name', value: form.last_name, onChange: update, required: true }),
            h(Field, { key: 'email', label: 'Email', name: 'email', type: 'email', value: form.email, onChange: update, required: true }),
            h(Field, { key: 'password', label: 'Mot de passe', name: 'password', type: 'password', value: form.password, onChange: update, required: true }),
            h('div', { key: 'actions', className: 'account-actions' }, [
                h('a', { key: 'login', className: 'account-link-button', href: '/connexion' }, 'J’ai déjà un compte'),
                h(Button, { key: 'submit', type: 'submit', disabled: busy }, busy ? 'Envoi...' : 'Envoyer la demande')
            ])
        ]));
    }

    function AdminRequests() {
        const [session, setSession] = React.useState(null);
        const [requests, setRequests] = React.useState([]);
        const [message, setMessage] = React.useState('');
        const [tone, setTone] = React.useState('info');

        async function load() {
            const sessionData = await jsonFetch(api.session);
            setSession(sessionData.user);
            const requestData = await jsonFetch(api.requests);
            setRequests(requestData.results || []);
        }

        React.useEffect(() => {
            load().catch((error) => {
                setTone('danger');
                setMessage(error.message);
            });
        }, []);

        async function review(item, action) {
            try {
                const data = await jsonFetch(`/api/v1/accounts/${item.id}/review`, {
                    method: 'POST',
                    body: JSON.stringify({ action })
                });
                setTone('success');
                setMessage(data.message);
                await load();
            } catch (error) {
                setTone('danger');
                setMessage(error.message);
            }
        }

        const reviewerLabel = session?.role === 'admin' ? 'Demandes pharmacie' : 'Demandes prescripteurs';
        const description = session?.role === 'admin'
            ? 'L’admin valide les comptes pharmacie modératrice.'
            : 'La pharmacie modératrice valide les comptes prescripteurs.';

        return h(WorkspaceShell, {
            eyebrow: 'Modération',
            title: reviewerLabel,
            description,
            user: session,
            active: '/admin'
        }, h('section', { className: 'account-panel' }, [
            h('div', { key: 'toolbar', className: 'account-panel-toolbar' }, [
                h('div', null, [
                    h('strong', null, 'Files de demandes'),
                    h('p', null, requests.length ? `${requests.length} demande(s) visible(s)` : 'Aucune demande active')
                ]),
                h(Badge, { tone: session?.role === 'admin' ? 'warning' : 'success' }, session?.role === 'admin' ? 'Admin' : 'Pharmacie')
            ]),
            h(Notice, { key: 'notice', message, tone }),
            requests.length
                ? h('div', { key: 'list', className: 'account-request-list' }, requests.map((item) => (
                    h('article', { key: item.id, className: 'account-request-row' }, [
                        h('div', { key: 'identity' }, [
                            h('strong', null, [item.first_name, item.last_name].filter(Boolean).join(' ') || item.email),
                            h('p', null, item.email),
                            h('div', { className: 'account-row-badges' }, [
                                h(Badge, { key: 'role', tone: item.role === 'pharmacy' ? 'warning' : 'info' }, item.role === 'pharmacy' ? 'Pharmacie' : 'Prescripteur'),
                                h(Badge, { key: 'status', tone: item.status === 'approved' ? 'success' : item.status === 'rejected' ? 'danger' : 'neutral' }, item.status)
                            ])
                        ]),
                        h('div', { key: 'actions', className: 'account-row-actions' }, [
                            h(Button, { key: 'approve', variant: 'primary', disabled: item.status !== 'pending', onClick: () => review(item, 'approve') }, 'Accepter'),
                            h(Button, { key: 'reject', variant: 'outline', disabled: item.status !== 'pending', onClick: () => review(item, 'reject') }, 'Refuser')
                        ])
                    ])
                )))
                : h('p', { key: 'empty', className: 'account-empty' }, 'Aucune demande à traiter.')
        ]));
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

    function App({ page, next }) {
        if (page === 'register') return h(Register);
        if (page === 'admin') return h(AdminRequests);
        if (page === 'profile') return h(Profile);
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
