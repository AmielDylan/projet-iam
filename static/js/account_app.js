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

    function Shell({ title, eyebrow, description, children, aside }) {
        return h('div', { className: 'account-shell container' }, [
            h('section', { key: 'main', className: 'account-workspace' }, [
                h('header', { key: 'header', className: 'account-header' }, [
                    h('span', { key: 'eyebrow', className: 'workspace-kicker' }, eyebrow),
                    h('h1', { key: 'title', className: 'workspace-title' }, title),
                    description ? h('p', { key: 'description', className: 'account-description' }, description) : null
                ]),
                children
            ]),
            aside ? h('aside', { key: 'aside', className: 'account-aside' }, aside) : null
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
            try {
                const data = await jsonFetch(api.login, { method: 'POST', body: JSON.stringify(form) });
                const user = data.user || {};
                const destination = next || (user.role === 'prescriber' ? '/ordonnances' : '/admin');
                window.location.assign(destination);
            } catch (error) {
                setMessage(error.message);
            } finally {
                setBusy(false);
            }
        }

        return h(Shell, {
            eyebrow: 'Compte IAM',
            title: 'Connexion',
            description: 'Accès réservé aux comptes validés.',
            aside: h('div', { className: 'account-side-note' }, [
                h(Badge, { key: 'badge', tone: 'info' }, 'Validation requise'),
                h('p', { key: 'copy' }, 'Les interactions restent publiques. Les ordonnances nécessitent un compte prescripteur validé.')
            ])
        }, h('form', { className: 'account-panel account-form', onSubmit: submit }, [
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
            try {
                const data = await jsonFetch(api.register, { method: 'POST', body: JSON.stringify(form) });
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

        return h(Shell, {
            eyebrow: 'Demande de compte',
            title: 'Choisir le bon accès',
            description: 'La pharmacie est validée par l’admin. Les prescripteurs sont validés par la pharmacie modératrice.',
            aside: h('div', { className: 'account-side-note' }, [
                h(Badge, { key: 'admin', tone: 'warning' }, 'Pharmacie -> admin'),
                h(Badge, { key: 'pharmacy', tone: 'success' }, 'Prescripteur -> pharmacie'),
                h('p', { key: 'copy' }, 'Un compte prescripteur correspond à un prescripteur unique.')
            ])
        }, h('form', { className: 'account-panel account-form', onSubmit: submit }, [
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

        return h(Shell, {
            eyebrow: 'Modération',
            title: reviewerLabel,
            description
        }, h('section', { className: 'account-panel' }, [
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

        return h(Shell, {
            eyebrow: 'Prescripteur',
            title: 'Profil professionnel',
            description: 'Ces informations préremplissent automatiquement les ordonnances.'
        }, h('form', { className: 'account-panel account-form account-form--wide', onSubmit: submit }, [
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
