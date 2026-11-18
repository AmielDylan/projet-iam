/**
 * Home page: the interaction check in the hero card. Suggestions come from /api/v1/autocomplete;
 * the form opens the result on /interactions?med1=…&med2=… (static/js/redaction/home.js).
 */
(() => {
  /* Hero slideshow: cross-fade every 6 s; stops on hover or keyboard focus, on the pause button,
     and never starts when the visitor asks for reduced motion. */
  const stage = document.querySelector('[data-slides]');
  const toggle = document.querySelector('.slides-toggle');
  if (stage && toggle) {
    const slides = [...stage.querySelectorAll('.slide')];
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let index = 0;
    let timer = null;
    let paused = reduced;
    const hero = stage.closest('.hero');
    const show = (i) => {
      slides[index].classList.remove('is-active'); slides[index].setAttribute('aria-hidden', 'true');
      index = i;
      slides[index].classList.add('is-active'); slides[index].removeAttribute('aria-hidden');
    };
    const stop = () => { clearInterval(timer); timer = null; };
    const start = () => { if (!paused && !timer) timer = setInterval(() => show((index + 1) % slides.length), 6000); };
    if (slides.length > 1) {
      toggle.hidden = false;
      const sync = () => {
        toggle.setAttribute('aria-pressed', String(paused));
        toggle.setAttribute('aria-label', paused ? 'Relancer le diaporama' : 'Mettre le diaporama en pause');
      };
      sync();
      toggle.addEventListener('click', () => { paused = !paused; sync(); if (paused) stop(); else start(); });
      hero.addEventListener('mouseenter', stop);
      hero.addEventListener('mouseleave', start);
      hero.addEventListener('focusin', stop);
      hero.addEventListener('focusout', (e) => { if (!hero.contains(e.relatedTarget)) start(); });
      start();
    }
  }

  const form = document.getElementById('verifier');
  if (!form) return;
  const error = form.querySelector('.checker-error');
  const TYPES = { classe: 'Classe', substance: 'Substance', specialite: 'Spécialité' };

  function combobox(input) {
    const list = document.createElement('ul');
    list.className = 'hsuggest';
    list.id = input.getAttribute('aria-controls');
    list.setAttribute('role', 'listbox');
    list.hidden = true;
    input.parentElement.appendChild(list);
    let items = [];
    let active = -1;
    let timer = null;
    let asked = '';

    const close = () => { list.hidden = true; input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant'); active = -1; };
    const highlight = (i) => {
      active = i;
      [...list.children].forEach((li, k) => li.setAttribute('aria-selected', String(k === i)));
      if (i >= 0) input.setAttribute('aria-activedescendant', `${list.id}-${i}`);
    };
    const pick = (i) => {
      if (!items[i]) return;
      input.value = items[i].resultat;
      close();
      const next = form.med2 === input ? form.querySelector('.btn-check') : form.med2;
      next.focus();
    };
    const show = (results) => {
      items = results.slice(0, 6);
      list.replaceChildren(...items.map((r, i) => {
        const li = document.createElement('li');
        li.id = `${list.id}-${i}`;
        li.setAttribute('role', 'option');
        li.textContent = r.resultat;
        const type = document.createElement('small');
        type.textContent = TYPES[r.type] || r.type;
        li.appendChild(type);
        li.addEventListener('mousedown', (e) => { e.preventDefault(); pick(i); });
        return li;
      }));
      list.hidden = items.length === 0;
      input.setAttribute('aria-expanded', String(items.length > 0));
      active = -1;
    };

    input.addEventListener('input', () => {
      error.hidden = true;
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 2) { close(); return; }
      timer = setTimeout(async () => {
        asked = q;
        try {
          const response = await fetch(`/api/v1/autocomplete?q=${encodeURIComponent(q)}`);
          const data = response.ok ? await response.json() : [];
          if (asked === input.value.trim()) show(Array.isArray(data) ? data : []);
        } catch (e) { close(); }
      }, 250);
    });
    input.addEventListener('keydown', (e) => {
      if (list.hidden) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); highlight(Math.min(active + 1, items.length - 1)); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); highlight(Math.max(active - 1, 0)); }
      else if (e.key === 'Enter' && active >= 0) { e.preventDefault(); pick(active); }
      else if (e.key === 'Escape') { close(); }
    });
    input.addEventListener('blur', () => setTimeout(close, 120));
  }

  combobox(form.med1);
  combobox(form.med2);

  form.addEventListener('submit', (e) => {
    const med1 = form.med1.value.trim();
    const med2 = form.med2.value.trim();
    if (!med1 || !med2) {
      e.preventDefault();
      error.hidden = false;
      (med1 ? form.med2 : form.med1).focus();
    }
  });
})();
