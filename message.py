#!/usr/bin/env python3
"""
Envoie un message iMessage à chaque bénévole trouvé dans un PDF.

Usage :
    python3 message.py --dry-run
    python3 message.py --limit 1
    python3 message.py
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


def normalize_phone(phone_str):
    """Extrait les chiffres d'un numéro de téléphone et génère les variantes pour comparaison."""
    digits = re.sub(r"\D", "", str(phone_str))
    if not digits:
        return set()

    variations = {digits}
    # Si le numéro commence par 0 et comporte 10 chiffres (ex: 0612345678 -> 33612345678)
    if len(digits) == 10 and digits.startswith("0"):
        variations.add("33" + digits[1:])
    # Si le numéro commence par 33 et comporte 11 chiffres (ex: 33612345678 -> 0612345678)
    elif len(digits) == 11 and digits.startswith("33"):
        variations.add("0" + digits[2:])

    # Conserver les 9 derniers chiffres s'il y a au moins 9 chiffres
    if len(digits) >= 9:
        variations.add(digits[-9:])

    return variations


def load_group_members(file_path):
    """
    Charge les membres du groupe WhatsApp depuis un fichier texte ou CSV.
    Retourne un ensemble de clés (numéros normalisés et noms en minuscules).
    """
    members = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Normaliser en tant que numéro
                phone_vars = normalize_phone(line)
                if phone_vars:
                    members.update(phone_vars)

                # Conserver également en minuscules sans ponctuation pour les noms
                clean_str = re.sub(r"\s+", " ", line.lower().strip())
                members.add(clean_str)

    except FileNotFoundError:
        print(f"ERREUR : fichier de membres du groupe introuvable : {file_path}")
        sys.exit(1)
    except Exception as exc:
        print(f"ERREUR lors de la lecture du fichier de membres : {exc}")
        sys.exit(1)

    return members


def is_person_in_group(person, group_members):
    """Vérifie si une personne est déjà présente dans les membres du groupe."""
    if not group_members:
        return False

    # Vérification par téléphone
    tel_vars = normalize_phone(person.get("tel", "")) | normalize_phone(person.get("tel_display", ""))
    if tel_vars & group_members:
        return True

    # Vérification par nom / prénom
    nom = person.get("nom", "").lower().strip()
    prenom = person.get("prenom", "").lower().strip()
    full_name_1 = f"{prenom} {nom}"
    full_name_2 = f"{nom} {prenom}"

    if full_name_1 in group_members or full_name_2 in group_members:
        return True

    return False


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
    parser.add_argument(
        "--group-members-file",
        help="chemin du fichier contenant la liste des membres déjà présents dans le groupe WhatsApp (numéros ou noms)",
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

    group_members = set()
    if args.group_members_file:
        print(f"== Chargement des membres du groupe WhatsApp depuis {args.group_members_file} ==")
        group_members = load_group_members(args.group_members_file)
        print(f"Membres du groupe chargés.\n")

    people_to_send = []
    already_in_group = []

    for person in people:
        if is_person_in_group(person, group_members):
            already_in_group.append(person)
        else:
            people_to_send.append(person)

    if group_members:
        print(f"{len(already_in_group)} bénévole(s) déjà dans le groupe WhatsApp (ignoré(s)).")
        print(f"{len(people_to_send)} bénévole(s) à contacter par SMS.\n")

    ok = 0
    errors = 0

    for index, person in enumerate(people_to_send, start=1):
        message = MESSAGE_TEMPLATE.format(
            prenom=person["prenom"],
            link=WHATSAPP_LINK,
        )

        print(
            f"[{index:2}/{len(people_to_send)}] "
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
            if ok < len(people_to_send) and not (args.limit and ok >= args.limit):
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
