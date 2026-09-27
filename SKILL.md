---
name: explique-moi-claude
description: Crée une fiche de cours HTML « Explique-moi Claude » (explication pour non-développeur avec un dessin Xiaohei, une métaphore, tous les changements, les risques et un lexique cumulé), ou seulement un dessin façon croquis (personnage Xiaohei, étiquettes manuscrites en français). Claude Code uniquement. À utiliser SEULEMENT quand l'utilisateur le demande explicitement — « explique-moi », « explique-moi ça », « explique-moi ce que tu viens de faire », « pour mieux comprendre », « fais-moi une fiche », « dessine-moi… », « fais-moi un dessin de… ». Ne jamais se déclencher de sa propre initiative, même après un gros travail technique.
---

# Explique-moi Claude — la fiche

Transforme ce qui vient d'être fait dans la conversation (ou le sujet que l'utilisateur nomme) en une **fiche de cours** : une page HTML à part, avec un dessin, rangée dans le cahier de l'utilisateur. L'utilisateur n'est pas développeur : tout est en français simple, chaque partie est développée, pas résumée.

**Seulement un dessin** (« dessine-moi… », « fais-moi un dessin de… ») : pas de fiche. Lis `${CLAUDE_SKILL_DIR}/DESSIN.md` et suis-le en entier.

## Claude Code uniquement

Ce skill écrit sur le disque de l'utilisateur et lance Python. Si tu n'es pas Claude Code (claude.ai sur le web, onglet Chat de Claude Desktop, Cowork, application mobile), **n'exécute rien** : réponds en une phrase qu'explique-moi-claude ne fonctionne que dans Claude Code (terminal, VS Code, Cursor ou onglet Code de Claude Desktop).

## Quand l'utiliser

**Seulement sur demande** : « explique-moi », « explique-moi ça », « pour mieux comprendre », « fais-moi une fiche », ou `/explique-moi-claude`. Jamais de fiche spontanée, jamais de proposition de fiche non sollicitée.

Sujet par défaut : le travail fait depuis la dernière fiche (ou depuis le début de la conversation). Si l'utilisateur nomme un sujet (« explique-moi le machine learning »), la fiche porte sur ce sujet.

## Outils et réglages

- Dossier du skill : `${CLAUDE_SKILL_DIR}` (noté `<skill>` dans `DESSIN.md`)
- Fiche : `${CLAUDE_SKILL_DIR}/scripts/fiche.py`
- Dessin : `${CLAUDE_SKILL_DIR}/scripts/dessin.py`, mode d'emploi dans `${CLAUDE_SKILL_DIR}/DESSIN.md`
- Réglages : `${CLAUDE_SKILL_DIR}/config.json` — `dossier_cours` (le cahier) et `cloudflare` (identifiants du dessin). Jamais publié (ignoré par git) et conservé lors des mises à jour (`git pull`).
- Python : essaie `python`, puis `py`, puis `python3`. Dépendance : Pillow (`python -m pip install pillow` si `import PIL` échoue).

**Première utilisation** (ou si `config.json` manque, ou si le dessin répond « Identifiants Cloudflare introuvables ») : lance
`python "${CLAUDE_SKILL_DIR}/scripts/fiche.py" --config "${CLAUDE_SKILL_DIR}/config.json" --init`.
Le fichier s'ouvre dans l'éditeur de texte de l'utilisateur. Dis-lui : `dossier_cours` = où ranger ses fiches (par défaut `Documents/Explique-moi Claude`) ; `account_id` et `api_token` Cloudflare = à coller **lui-même** dans le fichier, puis enregistrer. **Ne demande jamais la clé dans la conversation et ne l'affiche jamais.**

Avant chaque fiche, vérifie que le dossier `dossier_cours` existe. S'il a été déplacé, demande à l'utilisateur où il est et corrige `config.json`.

## Déroulé

