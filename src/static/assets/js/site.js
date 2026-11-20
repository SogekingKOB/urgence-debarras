/* Urgences Débarras Brest : comportements communs et animations (design « place nette »).
   Les animations passent par Framer Motion (motion.js, chargé avant ce fichier, global « Motion »).
   Si Framer Motion manque, si le visiteur préfère moins de mouvement ou économise ses données,
   rien n'est animé et tout reste visible : la classe « anim » n'est alors pas posée sur <html>. */
(function () {
  'use strict';
  var root = document.documentElement;
  root.classList.remove('no-js');

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return [].slice.call((r || document).querySelectorAll(s)); };
  var M = window.Motion;
  var still = matchMedia('(prefers-reduced-motion:reduce)').matches ||
    !!(navigator.connection && navigator.connection.saveData);
  var anim = !!(M && M.animate && !still && 'IntersectionObserver' in window);
  root.classList.add(anim ? 'anim' : 'no-anim');
  var EASE = [0.2, 0.7, 0.1, 1];
  var SPRING = { type: 'spring', stiffness: 380, damping: 22 };

  /* Une seule observation par élément, déclenchée une fois */
  function once(els, amount, fn) {
    if (!els.length) return;
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        io.unobserve(e.target);
        fn(e.target);
      });
    }, { threshold: amount });
    els.forEach(function (el) { io.observe(el); });
  }

  /* ---------- Copies qui bouclent : avis et bandeau (masquées aux lecteurs d'écran) ---------- */
  function doubleUp(track) {
    [].slice.call(track.children).forEach(function (item) {
      var copy = item.cloneNode(true);
      copy.setAttribute('aria-hidden', 'true');
      track.appendChild(copy);
    });
  }
  if (anim) {
    $$('.mq-track').forEach(doubleUp);
    $$('.tk').forEach(doubleUp);
  }

  /* ---------- En-tête : barre de progression de lecture, pilule qui suit la souris ---------- */
  var prog = $('#prog'), tick = false;
  function onScroll() {
    if (prog) {
      var max = root.scrollHeight - innerHeight;
      prog.style.transform = 'scaleX(' + (max > 0 ? Math.min(scrollY / max, 1) : 0) + ')';
    }
    tick = false;
  }
  addEventListener('scroll', function () {
    if (!tick) { tick = true; requestAnimationFrame(onScroll); }
  }, { passive: true });
  onScroll();

  var nav = $('.nav'), pill = nav && $('.pill', nav);
  if (nav && pill && anim) {
    var shown = false;
    $$('a', nav).forEach(function (a) {
      function over() {
        var box = { x: a.offsetLeft, y: a.offsetTop, width: a.offsetWidth, height: a.offsetHeight };
        $$('a', nav).forEach(function (b) { b.classList.toggle('hov', b === a); });
        if (!shown) {
          M.animate(pill, { x: box.x, y: box.y, width: box.width, height: box.height }, { duration: 0 });
          M.animate(pill, { opacity: 1 }, { duration: 0.15 });
          shown = true;
        } else {
          M.animate(pill, box, { type: 'spring', stiffness: 420, damping: 32 });
        }
      }
      a.addEventListener('mouseenter', over);
      a.addEventListener('focus', over);
    });
    function out() {
      shown = false;
      $$('a', nav).forEach(function (b) { b.classList.remove('hov'); });
      M.animate(pill, { opacity: 0 }, { duration: 0.15 });
    }
    nav.addEventListener('mouseleave', out);
    nav.addEventListener('focusout', function (e) { if (!nav.contains(e.relatedTarget)) out(); });
  }

  /* ---------- Menu mobile ---------- */
  var topbar = $('#bar-top'), menuBtn = $('#menu-btn'), mnav = $('#mnav');
  function setMenu(open) {
    if (!menuBtn || !mnav) return;
    menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    menuBtn.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
    mnav.hidden = !open;
    if (topbar) mnav.style.top = topbar.getBoundingClientRect().bottom + 'px';
    document.body.style.overflow = open ? 'hidden' : '';
    if (open && anim) {
      M.animate($$('li', mnav).filter(function (li) { return li.parentNode.parentNode.parentNode === mnav; }),
        { opacity: [0, 1], x: [-16, 0] }, { duration: 0.35, delay: M.stagger(0.03), ease: EASE });
    }
  }
  if (menuBtn && mnav) {
    menuBtn.addEventListener('click', function () {
      setMenu(menuBtn.getAttribute('aria-expanded') !== 'true');
    });
    addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menuBtn.getAttribute('aria-expanded') === 'true') {
        setMenu(false);
        menuBtn.focus();
      }
    });
    $$('a', mnav).forEach(function (a) { a.addEventListener('click', function () { setMenu(false); }); });
  }

  /* ---------- Hero d'accueil : les objets tombent en tas, puis sont évacués ---------- */
  var heroBox = $('.hero.home');
  if (heroBox && anim) {
    var objs = $$('.obj', heroBox), mark = $('h1 mark', heroBox), hlb = mark && $('.hlb', mark);
    var stamp = $('.stamp', heroBox), rating = $('.rating', heroBox), photo = $('.ph', heroBox);
    var replay = $('.replay', heroBox), timer = 0, playing = [];
    /* Si la page s'affiche tard (connexion lente), on ne rejoue pas le tas : le titre est déjà lu */
    var fresh = performance.now() < 2500;
    function stop() { playing.forEach(function (a) { a.stop(); }); playing = []; clearTimeout(timer); }
    function clear() {
      objs.forEach(function (o, i) {
        var dir = i % 2 ? 1 : -1;
        playing.push(M.animate(o, {
          x: dir * (260 + (i * 47) % 300), y: -(380 + (i * 61) % 300), rotate: dir * (40 + (i * 17) % 80), opacity: 0
        }, { duration: 0.75, delay: (i % 11) * 0.045, ease: [0.5, 0, 0.75, 0] }));
      });
      if (hlb) {
        playing.push(M.animate(hlb, { scaleX: [0, 1] }, { duration: 0.5, delay: 0.7, ease: EASE }));
        timer = setTimeout(function () { mark.classList.remove('pre'); }, 750);
      }
    }
    function run() {
      stop();
      if (mark) mark.classList.add('pre');
      if (hlb) hlb.style.transform = 'scaleX(0)';
      objs.forEach(function (o, i) {
        var r = (i * 13) % 34 - 17;
        M.animate(o, { x: 0, opacity: 0, rotate: 0 }, { duration: 0 });
        playing.push(M.animate(o, { opacity: [0, 1], scale: [0.3, 1], y: [-120, 0], rotate: [0, r] },
          { type: 'spring', stiffness: 260, damping: 17, delay: i * 0.035 }));
      });
      timer = setTimeout(clear, 1900);
    }
    if (fresh) {
      if (photo) M.animate(photo, { opacity: [0, 1], y: [30, 0], rotate: [2, 0] }, { duration: 0.7, delay: 0.3, ease: EASE });
      if (rating) M.animate(rating, { opacity: [0, 1], x: [20, 0] }, { duration: 0.5, delay: 1, ease: EASE });
      if (stamp) {
        stamp.style.opacity = 0;
        M.animate(stamp, { scale: [2.4, 1], opacity: [0, 1], rotate: [-20, -6] },
          { delay: 2.5, type: 'spring', stiffness: 420, damping: 15 });
      }
      run();
    }
    if (replay) {
      replay.hidden = false;
      replay.addEventListener('click', run);
    }
  }

  /* ---------- Bandeaux qui défilent : engagements, avis ---------- */
  if (anim) {
    $$('.tk').forEach(function (tk) {
      M.animate(tk, { x: ['0%', '-50%'] }, { duration: tk.scrollWidth / 2 / 50, ease: 'linear', repeat: Infinity });
    });
    var rows = $$('.mq-track').map(function (track) {
      var rev = track.parentNode.classList.contains('rev');
      return M.animate(track, { x: rev ? ['-50%', '0%'] : ['0%', '-50%'] },
        { duration: track.scrollWidth / 2 / 30, ease: 'linear', repeat: Infinity });
    });
    var box = $('.marquee'), btn = $('.mq-pause'), user = false, hover = false;
    var sync = function () { rows.forEach(function (a) { if (user || hover) a.pause(); else a.play(); }); };
    if (box) {
      box.addEventListener('mouseenter', function () { hover = true; sync(); });
      box.addEventListener('mouseleave', function () { hover = false; sync(); });
      box.addEventListener('focusin', function () { hover = true; sync(); });
      box.addEventListener('focusout', function () { hover = false; sync(); });
    }
    if (btn) {
      btn.addEventListener('click', function () {
        user = !user;
        btn.setAttribute('aria-pressed', user ? 'true' : 'false');
        $('span', btn).textContent = user ? 'Relancer le défilement' : 'Mettre en pause';
        sync();
      });
    }
  }

  /* ---------- Bandes à faire défiler : situations, photos ---------- */
  var moved = 0, DRAG_MIN = 6;
  function strip(track, bar) {
    function paint() {
      if (!bar) return;
      var max = track.scrollWidth - track.clientWidth;
      bar.style.transform = 'scaleX(' + Math.max(0.1, max > 0 ? track.scrollLeft / max : 1) + ')';
    }
    track.addEventListener('scroll', function () { requestAnimationFrame(paint); }, { passive: true });
    paint();
    var down = false, sx = 0, sl = 0;
    track.addEventListener('pointerdown', function (e) {
      if (e.pointerType === 'touch' || e.button !== 0) return;
      down = true; moved = 0; sx = e.clientX; sl = track.scrollLeft;
    });
    addEventListener('pointermove', function (e) {
      if (!down) return;
      var d = e.clientX - sx;
      moved = Math.max(moved, Math.abs(d));
      if (moved > DRAG_MIN) { track.classList.add('drag'); track.scrollLeft = sl - d; }
    });
    ['pointerup', 'pointercancel'].forEach(function (ev) {
      addEventListener(ev, function () {
        if (!down) return;
        down = false;
        if (track.classList.contains('drag')) {
          track.classList.remove('drag');
          /* on se recale sur la carte la plus proche */
          var card = track.firstElementChild, step = card ? card.offsetWidth + 14 : 0;
          if (step) track.scrollTo({ left: Math.round(track.scrollLeft / step) * step, behavior: still ? 'auto' : 'smooth' });
        }
      });
    });
    track.addEventListener('dragstart', function (e) { e.preventDefault(); });
    track.addEventListener('click', function (e) {
      if (moved > DRAG_MIN) { e.preventDefault(); e.stopPropagation(); moved = 0; }
    }, true);
    return paint;
  }
  function arrows(wrap, current) {
    $$('.arrows button', wrap).forEach(function (b) {
      b.addEventListener('click', function () {
        var t = current();
        t.scrollBy({ left: Number(b.getAttribute('data-dir')) * Math.min(t.clientWidth * 0.8, 640), behavior: still ? 'auto' : 'smooth' });
      });
    });
  }
  $$('.gwrap').forEach(function (wrap) {
    var track = $('.track', wrap);
    strip(track, $('.gprog i', wrap));
    arrows(wrap, function () { return track; });
  });

  /* Onglets des situations (particuliers / professionnels), au clic et aux flèches du clavier */
  $$('.tabs').forEach(function (box) {
    var tabs = $$('[role=tab]', box), bar = $('.sbar .gprog i', box), paints = {};
    $$('.rsc', box).forEach(function (t) { paints[t.parentNode.id] = strip(t, bar); });
    function visible() { return $('.tpanel:not([hidden]) .rsc', box); }
    function select(tab, focus, first) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.tabIndex = on ? 0 : -1;
        $('#' + t.getAttribute('aria-controls')).hidden = !on;
      });
      var track = visible();
      if (track) {
        track.scrollLeft = 0;
        if (paints[track.parentNode.id]) paints[track.parentNode.id]();
        if (anim && !first) {
          M.animate($$('.scard', track), { opacity: [0, 1], y: [18, 0], scale: [0.97, 1] },
            { duration: 0.35, delay: M.stagger(0.04), ease: EASE });
        }
      }
      if (focus) tab.focus();
    }
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { select(t, false); });
      t.addEventListener('keydown', function (e) {
        var next = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : null;
        if (next === null) return;
        e.preventDefault();
        select(tabs[(next + tabs.length) % tabs.length], true);
      });
    });
    arrows(box, visible);
    if (tabs.length) select(tabs[0], false, true);
  });

  /* ---------- Apparitions au défilement ---------- */
  if (anim) {
    /* Les éléments d'une même liste arrivent l'un après l'autre, avec un léger ressort */
    var GROUPS = [['.sgrid', '.scard'], ['.steps', 'li'], ['.boxes', '.carton'], ['.cols', 'div'], ['.ladder', 'article'],
      ['.faq', 'details'], ['.gal', 'figure'], ['.fgrid', 'div'], ['.yn', 'div'], ['.tell ul', 'li'], ['.rows', 'article'],
      ['.avis', 'figure'], ['.book-side .meta', 'li'], ['.cbox', '.crow']];
    var springy = [];
    GROUPS.forEach(function (g) {
      $$(g[0]).forEach(function (parent) {
        var kids = [].slice.call(parent.children).filter(function (k) { return k.matches(g[1]); });
        if (!kids.length) return;
        kids.forEach(function (k) { k.style.opacity = 0; });
        springy.push({ el: parent, kids: kids });
      });
    });
    springy.forEach(function (s) { s.el.__kids = s.kids; });
    once(springy.map(function (s) { return s.el; }), 0.1, function (el) {
      var kids = el.__kids.slice(0, 8), rest = el.__kids.slice(8);
      M.animate(kids, { opacity: [0, 1], y: [14, 0], scale: [0.94, 1] },
        { delay: M.stagger(0.06), type: 'spring', stiffness: SPRING.stiffness, damping: SPRING.damping });
      rest.forEach(function (k) { k.style.opacity = 1; });
    });
    /* Titres et paragraphes marqués data-rv : montée douce */
    once($$('[data-rv]'), 0.15, function (el) {
      var prev = el.previousElementSibling, d = prev && prev.hasAttribute('data-rv') ? 0.08 : 0;
      M.animate(el, { opacity: [0, 1], y: [26, 0] }, { duration: 0.6, delay: d, ease: EASE });
    });
  }

  /* ---------- Bon d'enlèvement : les lignes se cochent l'une après l'autre ---------- */
  $$('.bon').forEach(function (bon) {
    if (!anim) return;
    var boxes = $$('.box', bon), stmp = $('.stmp', bon);
    /* Framer Motion gère le tracé des SVG par « pathLength » (0 = invisible, 1 = complet) */
    var paths = boxes.map(function (b) { return $('path', b); });
    M.animate(paths, { pathLength: 0 }, { duration: 0 });
    if (stmp) M.animate(stmp, { opacity: 0 }, { duration: 0 });
    once([bon], 0.35, function () {
      boxes.forEach(function (b, i) {
        setTimeout(function () {
          b.classList.add('on');
          M.animate(paths[i], { pathLength: 1 }, { duration: 0.25 });
          if (i === boxes.length - 1 && stmp) {
            M.animate(stmp, { scale: [2.2, 1], opacity: [0, 1], rotate: [-18, -7] },
              { delay: 0.2, type: 'spring', stiffness: 420, damping: 15 });
          }
        }, 320 * (i + 1));
      });
    });
  });

  /* ---------- Avant / après : le curseur découpe la photo « après » ---------- */
  $$('.ba').forEach(function (ba) {
    var range = $('input', ba), touched = false, demo = null;
    function set(v) { ba.style.setProperty('--p', v + '%'); }
    range.addEventListener('input', function () { set(range.value); });
    ['pointerdown', 'keydown', 'input'].forEach(function (ev) {
      ba.addEventListener(ev, function () { touched = true; if (demo) demo.stop(); }, { once: true });
    });
    if (!anim) return;
    /* Démonstration : le curseur va et vient une fois, sauf si le visiteur l'a déjà pris en main */
    once([ba], 0.5, function () {
      if (touched) return;
      demo = M.animate(50, [50, 85, 15, 50], {
        duration: 2.6, ease: 'easeInOut', delay: 0.3,
        onUpdate: function (v) { set(v.toFixed(2)); range.value = Math.round(v); }
      });
    });
  });

  /* ---------- Carte du Finistère : le contour se dessine, puis les villes apparaissent ---------- */
  $$('[data-map]').forEach(function (map) {
    if (!anim) return;
    var dep = $('.dep', map), coms = $$('.com', map), labels = $$('.lb', map);
    M.animate(dep, { pathLength: 0, fillOpacity: 0 }, { duration: 0 });
    M.animate(coms.concat(labels), { opacity: 0 }, { duration: 0 });
    once([map], 0.25, function () {
      M.animate(dep, { pathLength: 1 }, { duration: 1.4, ease: 'easeInOut' });
      M.animate(dep, { fillOpacity: 1 }, { duration: 0.6, delay: 0.8 });
      coms.forEach(function (c, i) {
        M.animate(c, { opacity: [0, 1], scale: [0.4, 1] }, { delay: 1 + i * 0.05, type: 'spring', stiffness: 300, damping: 20 });
      });
      M.animate(labels, { opacity: [0, 1] }, { duration: 0.4, delay: M.stagger(0.04, { startDelay: 1.6 }) });
    });
  });

  /* ---------- Coordonnées à copier ---------- */
  $$('.cp').forEach(function (b) {
    b.addEventListener('click', function () {
      var text = b.getAttribute('data-copy');
      if (!navigator.clipboard) return;
      navigator.clipboard.writeText(text).then(function () {
        b.textContent = 'Copié';
        if (anim) M.animate(b, { scale: [0.85, 1] }, { type: 'spring', stiffness: 500, damping: 15 });
        setTimeout(function () { b.textContent = 'Copier'; }, 1600);
      }, function () {});
    });
  });

  /* ---------- Galerie : agrandissement au clic ---------- */
  var zoom = $('#zoom');
  if (zoom && typeof zoom.showModal === 'function') {
    $$('.gal .zbtn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var i = $('img', btn);
        $('img', zoom).src = i.dataset.full || i.currentSrc || i.src;
        $('img', zoom).alt = i.alt;
        zoom.showModal();
        if (anim) M.animate($('img', zoom), { opacity: [0, 1], scale: [0.94, 1] }, { duration: 0.3, ease: EASE });
      });
    });
    zoom.addEventListener('click', function () { zoom.close(); });
  }

  /* ---------- Formulaire de demande de visite ----------
     Sans JavaScript, le formulaire part normalement vers /envoi, qui redirige vers /merci/.
     Avec JavaScript, l'envoi se fait sans quitter la page. */
  var form = $('#visiteForm');
  if (!form) return;
  var ko = $('#ko'), ok = $('#ok'), submit = $('button[type=submit]', form);
  var started = $('input[name=t]', form);
  if (started) started.value = String(Date.now());

  function valid(f) {
    return f.prenom.value.trim() && f.nom.value.trim() &&
      f.tel.value.replace(/\D/g, '').length >= 10 &&
      (!f.mail.value.trim() || /^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(f.mail.value.trim())) &&
      f.motif.value && f.adresse.value.trim() && f.consent.checked;
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    ok.classList.remove('show');
    if (!valid(form)) {
      ko.textContent = 'Il manque une information : prénom, nom, téléphone, situation, adresse, ou la case d’accord.';
      ko.classList.add('show');
      ko.focus();
      return;
    }
    ko.classList.remove('show');
    submit.disabled = true;
    submit.textContent = 'Envoi en cours…';
    fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: { 'Accept': 'application/json' }
    }).then(function (r) {
      return r.json().catch(function () { return { ok: false }; });
    }).then(function (res) {
      if (!res || !res.ok) throw new Error((res && res.error) || 'envoi');
      form.hidden = true;
      ok.classList.add('show');
      ok.focus();
      if (anim) M.animate(ok, { opacity: [0, 1], scale: [0.96, 1] }, SPRING);
      if (ok.scrollIntoView) ok.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }).catch(function () {
      ko.textContent = 'L’envoi n’a pas abouti. Appelez-nous au 06 65 30 14 90, nous organisons la visite avec vous.';
      ko.classList.add('show');
      ko.focus();
    }).then(function () {
      submit.disabled = false;
      submit.textContent = 'Demander ma visite gratuite';
    });
  });
})();
