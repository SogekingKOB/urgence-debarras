/* Urgences Débarras Brest : comportements communs.
   Repris de la maquette (en-tête, barre mobile, apparitions, galerie), plus le menu mobile
   et l'envoi du formulaire de visite. */
(function () {
  'use strict';
  var root = document.documentElement;
  root.classList.remove('no-js');

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return [].slice.call((r || document).querySelectorAll(s)); };

  /* Avis qui défilent : chaque avis n'est écrit qu'une fois dans la page.
     On ajoute ici la copie de chaque rangée (masquée aux lecteurs d'écran) qui permet la boucle. */
  $$('.mq-track').forEach(function (track) {
    [].slice.call(track.children).forEach(function (card) {
      var copy = card.cloneNode(true);
      copy.setAttribute('aria-hidden', 'true');
      track.appendChild(copy);
    });
  });

  /* En-tête opaque au défilement, barre d'appel mobile */
  var topbar = $('#bar-top'), bar = $('#bar'), tick = false;
  var prog = $('#prog'), shot = $('.hero .shot');
  var still = matchMedia('(prefers-reduced-motion:reduce)').matches;
  var wide = matchMedia('(min-width:900px) and (hover:hover)');
  var PARALLAX_RATE = 0.06, PARALLAX_MAX = 24;
  var bigbg = $('.big .bg');
  function onScroll() {
    /* Citation plein cadre : la photo glisse un peu plus lentement que la page */
    if (bigbg && !still && innerWidth > 799) {
      var r = bigbg.parentNode.getBoundingClientRect();
      if (r.bottom > 0 && r.top < innerHeight) bigbg.style.transform = 'translateY(' + ((r.top / innerHeight) * -8).toFixed(2) + '%)';
    }
    if (topbar) topbar.classList.toggle('solid', scrollY > 30);
    if (bar) bar.classList.toggle('on', scrollY > innerHeight * 0.6);
    /* Barre de progression de lecture */
    if (prog) {
      var max = root.scrollHeight - innerHeight;
      prog.style.transform = 'scaleX(' + (max > 0 ? Math.min(scrollY / max, 1) : 0) + ')';
    }
    /* Légère parallaxe de la photo d'en-tête, sur grand écran seulement */
    if (shot && !still && wide.matches && scrollY < innerHeight) {
      shot.style.translate = '0 ' + Math.min(scrollY * PARALLAX_RATE, PARALLAX_MAX) + 'px';
    }
    tick = false;
  }
  addEventListener('scroll', function () {
    if (!tick) { tick = true; requestAnimationFrame(onScroll); }
  }, { passive: true });
  onScroll();

  /* Menu mobile */
  var menuBtn = $('#menu-btn'), mnav = $('#mnav');
  function setMenu(open) {
    if (!menuBtn || !mnav) return;
    menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    menuBtn.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
    mnav.hidden = !open;
    topbar.classList.toggle('open', open);
    document.body.style.overflow = open ? 'hidden' : '';
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

  /* Apparitions : un bloc de titre par section, et la grille de photos.
     Opacité + translation seulement : c'est ce que le GPU fait le moins cher sur mobile. */
  var calm = matchMedia('(prefers-reduced-motion:reduce)').matches ||
    (navigator.connection && navigator.connection.saveData) ||
    !('IntersectionObserver' in window);
  if (calm) {
    root.classList.add('no-anim');
  } else {
    var narrow = matchMedia('(max-width:700px)').matches;
    /* Apparitions échelonnées : les éléments d'une même liste arrivent l'un après l'autre */
    var STAGGER = 0.07, STAGGER_CAP = 6;
    [['.rows', 'article'], ['.sgrid', 'a'], ['.steps', 'li'], ['.cols', 'div'], ['.ladder', 'article'], ['.facts ul', 'li'],
      ['.yn', 'div'], ['.yn ul', 'li'], ['.faq', 'details'], ['.book-side .meta', 'li'],
      ['.fgrid', 'div'], ['.tell ul', 'li'], ['.bento', 'div'], ['.checks', 'li']].forEach(function (g) {
      $$(g[0]).forEach(function (parent) {
        var i = 0;
        $$(g[1], parent).forEach(function (el) {
          if (el.parentNode !== parent) return;
          el.setAttribute('data-rv', '');
          el.style.transitionDelay = Math.min(i++, STAGGER_CAP) * STAGGER + 's';
        });
      });
    });
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        var el = e.target;
        el.classList.add('on');
        io.unobserve(el);
        setTimeout(function () { el.style.transitionDelay = ''; }, 1400);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
    $$('[data-rv]').forEach(function (el) { io.observe(el); });
    var gio = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        $$('figure', e.target).forEach(function (fig, i) {
          fig.style.transitionDelay = (narrow ? Math.min(i, 3) * 0.05 : Math.min(i, 11) * 0.045) + 's';
          fig.classList.add('on');
        });
        gio.unobserve(e.target);
      });
    }, { threshold: 0.08 });
    $$('.gal').forEach(function (el) { gio.observe(el); });
    sectionMotion();
  }

  /* Animations propres à chaque section (jamais lancées si le visiteur préfère moins de mouvement) */
  function sectionMotion() {
    var EASE = 'cubic-bezier(.2,.7,.1,1)', SHAPES = 'path,circle,rect,line,polyline,polygon,ellipse';
    function once(els, threshold, fn) {
      var o = new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          if (!e.isIntersecting) return;
          o.unobserve(e.target);
          fn(e.target);
        });
      }, { threshold: threshold });
      els.forEach(function (el) { o.observe(el); });
    }

    /* Titres : le masque est porté par un élément intérieur, sinon le titre masqué n'est jamais vu à l'écran */
    $$('h2[data-rv]').forEach(function (h) {
      var s = document.createElement('span');
      s.className = 'hm';
      while (h.firstChild) s.appendChild(h.firstChild);
      h.appendChild(s);
      h.classList.add('mask');
    });

    /* Icônes : le trait se dessine quand la carte ou la ligne apparaît */
    var icons = $$('.scard .ico, .yn li .ico, .cols > div > .ico, .fgrid .ico, .tell .ico, .bento > div > .ico, .checks .ico').filter(function (svg) {
      var shapes = $$(SHAPES, svg), lens = shapes.map(function (s) {
        try { return s.getTotalLength(); } catch (err) { return 0; }
      });
      if (!shapes.length || lens.some(function (l) { return !(l > 0); })) return false;
      shapes.forEach(function (s, i) { s.style.strokeDasharray = lens[i]; s.style.strokeDashoffset = lens[i]; });
      return true;
    });
    once(icons, 0.5, function (svg) {
      var host = svg.closest('[data-rv]'), wait = (host ? parseFloat(host.style.transitionDelay) || 0 : 0) + 0.15;
      var shapes = $$(SHAPES, svg);
      shapes.forEach(function (s, i) {
        s.style.transition = 'stroke-dashoffset .9s ' + EASE + ' ' + (wait + i * 0.1).toFixed(2) + 's';
        s.style.strokeDashoffset = '0';
      });
      setTimeout(function () { shapes.forEach(function (s) { s.removeAttribute('style'); }); }, (wait + 1.8) * 1000);
    });

    /* Avis : les cinq étoiles s'allument l'une après l'autre */
    $$('.rc .stars').forEach(function (p) {
      var stars = p.textContent.trim().split('');
      p.textContent = '';
      stars.forEach(function (c) {
        var s = document.createElement('span');
        s.textContent = c;
        p.appendChild(s);
      });
    });

    /* Citation plein cadre : les mots montent l'un après l'autre */
    $$('.big blockquote').forEach(function (q) {
      var words = q.textContent.split(' ');
      q.textContent = '';
      words.forEach(function (w, i) {
        var span = document.createElement('span');
        span.className = 'w';
        span.textContent = w;
        span.style.transitionDelay = (i * 0.07).toFixed(2) + 's';
        q.appendChild(span);
        if (i < words.length - 1) q.appendChild(document.createTextNode(' '));
      });
      q.classList.add('words');
    });

    /* Avant / après : le curseur fait une démonstration, sauf si le visiteur l'a déjà pris en main */
    var SWEEP = [50, 18, 82, 50], SWEEP_MS = 2800;
    once($$('.ba'), 0.6, function (ba) {
      var touched = false, t0 = 0;
      ['pointerdown', 'keydown', 'input'].forEach(function (ev) {
        ba.addEventListener(ev, function () { touched = true; }, { once: true });
      });
      function frame(now) {
        if (touched) return;
        if (!t0) t0 = now;
        var k = Math.min((now - t0) / SWEEP_MS, 1) * (SWEEP.length - 1);
        var i = Math.min(Math.floor(k), SWEEP.length - 2), f = k - i;
        var v = SWEEP[i] + (SWEEP[i + 1] - SWEEP[i]) * (0.5 - Math.cos(f * Math.PI) / 2);
        ba.style.setProperty('--p', v.toFixed(2) + '%');
        if (k < SWEEP.length - 1) requestAnimationFrame(frame);
      }
      setTimeout(function () { requestAnimationFrame(frame); }, 450);
    });

    /* Bandeau d'appel : le texte entre, puis le bouton d'appel sonne deux fois */
    once($$('#appel'), 0.35, function (el) { el.classList.add('in'); });
  }

  /* Onglets des situations (particuliers / professionnels), au clic et aux flèches du clavier */
  $$('.tabs').forEach(function (box) {
    var tabs = $$('[role=tab]', box);
    function select(tab, focus) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.tabIndex = on ? 0 : -1;
        $('#' + t.getAttribute('aria-controls')).hidden = !on;
      });
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
    select(tabs[0], false);
  });

  /* Bande de photos : flèches, barre de progression, glisser à la souris (le doigt défile déjà seul) */
  var moved = 0, DRAG_MIN = 6;
  $$('.gwrap').forEach(function (wrap) {
    var track = $('.track', wrap), bar = $('.gprog i', wrap);
    function paint() {
      var max = track.scrollWidth - track.clientWidth;
      bar.style.transform = 'scaleX(' + Math.max(0.1, max > 0 ? track.scrollLeft / max : 1) + ')';
    }
    track.addEventListener('scroll', function () { requestAnimationFrame(paint); }, { passive: true });
    paint();
    $$('.arrows button', wrap).forEach(function (b) {
      b.addEventListener('click', function () {
        track.scrollBy({ left: Number(b.getAttribute('data-dir')) * track.clientWidth * 0.8, behavior: still ? 'auto' : 'smooth' });
      });
    });
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
      addEventListener(ev, function () { down = false; track.classList.remove('drag'); });
    });
    track.addEventListener('dragstart', function (e) { e.preventDefault(); });
  });

  /* Avis qui défilent : bouton pause (le survol et le focus suspendent aussi le défilement) */
  $$('.mq-pause').forEach(function (btn) {
    var box = $('.marquee');
    if (!box) return;
    btn.addEventListener('click', function () {
      var paused = box.classList.toggle('paused');
      btn.setAttribute('aria-pressed', paused ? 'true' : 'false');
      btn.textContent = paused ? 'Reprendre le défilement' : 'Mettre en pause';
    });
  });

  /* Avant / après : le curseur découpe la photo « après » */
  $$('.ba').forEach(function (ba) {
    var range = $('input', ba);
    range.addEventListener('input', function () { ba.style.setProperty('--p', range.value + '%'); });
  });

  /* Galerie : agrandissement au clic */
  var zoom = $('#zoom');
  if (zoom && typeof zoom.showModal === 'function') {
    $$('.gal .zbtn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (moved > DRAG_MIN) { moved = 0; return; }
        var i = $('img', btn);
        $('img', zoom).src = i.dataset.full || i.currentSrc || i.src;
        $('img', zoom).alt = i.alt;
        zoom.showModal();
      });
    });
    zoom.addEventListener('click', function () { zoom.close(); });
  }

  /* Formulaire de demande de visite.
     Sans JavaScript, le formulaire part normalement vers /envoi, qui redirige vers /merci/.
     Avec JavaScript, l'envoi se fait sans quitter la page. */
  var form = $('#visiteForm');
  if (!form) return;
  var ko = $('#ko'), ok = $('#ok'), btn = $('button[type=submit]', form);
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
    btn.disabled = true;
    btn.textContent = 'Envoi en cours…';
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
      if (ok.scrollIntoView) ok.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }).catch(function () {
      ko.textContent = 'L’envoi n’a pas abouti. Appelez-nous au 06 65 30 14 90, nous organisons la visite avec vous.';
      ko.classList.add('show');
      ko.focus();
    }).then(function () {
      btn.disabled = false;
      btn.textContent = 'Demander ma visite gratuite';
    });
  });
})();