1. **Rédiger le contenu** de la fiche (voir « Contenu » plus bas), en commençant par la métaphore de la partie « L'image ».
2. **Dossier de travail** : un dossier temporaire, par exemple `%TEMP%\explique-moi-claude\` sous Windows ou `/tmp/explique-moi-claude/` ailleurs. Rien de ce dossier n'a besoin d'être gardé : `fiche.py` copie le dessin dans le cahier.
3. **Dessiner (obligatoire, une seule image)** : illustre la métaphore de « L'image » en suivant les étapes 3 à 7 de `${CLAUDE_SKILL_DIR}/DESSIN.md` : inventer l'action de Xiaohei, `gen` sans texte → **ouvrir le brut pour le regarder** → refaire si raté → `annotate` avec 3 à 5 étiquettes FR → **ouvrir le PNG final pour vérifier**. Enregistre le résultat, par exemple `dessin.png`, dans le dossier de travail.
   - Si le dessin est impossible (quota du jour épuisé, pas de réseau, identifiants manquants), ne bloque pas : mets la raison dans `illustration_erreur`, fais la fiche quand même et dis-le dans la réponse.
4. **Écrire le JSON** (UTF-8) dans le dossier de travail, par exemple `fiche.json`, au format décrit en haut de `fiche.py` (exemple complet : `${CLAUDE_SKILL_DIR}/examples/fiche-exemple.json`). Mets `"illustration"` = chemin du PNG final et une `"legende"` courte.
5. **Lancer** : `python "${CLAUDE_SKILL_DIR}/scripts/fiche.py" --config "${CLAUDE_SKILL_DIR}/config.json" "<dossier de travail>/fiche.json"`. Le script crée la fiche dans `<cahier>/fiches/` (le dessin est intégré dans le HTML et copié dans `fiches/images/`), met à jour le sommaire `index.html` et le lexique `lexique.html`, puis ouvre la fiche dans le navigateur.
6. **Répondre** : ne recopie PAS l'explication dans la conversation. Termine seulement par une ligne : `📘 Explique-moi Claude : <chemin de la fiche>` (ouverte dans ton navigateur).

## Contenu de la fiche (tout en français, chaque partie développée, pas résumée)

- **titre** : ce qui a été fait, en quelques mots.
- **projet** : le nom du dossier ou projet en cours.
- **phrase** (En une phrase) : ce qui vient de se passer, dit comme à un ami.
- **illustration** + **legende** (En un dessin) : le dessin Xiaohei de la métaphore, affiché juste après « En une phrase ».
- **image** (L'image) : une métaphore de la vie réelle (cuisine, poste, usine, sport, école…) sur plusieurs paragraphes, qui explique comment la chose fonctionne, pas seulement ce qu'elle est.
- **changements** (Ce qui a changé, en entier) : TOUS les changements, sans limite de nombre. Pour chacun : avant → maintenant → pourquoi.
- **pourquoi** (Pourquoi c'est fait comme ça) : les choix faits, les alternatives possibles, et ce qui se serait passé avec une autre option.
- **a_faire** (Ce que tu dois faire, toi) : liste vide si rien ; sinon les étapes exactes à tester, ou la décision à prendre avec les options expliquées.
- **risques** (Ce qui peut coincer) : risques, limites, ce qui pourrait casser plus tard, dit franchement. Pour CHAQUE risque, remplis `probabilite` avec une phrase simple et honnête, par exemple « Honnêtement, ça a très peu de chances d'arriver » ou « Honnêtement, c'est un vrai risque, parce que… ».
- **lexique** (Le lexique) : TOUS les termes techniques de la réponse, sans exception, chacun avec une `definition` simple et une `image` pour s'en souvenir. Ils s'ajoutent au lexique cumulé (`lexique.html`).

## Autres commandes

- `--index` : reconstruit `index.html` et `lexique.html` à partir de `donnees.json` (après un déplacement ou une modification à la main).
- `--root <dossier>` : utilise un autre cahier que celui de la config.
- `--no-open` : n'ouvre pas le navigateur.

## Erreurs

- « Champ obligatoire manquant » : `titre` et `phrase` sont indispensables.
- « Attention : fiche créée SANS dessin » : le chemin `illustration` est absent ou faux ; la fiche affiche « Dessin indisponible » avec la raison.
- Erreurs du dessin (identifiants, 401, 429, réseau) : voir la section « Erreurs » de `DESSIN.md`.
