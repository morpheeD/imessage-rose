# iMessage Rose Festival

Ce projet permet d'extraire automatiquement la liste des bénévoles à partir d'un fichier PDF (planning Wezecrew) et de leur envoyer un iMessage contenant le lien d'invitation au groupe WhatsApp du bénévolat.

Pour éviter de renvoyer le lien aux bénévoles qui ont déjà rejoint le groupe, le script permet d'utiliser un fichier contenant la liste des membres actuels du groupe WhatsApp.

---

## Fonctionnalités

- Extraction automatique des numéros et noms de bénévoles depuis le PDF.
- Vérification préalable des membres déjà présents dans le groupe WhatsApp (par numéro de téléphone ou nom/prénom).
- Envoi automatique d'un iMessage avec temporisation entre chaque envoi.
- Mode `--dry-run` pour tester sans envoyer de messages.

---

## Installation

### Prérequis
- **macOS** (nécessaire pour l'envoi d'iMessage via `osascript` / l'application Messages).
- **Python 3.8+**
- Bibliothèque `pypdf` :
  ```bash
  python3 -m pip install pypdf
  ```

---

## Utilisation

### Commandes de base

- **Exécution à blanc (recommandé pour vérifier avant envoi) :**
  ```bash
  python3 message.py --dry-run
  ```

- **Filtrer avec le fichier des membres WhatsApp :**
  ```bash
  python3 message.py --group-members-file membres_whatsapp.txt --dry-run
  ```

- **Limiter à un certain nombre d'envois :**
  ```bash
  python3 message.py --limit 5
  ```

- **Spécifier un fichier PDF personnalisé :**
  ```bash
  python3 message.py --pdf "/chemin/vers/votre_planning.pdf"
  ```

---

## Comment générer le fichier des membres WhatsApp (`--group-members-file`)

Le fichier transmis avec l'argument `--group-members-file` est un simple fichier texte ou CSV. Il doit contenir **un numéro de téléphone ou un nom par ligne**.

### Format du fichier (`membres_whatsapp.txt`)

Exemple de contenu :
```text
0612345678
+33698765432
Jean Dupont
Marie Curie
```

> **Note :** Le script prend en compte les équivalences de numéros (ex: `0612345678`, `+33612345678`, `33612345678`).

---

### Méthodes pour récupérer la liste des membres du groupe WhatsApp

#### Méthode 1 : Depuis WhatsApp Web (Copie rapide)
1. Ouvrez [WhatsApp Web](https://web.whatsapp.com/) dans votre navigateur Google Chrome ou Firefox.
2. Ouvrez la discussion de votre groupe WhatsApp.
3. Cliquez sur l'en-tête du groupe en haut pour ouvrir les **Infos du groupe**.
4. Faites défiler vers le bas jusqu'à la section **Membres** (ou la liste des participants sous le nom du groupe).
5. Sélectionnez et copiez le texte contenant les numéros/noms des membres.
6. Collez le texte dans un fichier nommé `membres_whatsapp.txt` et enregistrez-le.

#### Méthode 2 : Extraction via la console du navigateur (WhatsApp Web)
1. Ouvrez l'en-tête du groupe WhatsApp sur WhatsApp Web.
2. Ouvrez la console du navigateur (`F12` ou `Clic droit -> Inspecter -> Console`).
3. Collez l'extrait JavaScript suivant pour extraire les numéros et noms affichés :
   ```javascript
   const members = Array.from(document.querySelectorAll('span[title]'))
     .map(el => el.getAttribute('title'))
     .filter(t => t && (t.startsWith('+') || t.match(/\d/)));
   console.log([...new Set(members)].join('\n'));
   ```
4. Copiez le résultat affiché dans la console et enregistrez-le dans `membres_whatsapp.txt`.

#### Méthode 3 : Exportation manuelle depuis l'application mobile
Vous pouvez également noter ou copier les numéros/noms depuis les infos du groupe sur votre téléphone et créer le fichier texte manuellement.

---

## Tests unitaires

Pour exécuter la suite de tests automatisés :
```bash
python3 -m unittest discover
```
