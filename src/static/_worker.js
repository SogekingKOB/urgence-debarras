/**
 * Urgences Débarras Brest : Cloudflare Pages, mode « _worker.js ».
 *
 * - POST /envoi : reçoit le formulaire de /visite-gratuite/, le valide, puis envoie un e-mail
 *   à l'entreprise par la messagerie OVH (SMTP, connexion chiffrée sur le port 465).
 *   Réponse JSON si le navigateur la demande (envoi par JavaScript), sinon redirection
 *   vers /merci/ (envoi classique sans JavaScript).
 * - Tout le reste : fichiers statiques du site.
 *
 * Variables à créer dans Cloudflare (Pages > Settings > Variables and Secrets) :
 *   SMTP_USER  (texte)   adresse e-mail OVH qui envoie, ex. info@urgencesdebarras.fr
 *   SMTP_PASS  (secret)  mot de passe de cette adresse
 *   SMTP_HOST  (texte)   serveur sortant OVH ; facultatif, par défaut ssl0.ovh.net
 *   MAIL_TO    (texte)   destinataire des demandes ; facultatif, par défaut SMTP_USER
 */
import { connect } from 'cloudflare:sockets';

const DEFAULT_HOST = 'ssl0.ovh.net';
const SMTP_PORT = 465; // connexion chiffrée dès l'ouverture (SSL/TLS)
const SMTP_TIMEOUT_MS = 15000;
const MAIL_DOMAIN = 'urgencesdebarras.fr';
const FROM_NAME = 'Site Urgences Débarras';
const MIN_FILL_MS = 3000; // un humain met plus de 3 secondes à remplir le formulaire
// Doit rester identique à la liste MOTIFS de build.py
const MOTIFS = [
  'Succession, après un décès',
  'Départ en EHPAD ou maison de retraite',
  'Maison ou appartement',
  'Fin de bail, état des lieux ou vente',
  'Diogène, logement très encombré',
  'Logement insalubre ou après un sinistre',
  'Corps de ferme, grange, dépendances',
  'Cave, grenier, garage',
  'Propriétaire bailleur',
  'Local professionnel',
  'Notaire, agence, mandataire',
  'Autre',
];

/** Texte sur une ligne : sans retour à la ligne ni caractère de contrôle, longueur bornée. */
function line(form, key, max) {
  const v = form.get(key);
  const s = typeof v === 'string' ? v : '';
  return s.replace(/[\u0000-\u001F\u007F]+/g, ' ').trim().slice(0, max);
}

/** Texte libre : retours à la ligne conservés, autres caractères de contrôle retirés. */
function block(form, key, max) {
  const v = form.get(key);
  const s = (typeof v === 'string' ? v : '').replace(/\r\n/g, '\n');
  return s.replace(/[\u0000-\u0008\u000B-\u001F\u007F]+/g, ' ').trim().slice(0, max);
}

/** Texte UTF-8 en base64 (btoa n'accepte que le latin-1). */
function b64(text) {
  const bytes = new TextEncoder().encode(text);
  let bin = '';
  for (const byte of bytes) bin += String.fromCharCode(byte);
  return btoa(bin);
}

/** En-tête encodé (RFC 2047) pour les accents. */
const encodedWord = (text) => '=?UTF-8?B?' + b64(text) + '?=';

/**
 * Envoie un e-mail par SMTP (connexion chiffrée, authentification LOGIN).
 * Lève une erreur au moindre refus du serveur.
 */
async function sendSmtp({ host, user, pass, to, replyTo, subject, text }) {
  const socket = connect({ hostname: host, port: SMTP_PORT }, { secureTransport: 'on', allowHalfOpen: false });
  const reader = socket.readable.getReader();
  const writer = socket.writable.getWriter();
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  let buffer = '';

  const readLine = async () => {
    while (!buffer.includes('\r\n')) {
      const { value, done } = await reader.read();
      if (done) throw new Error('connexion fermée par le serveur');
      buffer += decoder.decode(value, { stream: true });
    }
    const end = buffer.indexOf('\r\n');
    const lineText = buffer.slice(0, end);
    buffer = buffer.slice(end + 2);
    return lineText;
  };
  /** Lit une réponse complète (les lignes « 250-… » continuent jusqu'à « 250 … »). */
  const reply = async () => {
    let last;
    do {
      last = await readLine();
    } while (/^\d{3}-/.test(last));
    return { code: Number(last.slice(0, 3)), text: last };
  };
  const expect = async (codes, step) => {
    const r = await reply();
    if (!codes.includes(r.code)) throw new Error(`SMTP ${step} : ${r.text.slice(0, 200)}`);
  };
  const send = (s) => writer.write(encoder.encode(s + '\r\n'));

  const run = async () => {
    await expect([220], 'accueil');
    await send('EHLO ' + MAIL_DOMAIN);
    await expect([250], 'EHLO');
    await send('AUTH LOGIN');
    await expect([334], 'AUTH');
    await send(b64(user));
    await expect([334], 'identifiant');
    await send(b64(pass));
    await expect([235], 'mot de passe');
    await send(`MAIL FROM:<${user}>`);
    await expect([250], 'MAIL FROM');
    await send(`RCPT TO:<${to}>`);
    await expect([250, 251], 'RCPT TO');
    await send('DATA');
    await expect([354], 'DATA');

    const body = (b64(text).match(/.{1,76}/g) || []).join('\r\n');
    const headers = [
      `From: ${encodedWord(FROM_NAME)} <${user}>`,
      `To: <${to}>`,
      ...(replyTo ? [`Reply-To: <${replyTo}>`] : []),
      `Subject: ${encodedWord(subject)}`,
      `Date: ${new Date().toUTCString()}`,
      `Message-ID: <${crypto.randomUUID()}@${MAIL_DOMAIN}>`,
      'MIME-Version: 1.0',
      'Content-Type: text/plain; charset=UTF-8',
      'Content-Transfer-Encoding: base64',
    ];
    // Le corps est en base64 : aucune ligne ne peut commencer par un point.
    await send(headers.join('\r\n') + '\r\n\r\n' + body + '\r\n.');
    await expect([250], 'envoi du message');
    await send('QUIT');
  };

  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error('SMTP : délai dépassé')), SMTP_TIMEOUT_MS);
  });
  try {
    await Promise.race([run(), timeout]);
  } finally {
    clearTimeout(timer);
    try { socket.close(); } catch (e) { /* déjà fermée */ }
  }
}

