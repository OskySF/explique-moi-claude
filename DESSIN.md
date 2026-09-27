# Dessin Xiaohei (explique-moi-claude)

Mode d'emploi du dessin, lu depuis `SKILL.md` : pour un dessin seul (« dessine-moi… ») ou pour le dessin d'une fiche. Dessine un projet, un workflow, un document ou une idée en illustrations 16:9 façon croquis (personnage Xiaohei, étiquettes manuscrites en français), générées via Cloudflare Workers AI.

Adapté du skill open source **ian-xiaohei-illustrations** de Ian (github.com/helloianneo/ian-xiaohei-illustrations, licence MIT) : le style et le personnage Xiaohei sont son travail. Cette version : français, génération via Cloudflare Workers AI (FLUX.2 klein 4B, quota gratuit ≈ 60 images/jour), texte ajouté par code (police Caveat, licence OFL, dans `fonts/`) au lieu d'être dessiné par le modèle, donc zéro faute d'orthographe.

## Claude Code uniquement

Ce skill a besoin du disque et du Python de l'utilisateur. Si tu n'es pas Claude Code (claude.ai sur le web, onglet Chat de Claude Desktop, Cowork, application mobile), **n'exécute rien** : réponds en une phrase que le dessin d'explique-moi-claude ne fonctionne que dans Claude Code (terminal, VS Code ou onglet Code de Claude Desktop).

## Outils et réglages

`<skill>` = le dossier du skill, donné dans `SKILL.md` (« Dossier du skill »).

- Script : `<skill>/scripts/dessin.py`
- Réglages (partagés avec la fiche) : `<skill>/config.json`
- Python : essaie `python`, puis `py`, puis `python3`. Dépendance : Pillow (`python -m pip install pillow` si `import PIL` échoue).

**Première utilisation** : si le script répond « Identifiants Cloudflare introuvables », suis « Première utilisation » dans `SKILL.md`. Explique à l'utilisateur qu'il doit coller lui-même son `account_id` (tableau de bord Cloudflare) et son `api_token` (jeton API avec la permission « Workers AI ») dans le fichier qui s'ouvre, puis enregistrer. **Ne demande jamais la clé dans la conversation et ne l'affiche jamais.**

## But

Transformer un projet, un process, un document ou une idée en 1 à 8 illustrations 16:9 qu'un novice comprend en 10 secondes. Pas un organigramme, pas une slide : un croquis blanc, un peu absurde, où Xiaohei fait l'action qui explique l'idée. Une seule idée par image.

## Xiaohei (le personnage)

Petit blob noir plein en forme de haricot, deux petits yeux blancs en points, pas d'oreilles/bouche/nez, bras et jambes fins en bâtons, air impassible et sérieux. Il fait une tâche absurde mais logique. Jamais décoratif : si on l'enlève et que l'idée tient encore, il est mal utilisé. Jamais mignon, jamais mascotte, jamais chat.

## Workflow

### 1. Comprendre
Lis le projet / document / idée (ou ce qui vient d'être fait dans la conversation). Si c'est un dossier de code : explore la structure, les points d'entrée, l'ordre des étapes. Repère les « moments » qui méritent un dessin (point de bascule, entrée→traitement→sortie, tri, avant/après, piège fréquent). 1 image par défaut après un travail, 1-3 pour une idée, 4-8 pour un projet entier, 9 max.

### 2. Plan (si demandé, ou si > 4 images)
Pour chaque image : où elle va, l'idée, le type (workflow, système partiel, avant/après, états, métaphore, couches, parcours, mini-BD), ce que fait Xiaohei, 1-2 objets, 3-5 étiquettes FR (1 à 3 mots). Si l'utilisateur veut valider, attends. S'il dit « génère », enchaîne.

### 3. Inventer une métaphore neuve
1) Transformer l'abstrait en action physique (bloquer, trier, peser, fermenter, filtrer, déballer, recoller…).
2) Remplacer le système par un objet low-tech (vieille machine, presse, entonnoir, balance, tiroir, puits, tuyaux, boîte aux lettres, échelle, pelote, corde à linge…). 1-2 objets max.
3) Xiaohei porte l'action (tire, pousse, tourne la manivelle, pèse, coud, bouche une fuite, trie, garde la porte…).

### 4. Générer le dessin (SANS texte)

```bash
python "<skill>/scripts/dessin.py" gen --config "<skill>/config.json" --seed <n> --out "<sortie>/01-slug-brut.png" --prompt "<prompt>"
```

Gabarit de prompt (en anglais, remplacer {…}) :

```
Minimalist black ink hand-drawn doodle on a pure white background. Thin slightly wobbly pen lines, very sparse, at least 40% empty white space, simple quick product sketch, few details. Main character: a small featureless solid-black bean-shaped blob creature, no ears, no mouth, no nose, only two tiny white dot eyes, thin black stick legs and thin stick arms, deadpan. The creature is actively {ACTION PRÉCISE avec les mains}. {GAUCHE : entrée}. {CENTRE : objet/machine}. {DROITE : sortie}. No text, no letters, no numbers, no arrows, no colors, black ink only. No shadows, no gradients, no texture. Not cute, not a cat, not a mascot, not a children's book illustration.
```

Règles : jamais de texte ni de flèches demandés au modèle. Sujet ≈ 40-60 % du cadre. Pour garder le même Xiaohei entre images, passer la meilleure image précédente en `--ref`. ≈ 30 s et ≈ 160 neurons par image (quota gratuit 10 000/jour).

### 5. Regarder le brut
Ouvre l'image (Read) AVANT d'annoter. Refais (autre seed ou prompt corrigé) si : Xiaohei a des oreilles / ressemble à un chat ou une mascotte ; il ne fait rien ; trop chargé ; lettres parasites ; fond pas blanc ; style BD enfant ou vectoriel.

### 6. Annoter par code
Écris un JSON d'étiquettes (x, y = fractions 0-1 de la largeur/hauteur), en plaçant le texte dans le blanc et en évitant que les flèches traversent le personnage :

```bash
python "<skill>/scripts/dessin.py" annotate 01-slug-brut.png 01-slug.json 01-slug.png
```

```json
[{"text":"idées en vrac","x":0.13,"y":0.30,"color":"orange","arrow_to":[0.33,0.25]},
 {"text":"il mouline","x":0.70,"y":0.22,"color":"red","arrow_to":[0.54,0.47]},
 {"text":"prêt à poster","x":0.80,"y":0.86,"color":"blue"}]
```

Couleurs : **orange** = flux / chemin principal ; **rouge** = point clé, problème, résultat ; **bleu** = note secondaire, état du système. 3 à 6 étiquettes, 1 à 3 mots. Options : `size` (défaut 46), `rotate`. Pas de titre en haut à gauche.

### 7. Vérifier puis livrer
Ouvre le PNG final : étiquettes lisibles, pas sur le trait, flèches justes. Corrige le JSON et relance `annotate` (ne regénère pas l'image pour une étiquette). Range les images dans un dossier `illustrations/` du projet courant (`01-slug.png`, `02-slug.png`…, garder les `-brut.png`). Donne le chemin et un résumé court. (Pour une fiche : une seule image, enregistrée là où `SKILL.md` l'indique.)

## Erreurs
« Identifiants Cloudflare introuvables » → voir Première utilisation ; 401/403 → jeton révoqué ou faux ; 429 ou « daily limit » → quota du jour épuisé (recharge à minuit UTC) ; erreur réseau → vérifier la connexion.
