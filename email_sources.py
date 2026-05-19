"""
Module de lecture des emails (Google Alerts, LinkedIn Jobs alerts).
Se branche sur le même pipeline Claude → Telegram que bot.py.

Setup nécessaire :
1. Activer 2FA sur le compte Gmail
2. Créer un App Password : myaccount.google.com → Security → App passwords
3. Ajouter aux secrets GitHub : GMAIL_USER, GMAIL_APP_PASSWORD
"""
import os
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


EMAIL_SOURCES = [
    {
        "name": "Google Alerts",
        "from": "googlealerts-noreply@google.com",
    },
    {
        "name": "LinkedIn Jobs",
        "from": "jobs-noreply@linkedin.com",
    },
    {
        "name": "LinkedIn Job Alerts",
        "from": "jobalerts-noreply@linkedin.com",
    },
]


def connect_imap():
    """Se connecte à Gmail via IMAP. Retourne None si pas configuré."""
    user = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    server = os.environ.get("IMAP_SERVER", "imap.gmail.com")

    if not user or not password:
        return None

    mail = imaplib.IMAP4_SSL(server)
    mail.login(user, password)
    mail.select("INBOX")
    return mail


def fetch_recent_unread(mail, sender, since_hours=26):
    """Récupère les emails non lus d'un expéditeur sur les dernières N heures.
    26h (pas 24) évite de rater des emails si le bot tourne un peu plus tard."""
    since_date = (datetime.now() - timedelta(hours=since_hours)).strftime("%d-%b-%Y")
    status, ids = mail.search(None, f'(FROM "{sender}" SINCE {since_date} UNSEEN)')
    if status != "OK" or not ids[0]:
        return []

    out = []
    for msg_id in ids[0].split():
        _, data = mail.fetch(msg_id, "(RFC822)")
        msg = email.message_from_bytes(data[0][1])
        out.append((msg_id, msg))
    return out


def decode_subject(msg):
    raw = msg.get("Subject", "")
    parts = decode_header(raw)
    out = []
    for content, enc in parts:
        if isinstance(content, bytes):
            out.append(content.decode(enc or "utf-8", errors="ignore"))
        else:
            out.append(content)
    return "".join(out)


def extract_body(msg, max_chars=10000):
    """Extrait le texte d'un email, fallback HTML→texte si nécessaire."""
    text_body = ""
    html_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp:
                continue
            try:
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                decoded = payload.decode(charset, errors="ignore")
                if ctype == "text/plain" and not text_body:
                    text_body = decoded
                elif ctype == "text/html" and not html_body:
                    html_body = decoded
            except Exception:
                continue
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            text_body = msg.get_payload(decode=True).decode(charset, errors="ignore")
        except Exception:
            pass

    body = text_body
    if not body and html_body:
        body = BeautifulSoup(html_body, "html.parser").get_text(separator="\n", strip=True)

    lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
    body = "\n".join(lines)
    return body[:max_chars]


def mark_as_read(mail, msg_id):
    """Marque l'email comme lu pour ne pas le re-traiter au prochain run."""
    mail.store(msg_id, "+FLAGS", "\\Seen")


def process_email_sources(client, profile, analyze_fn, format_fn, send_fn,
                          tg_token, tg_chat):
    """Traite tous les emails des sources configurées.

    Arguments injectés (depuis bot.py) :
      analyze_fn : analyze_with_claude
      format_fn  : format_message
      send_fn    : send_telegram

    Retourne le nombre de notifications envoyées.
    """
    mail = connect_imap()
    if mail is None:
        print("⊘ Email sources non configurées (GMAIL_USER manquant), skip.")
        return 0

    notified = 0
    try:
        for source in EMAIL_SOURCES:
            source_name = source["name"]
            sender = source["from"]
            print(f"→ {source_name} ({sender})")

            try:
                emails = fetch_recent_unread(mail, sender)
            except Exception as e:
                print(f"  ⚠ erreur IMAP : {e}")
                continue

            if not emails:
                print("  aucun email non lu")
                continue

            print(f"  {len(emails)} email(s) à traiter")

            for msg_id, msg in emails:
                try:
                    subject = decode_subject(msg)
                    body = extract_body(msg)

                    if not body or len(body) < 100:
                        mark_as_read(mail, msg_id)
                        continue

                    label = f"{source_name} — {subject[:80]}"
                    print(f"  Analyse : {subject[:60]}")

                    analysis = analyze_fn(client, label, "", body, profile)

                    if analysis.get("is_new_opportunity"):
                        out = format_fn(label, "", analysis)
                        send_fn(tg_token, tg_chat, out)
                        notified += 1
                        print(f"    ✓ notifié (score {analysis.get('priority_score')})")
                    else:
                        print(f"    pas pertinent : {analysis.get('reasoning', '')[:60]}")

                    mark_as_read(mail, msg_id)

                except Exception as e:
                    print(f"  ⚠ erreur traitement email : {e}")
                    continue

    finally:
        try:
            mail.close()
            mail.logout()
        except Exception:
            pass

    return notified
