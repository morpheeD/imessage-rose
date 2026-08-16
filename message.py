#!/usr/bin/env python3
"""
Envoie un message iMessage à chaque bénévole trouvé dans un PDF.

Usage :
    python3 imessage_rose_festival_corrige.py --dry-run
    python3 imessage_rose_festival_corrige.py --limit 1
    python3 imessage_rose_festival_corrige.py
"""

import argparse
import re
import subprocess
import sys
import time

PDF_PATH = "le plannig une fois les bénévoles affectés dans wezecrew"
WHATSAPP_LINK = "lien du groupe"
MESSAGE_TEMPLATE = (
    "Bonjour {prenom} voila le lien pour rejoindre le groupe "
    "wathapp pour ton benevolat sur le rose festival "
    "{link}  Cordialement Moustafa"
)
DELAY_BETWEEN_SENDS_SEC = 3
LINE_RE = re.compile(r"^\s*(.+?)\s+([A-Za-zÀ-ÿ'-]+)\s+(\+\d[\d ]+)\s*$")


def parse_pdf(path):
    """Lit le PDF et retourne la liste des bénévoles."""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("ERREUR : le module pypdf n'est pas installé.")
        print("Installe-le avec : python3 -m pip install pypdf")
        sys.exit(1)

    people = {}
    try:
        reader = PdfReader(path)
    except FileNotFoundError:
        print(f"ERREUR : fichier PDF introuvable : {path}")
        sys.exit(1)
    except Exception as exc:
        print(f"ERREUR lors de la lecture du PDF : {exc}")
        sys.exit(1)

    for page in reader.pages:
        text = page.extract_text() or ""
        for raw in text.splitlines():
            match = LINE_RE.match(raw)
            if not match:
                continue

            name_part, prenom, tel = match.groups()
            tel_norm = re.sub(r"\D", "", tel)
            if not tel_norm:
                continue

            people[tel_norm] = {
                "nom": name_part.strip(),
                "prenom": prenom.strip(),
                "tel": tel_norm,
                "tel_display": tel.replace(" ", ""),
            }

    return list(people.values())


def send_imessage(phone, message):
    """Envoie un message iMessage via AppleScript et Messages."""

    def esc(value):
        return value.replace("\\", "\\\\").replace('"', '\\"')

    apple_script = '''
tell application "Messages"
    set thePhone to "PHONE"
    set theBody to "BODY"
    set theService to first service whose service type is iMessage
    set theBuddy to buddy thePhone of theService
    send theBody to theBuddy
end tell
'''.replace("PHONE", esc(phone)).replace("BODY", esc(message))

    try:
        result = subprocess.run(
            ["osascript", "-e", apple_script],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, "Timeout lors de l'appel à osascript"
    except FileNotFoundError:
        return False, "osascript introuvable : ce script doit être lancé sur macOS"
    except Exception as exc:
        return False, str(exc)

    detail = result.stderr.strip() or result.stdout.strip()
    return result.returncode == 0, detail


def main():
    parser = argparse.ArgumentParser(
        description="Envoie un iMessage aux bénévoles présents dans un PDF."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="analyse le PDF et affiche les messages sans envoyer",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="nombre maximum de messages à envoyer (0 = tous)",
    )
    parser.add_argument(
        "--pdf",
        default=PDF_PATH,
        help=f"chemin du PDF (défaut : {PDF_PATH})",
    )
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit doit être supérieur ou égal à 0")

    print(f"== Parse de {args.pdf} ==")
    people = parse_pdf(args.pdf)
    print(f"{len(people)} bénévole(s) trouvé(s).\n")

    if not people:
        print("Aucun bénévole trouvé.")
        print("Vérifie le format du PDF ou adapte LINE_RE.")
        sys.exit(0)

    ok = 0
    errors = 0

    for index, person in enumerate(people, start=1):
        message = MESSAGE_TEMPLATE.format(
            prenom=person["prenom"],
            link=WHATSAPP_LINK,
        )

        print(
            f"[{index:2}/{len(people)}] "
            f"{person['nom']} {person['prenom']} "
            f"-> {person['tel_display']}"
        )

        if args.dry_run:
            print(f"      message : {message}")
            continue

        if args.limit and ok >= args.limit:
            break

        success, detail = send_imessage(person["tel_display"], message)

        if success:
            ok += 1
            print("      OK")
            if ok < len(people) and not (args.limit and ok >= args.limit):
                time.sleep(DELAY_BETWEEN_SENDS_SEC)
        else:
            errors += 1
            print(f"      ERREUR : {detail}")

    if args.dry_run:
        print("\nDRY-RUN : aucun message envoyé.")
    elif errors:
        print(f"\nTerminé : {ok} message(s) envoyé(s), {errors} échec(s).")
    else:
        print(f"\nTerminé : {ok} message(s) envoyé(s).")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