function respond(ok, status, error, wantsJson) {
  if (wantsJson) {
    return new Response(JSON.stringify(ok ? { ok: true } : { ok: false, error }), {
      status,
      headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' },
    });
  }
  return new Response(null, {
    status: 303,
    headers: { Location: ok ? '/merci/' : '/visite-gratuite/#devis', 'Cache-Control': 'no-store' },
  });
}

async function handleForm(request, env) {
  const wantsJson = (request.headers.get('Accept') || '').includes('application/json');
  if (request.method !== 'POST') {
    return new Response('Méthode non autorisée.', { status: 405, headers: { Allow: 'POST' } });
  }
  let form;
  try {
    form = await request.formData();
  } catch (e) {
    return respond(false, 400, 'Demande illisible.', wantsJson);
  }

  // Robots : champ piège rempli, horodatage incohérent, ou message rempli de liens.
  // On répond « ok » sans rien envoyer. Sans JavaScript, « t » est vide : l'envoi reste possible.
  const tRaw = line(form, 't', 20);
  const started = /^\d+$/.test(tRaw) ? Number(tRaw) : 0;
  const elapsed = Date.now() - started;
  const badTiming = tRaw !== '' && (started === 0 || elapsed < MIN_FILL_MS || elapsed > 86400000);
  const links = (block(form, 'msg', 2000) + ' ' + line(form, 'dispo', 200)).match(/https?:\/\/|www\./gi) || [];
  if (line(form, 'site', 200) !== '' || badTiming || links.length > 2) {
    return respond(true, 200, '', wantsJson);
  }

  const prenom = line(form, 'prenom', 80);
  const nom = line(form, 'nom', 80);
  const tel = line(form, 'tel', 30);
  const mail = line(form, 'mail', 160);
  const motif = line(form, 'motif', 80);
  const adresse = line(form, 'adresse', 200);
  const dispo = line(form, 'dispo', 200);
  const msg = block(form, 'msg', 2000);
  const consent = form.get('consent') === '1';

  const errors = [];
  if (!prenom || !nom) errors.push('prénom et nom');
  if (tel.replace(/\D+/g, '').length < 10) errors.push('téléphone');
  if (mail !== '' && !/^[^@\s"(),;<>]+@[^@\s"(),;<>]+\.[a-z]{2,}$/i.test(mail)) errors.push('e-mail');
  if (!MOTIFS.includes(motif)) errors.push('situation');
  if (!adresse) errors.push('adresse');
  if (!consent) errors.push('accord');
  if (errors.length) {
    return respond(false, 422, 'Il manque une information : ' + errors.join(', ') + '.', wantsJson);
  }

  const when = new Intl.DateTimeFormat('fr-FR', {
    timeZone: 'Europe/Paris', dateStyle: 'short', timeStyle: 'short',
  }).format(new Date());
  const text =
    'Nouvelle demande de visite gratuite depuis le site\n\n' +
    `Nom : ${prenom} ${nom}\n` +
    `Téléphone : ${tel}\n` +
    `E-mail : ${mail || 'non renseigné'}\n` +
    `Situation : ${motif}\n` +
    `Adresse du bien : ${adresse}\n` +
    `Disponibilités : ${dispo || 'non renseignées'}\n\n` +
    `Précisions :\n${msg || '(aucune)'}\n\n` +
    `Envoyé le ${when}. La personne a coché la case d'accord.\n`;

  const failure = "L'envoi n'a pas abouti. Appelez-nous au 06 65 30 14 90.";
  if (!env.SMTP_USER || !env.SMTP_PASS) {
    console.error('envoi : SMTP_USER ou SMTP_PASS absent');
    return respond(false, 500, failure, wantsJson);
  }
  try {
    await sendSmtp({
      host: env.SMTP_HOST || DEFAULT_HOST,
      user: env.SMTP_USER,
      pass: env.SMTP_PASS,
      to: env.MAIL_TO || env.SMTP_USER,
      replyTo: mail,
      subject: `Demande de visite : ${motif} (${nom})`,
      text,
    });
  } catch (e) {
    console.error('envoi : échec SMTP', String(e && e.message ? e.message : e));
    return respond(false, 502, failure, wantsJson);
  }
  return respond(true, 200, '', wantsJson);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/envoi') return handleForm(request, env);
    return env.ASSETS.fetch(request);
  },
};
