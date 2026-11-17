<?php
/**
 * Urgences Débarras Brest : réception du formulaire de demande de visite.
 *
 * Reçoit un POST depuis /visite-gratuite/, valide les champs, puis envoie un e-mail
 * à l'entreprise. Réponse JSON si le navigateur la demande (envoi par JavaScript),
 * sinon redirection vers /merci/ (envoi classique sans JavaScript).
 *
 * À vérifier à l'installation : l'adresse d'expédition FROM doit exister sur le domaine
 * (ou être autorisée par l'hébergeur), sinon les e-mails risquent d'être classés en indésirables.
 */
declare(strict_types=1);

const TO_EMAIL   = 'info@urgencesdebarras.fr';
const FROM_EMAIL = 'site@urgencesdebarras.fr';
const FROM_NAME  = 'Site Urgences Débarras';
const MIN_FILL_MS = 3000;     // un humain met plus de 3 secondes à remplir le formulaire
const MAX_PER_HOUR = 5;       // envois maximum par adresse IP et par heure
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

ini_set('display_errors', '0');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');

$wantsJson = stripos($_SERVER['HTTP_ACCEPT'] ?? '', 'application/json') !== false;

function respond(bool $ok, int $status, string $error, bool $json): void
{
    http_response_code($status);
    if ($json) {
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode($ok ? ['ok' => true] : ['ok' => false, 'error' => $error], JSON_UNESCAPED_UNICODE);
    } else {
        header('Location: ' . ($ok ? '/merci/' : '/visite-gratuite/#devis'), true, 303);
    }
    exit;
}

/** Texte sur une ligne : sans retour à la ligne ni caractère de contrôle, longueur bornée. */
function line(string $key, int $max): string
{
    $v = $_POST[$key] ?? '';
    $v = is_string($v) ? $v : '';
    $v = preg_replace('/[\x00-\x1F\x7F]+/u', ' ', $v) ?? '';
    return mb_substr(trim($v), 0, $max);
}

/** Texte libre : retours à la ligne conservés, autres caractères de contrôle retirés. */
function block(string $key, int $max): string
{
    $raw = $_POST[$key] ?? '';
    $v = str_replace("\r\n", "\n", is_string($raw) ? $raw : '');
    $v = preg_replace('/[\x00-\x08\x0B-\x1F\x7F]+/u', ' ', $v) ?? '';
    return mb_substr(trim($v), 0, $max);
}

function tooManyRequests(): bool
{
    $ip = $_SERVER['REMOTE_ADDR'] ?? 'inconnue';
    $file = sys_get_temp_dir() . '/ud_form_' . hash('sha256', $ip . __FILE__);
    $fh = @fopen($file, 'c+');
    if ($fh === false) {
        error_log('envoi.php : impossible d\'ouvrir le compteur anti-abus');
        return false;
    }
    flock($fh, LOCK_EX); // lecture et écriture sous verrou : pas de contournement par envois simultanés
    $now = time();
    $raw = json_decode((string)stream_get_contents($fh), true);
    $hits = is_array($raw)
        ? array_values(array_filter($raw, static fn($t) => is_int($t) && $t > $now - 3600))
        : [];
    $blocked = count($hits) >= MAX_PER_HOUR;
    if (!$blocked) {
        $hits[] = $now;
        ftruncate($fh, 0);
        rewind($fh);
        fwrite($fh, (string)json_encode($hits));
    }
    flock($fh, LOCK_UN);
    fclose($fh);
    return $blocked;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    respond(false, 405, 'Méthode non autorisée.', true);
}

// Robots : champ piège rempli, horodatage incohérent, ou message rempli de liens.
// On répond « ok » sans rien envoyer. Sans JavaScript, « t » est vide : l'envoi reste
// possible, mais il passe par le limiteur d'envois.
$tRaw = line('t', 20);
$started = ctype_digit($tRaw) ? (int)$tRaw : 0;
$elapsed = (int)floor(microtime(true) * 1000) - $started;
$badTiming = $tRaw !== '' && ($started === 0 || $elapsed < MIN_FILL_MS || $elapsed > 86400000);
$tooManyLinks = preg_match_all('~https?://|www\.~i', block('msg', 2000) . ' ' . line('dispo', 200)) > 2;
if (line('site', 200) !== '' || $badTiming || $tooManyLinks) {
    respond(true, 200, '', $wantsJson);
}

$prenom  = line('prenom', 80);
$nom     = line('nom', 80);
$tel     = line('tel', 30);
$mail    = line('mail', 160);
$motif   = line('motif', 80);
$adresse = line('adresse', 200);
$dispo   = line('dispo', 200);
$msg     = block('msg', 2000);
$consent = ($_POST['consent'] ?? '') === '1';

$errors = [];
if ($prenom === '' || $nom === '') {
    $errors[] = 'prénom et nom';
}
if (strlen(preg_replace('/\D+/', '', $tel) ?? '') < 10) {
    $errors[] = 'téléphone';
}
if ($mail !== '' && (filter_var($mail, FILTER_VALIDATE_EMAIL) === false || strpbrk($mail, '"(),;<>') !== false)) {
    $errors[] = 'e-mail';
}
if (!in_array($motif, MOTIFS, true)) {
    $errors[] = 'situation';
}
if ($adresse === '') {
    $errors[] = 'adresse';
}
if (!$consent) {
    $errors[] = 'accord';
}
if ($errors) {
    respond(false, 422, 'Il manque une information : ' . implode(', ', $errors) . '.', $wantsJson);
}

if (tooManyRequests()) {
    respond(false, 429, 'Trop de demandes envoyées. Appelez-nous au 06 65 30 14 90.', $wantsJson);
}

$body = "Nouvelle demande de visite gratuite depuis le site\n\n"
    . "Nom : {$prenom} {$nom}\n"
    . "Téléphone : {$tel}\n"
    . 'E-mail : ' . ($mail !== '' ? $mail : 'non renseigné') . "\n"
    . "Situation : {$motif}\n"
    . "Adresse du bien : {$adresse}\n"
    . 'Disponibilités : ' . ($dispo !== '' ? $dispo : 'non renseignées') . "\n\n"
    . "Précisions :\n" . ($msg !== '' ? $msg : '(aucune)') . "\n\n"
    . 'Envoyé le ' . date('d/m/Y à H:i') . ". La personne a coché la case d'accord.\n";

$subject = mb_encode_mimeheader('Demande de visite : ' . $motif . ' (' . $nom . ')', 'UTF-8', 'Q');
$headers = [
    'From' => mb_encode_mimeheader(FROM_NAME, 'UTF-8', 'Q') . ' <' . FROM_EMAIL . '>',
    'MIME-Version' => '1.0',
    'Content-Type' => 'text/plain; charset=UTF-8',
    'Content-Transfer-Encoding' => '8bit',
];
if ($mail !== '') {
    $headers['Reply-To'] = $mail; // validé par FILTER_VALIDATE_EMAIL : aucun retour à la ligne possible
}

if (!mail(TO_EMAIL, $subject, $body, $headers, '-f' . FROM_EMAIL)) {
    error_log('envoi.php : la fonction mail() a échoué');
    respond(false, 500, 'L\'envoi n\'a pas abouti. Appelez-nous au 06 65 30 14 90.', $wantsJson);
}

respond(true, 200, '', $wantsJson);
