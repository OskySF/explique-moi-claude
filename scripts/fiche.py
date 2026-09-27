#!/usr/bin/env python3
"""fiche.py — transforme une explication (JSON) en fiche HTML « Explique-moi Claude »,
met à jour le sommaire (index.html) et le lexique (lexique.html), puis ouvre la fiche.

  python fiche.py --config CONFIG fiche.json [--no-open]   # crée une fiche
  python fiche.py --config CONFIG --index                  # reconstruit sommaire + lexique
  python fiche.py --config CONFIG --init                   # crée CONFIG s'il manque et l'ouvre

CONFIG = le fichier de réglages du skill (<dossier du skill>/config.json), partagé
avec le dessin : {"dossier_cours": "...", "cloudflare": {"account_id": "...", "api_token": "..."}}.
Dossier des cours : --root, sinon "dossier_cours" de CONFIG, sinon ~/Documents/Explique-moi Claude.

Format du JSON (tout en français, texte simple ; **gras**, *italique* et `code` autorisés) :
{
  "titre": "Installer le pack Claude Code",
  "projet": "illustrations annotées",
  "phrase": "Ce qui vient de se passer, dit comme à un ami.",
  "illustration": "dessin.png",        (dessin Xiaohei annoté ; chemin absolu ou relatif au JSON)
  "legende": "Xiaohei trie les idées", (optionnel)
  "illustration_erreur": "...",        (optionnel : pourquoi il n'y a pas de dessin)
  "image": ["paragraphe 1 de la métaphore", "paragraphe 2"],
  "changements": [{"avant": "...", "apres": "...", "pourquoi": "..."}],
  "pourquoi": ["paragraphe sur les choix faits et les alternatives"],
  "a_faire": ["étape 1", "étape 2"],            (liste vide = rien à faire)
  "risques": [{"risque": "...", "probabilite": "Honnêtement, ça a très peu de chances d'arriver."}],
  "lexique": [{"terme": "CLAUDE.md", "definition": "...", "image": "..."}]
}
"""
import argparse, base64, datetime, html, json, os, re, shutil, subprocess, sys, unicodedata, webbrowser
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MARQUE = "Explique-moi Claude"
DEFAULT_COURS = Path.home() / "Documents" / MARQUE
CONFIG_MODELE = {
    "dossier_cours": str(DEFAULT_COURS),
    "cloudflare": {"account_id": "", "api_token": ""},
}

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

CSS = """
:root{--bg:#faf8f4;--card:#fff;--ink:#1d1d1f;--mute:#6b6b70;--line:#ece8e1;--orange:#f0801e;--red:#d7263d;--blue:#2b6cb0;--green:#2f9e66;--shadow:0 1px 2px rgba(0,0,0,.04),0 8px 24px rgba(0,0,0,.05)}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--card:#1d1d20;--ink:#f2f2f3;--mute:#a0a0a8;--line:#2c2c31;--shadow:none}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--blue)}
.wrap{max-width:780px;margin:0 auto;padding:40px 16px 80px}
.top{display:flex;justify-content:space-between;align-items:center;font-size:14px;margin-bottom:10px}
.kicker{font-family:Caveat,cursive;font-size:30px;color:var(--orange);margin:0}
h1{font-size:30px;line-height:1.2;margin:4px 0 8px}
.meta{color:var(--mute);font-size:14px;margin-bottom:28px}
.hero{background:var(--ink);color:var(--bg);border-radius:18px;padding:22px 24px;font-size:19px;font-weight:600;margin-bottom:26px}
.hero span{display:block;font-family:Caveat,cursive;font-size:24px;font-weight:700;color:var(--orange);margin-bottom:2px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px 24px;margin:18px 0;box-shadow:var(--shadow)}
.card h2{display:flex;align-items:center;gap:10px;font-size:18px;margin:0 0 12px}
.dot{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;font-size:15px;flex:none;color:#fff}
.o{background:var(--orange)}.r{background:var(--red)}.b{background:var(--blue)}.g{background:var(--green)}.k{background:#555}
.dessin img{display:block;width:100%;height:auto;border-radius:12px;border:1px solid var(--line);background:#fff}
.dessin figcaption{font-family:Caveat,cursive;font-size:22px;color:var(--mute);text-align:center;margin-top:8px}
.image p{font-size:17px}
.change{display:grid;grid-template-columns:1fr auto 1fr;gap:10px;align-items:stretch;margin:14px 0 4px}
.change .before,.change .after{border-radius:12px;padding:12px 14px;font-size:15px}
.before{background:rgba(215,38,61,.08)}.after{background:rgba(47,158,102,.10)}
.change .arrow{align-self:center;font-size:22px;color:var(--orange)}
.lbl{display:block;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);margin-bottom:3px}
.why{font-size:14.5px;color:var(--mute);margin:6px 2px 16px}
.why b{color:var(--ink)}
ol.steps{counter-reset:s;list-style:none;padding:0;margin:0}
ol.steps li{counter-increment:s;position:relative;padding:8px 0 8px 44px}
ol.steps li::before{content:counter(s);position:absolute;left:0;top:6px;width:30px;height:30px;border-radius:50%;background:var(--green);color:#fff;display:grid;place-items:center;font-weight:700;font-size:14px}
.warn li{margin:8px 0}
.odds{display:block;font-style:italic;color:var(--mute);font-size:14.5px;margin-top:2px}
dl{margin:0}
dt{font-weight:700;margin-top:14px}
dt code{background:rgba(240,128,30,.14);color:var(--orange);padding:1px 7px;border-radius:6px;font-size:14px;font-family:ui-monospace,Consolas,monospace}
dd{margin:4px 0 0 0}
dd i{display:block;color:var(--mute);font-style:normal;font-size:14.5px;margin-top:2px}
dd i::before{content:"🖼 "}
code{font-family:ui-monospace,Consolas,monospace;font-size:.92em;background:rgba(127,127,127,.12);padding:1px 5px;border-radius:5px}
.search{width:100%;padding:12px 16px;border-radius:12px;border:1px solid var(--line);background:var(--card);color:var(--ink);font-size:16px;margin:6px 0 14px}
.fiche{display:flex;gap:16px;align-items:center;text-decoration:none;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 18px;margin:10px 0;box-shadow:var(--shadow)}
.fiche:hover{border-color:var(--orange)}
.fiche .txt{flex:1;min-width:0}
.fiche b{display:block;font-size:17px}
.fiche small{color:var(--mute)}
.fiche p{margin:4px 0 0;font-size:15px;color:var(--mute)}
.fiche img{width:120px;height:69px;object-fit:cover;border-radius:8px;border:1px solid var(--line);background:#fff;flex:none}
.letters{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 8px}
.letters a{text-decoration:none;font-weight:700;font-size:14px;border:1px solid var(--line);background:var(--card);border-radius:8px;padding:3px 9px;color:var(--ink)}
.letter{font-family:Caveat,cursive;font-size:34px;color:var(--orange);margin:26px 0 0;border-bottom:1px solid var(--line)}
dl>.letter:first-child{margin-top:0}
.used{font-size:13px;color:var(--mute);margin-top:4px}
.empty{color:var(--mute);font-style:italic}
@media (max-width:560px){.change{grid-template-columns:1fr}.change .arrow{transform:rotate(90deg);justify-self:center}.fiche img{display:none}}
"""

HEAD = ('<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"><title>__TITLE__</title>'
        '<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@700&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">'
        '<style>' + CSS + '</style></head><body><div class="wrap">')
FOOT = '</div></body></html>'
FILTRE = """<script>
function filt(){var q=document.getElementById('q').value.toLowerCase();document.querySelectorAll('.item').forEach(function(e){e.style.display=e.textContent.toLowerCase().indexOf(q)>-1?'':'none';});}
</script>"""


# ---------------------------------------------------------------- outils
def t(s):
    """Échappe le HTML puis autorise **gras**, *italique* et `code`."""
    s = html.escape(str(s))
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*([^*\s][^*]*)\*", r"<em>\1</em>", s)
    return s


def ascii_lower(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", ascii_lower(s)).strip("-")[:50] or "fiche"


def date_fr(d):
    return f"{d.day} {MOIS[d.month - 1]} {d.year} à {d.hour:02d}h{d.minute:02d}"


def lire_config(path):
    if path and Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return {}


def dossier_cours(arg, cfg):
    if arg:
        return Path(arg).expanduser()
    v = cfg.get("dossier_cours")
    if v:
        return Path(os.path.expandvars(v)).expanduser()
    return DEFAULT_COURS


def ouvrir_fichier(path):
    """Ouvre un fichier dans l'éditeur de texte du système (jamais dans la conversation)."""
    if sys.platform.startswith("win"):
        subprocess.Popen(["notepad.exe", str(path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-e", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def init_config(path):
    path = Path(path)
    if path.exists():
        print("Config déjà présente ->", path)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(CONFIG_MODELE, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Config créée ->", path)
    cf = lire_config(path).get("cloudflare") or {}
    manque = [k for k in ("account_id", "api_token") if not cf.get(k)]
    if manque:
        print("À remplir par l'utilisateur :", ", ".join("cloudflare." + k for k in manque))
        ouvrir_fichier(path)


def load_data(root):
    f = root / "donnees.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {"fiches": [], "lexique": {}}


# ---------------------------------------------------------------- fiche
def render_dessin(f, stem, root, base):
    """Copie le dessin dans fiches/images/ et renvoie (html, chemin relatif à root ou None)."""
    src = f.get("illustration")
    path = (base / src) if src and not Path(src).is_absolute() else (Path(src) if src else None)
    titre = '<h2><span class="dot o">✎</span>En un dessin</h2>'
    if path and path.exists():
        images = root / "fiches" / "images"
        images.mkdir(parents=True, exist_ok=True)
        dst = images / (stem + path.suffix.lower())
        shutil.copyfile(path, dst)
        mime = MIME.get(dst.suffix, "image/png")
        b64 = base64.b64encode(dst.read_bytes()).decode()
        leg = f'<figcaption>{t(f["legende"])}</figcaption>' if f.get("legende") else ""
        alt = html.escape(f.get("legende") or f["titre"])
        return (f'<figure class="card dessin" style="margin:18px 0">{titre}'
                f'<img src="data:{mime};base64,{b64}" alt="{alt}">{leg}</figure>',
                dst.relative_to(root).as_posix())
    raison = f.get("illustration_erreur") or (f"fichier introuvable : {src}" if src else "aucun dessin fourni")
    return (f'<div class="card dessin">{titre}<p class="empty">Dessin indisponible pour cette fiche ({t(raison)}).</p></div>',
            None)


def render_fiche(f, when, dessin):
    h = [HEAD.replace("__TITLE__", MARQUE + " · " + html.escape(f["titre"]))]
    h.append('<div class="top"><a href="../index.html">← Sommaire</a><a href="../lexique.html">Lexique →</a></div>')
    h.append(f'<p class="kicker">{MARQUE}</p>')
    h.append(f'<h1>{t(f["titre"])}</h1>')
    proj = f' · projet : {t(f["projet"])}' if f.get("projet") else ""
    h.append(f'<div class="meta">{date_fr(when)}{proj}</div>')
    h.append(f'<div class="hero"><span>En une phrase</span>{t(f["phrase"])}</div>')
    h.append(dessin)

    if f.get("image"):
        h.append('<div class="card image"><h2><span class="dot o">🖼</span>L\'image</h2>')
        h += [f"<p>{t(p)}</p>" for p in f["image"]]
        h.append("</div>")

    if f.get("changements"):
        h.append('<div class="card"><h2><span class="dot b">↺</span>Ce qui a changé, en entier</h2>')
        for c in f["changements"]:
            h.append('<div class="change">'
                     f'<div class="before"><span class="lbl">Avant</span>{t(c.get("avant", ""))}</div>'
                     '<div class="arrow">→</div>'
                     f'<div class="after"><span class="lbl">Maintenant</span>{t(c.get("apres", ""))}</div></div>')
            if c.get("pourquoi"):
                h.append(f'<p class="why"><b>Pourquoi :</b> {t(c["pourquoi"])}</p>')
        h.append("</div>")

    if f.get("pourquoi"):
        h.append('<div class="card"><h2><span class="dot k">?</span>Pourquoi c\'est fait comme ça</h2>')
        h += [f"<p>{t(p)}</p>" for p in f["pourquoi"]]
        h.append("</div>")

    h.append('<div class="card"><h2><span class="dot g">✓</span>Ce que tu dois faire, toi</h2>')
    if f.get("a_faire"):
        h.append('<ol class="steps">' + "".join(f"<li>{t(s)}</li>" for s in f["a_faire"]) + "</ol>")
    else:
        h.append('<p>Rien. Tout est fait de ton côté.</p>')
    h.append("</div>")

    if f.get("risques"):
        h.append('<div class="card"><h2><span class="dot r">!</span>Ce qui peut coincer</h2><ul class="warn">')
        for r in f["risques"]:
            odds = f'<span class="odds">{t(r["probabilite"])}</span>' if r.get("probabilite") else ""
            h.append(f'<li>{t(r["risque"])} {odds}</li>')
        h.append("</ul></div>")

    if f.get("lexique"):
        h.append('<div class="card"><h2><span class="dot o">Aa</span>Le lexique</h2><dl>')
        for l in f["lexique"]:
            img = f'<i>{t(l["image"])}</i>' if l.get("image") else ""
            h.append(f'<dt><code>{html.escape(l["terme"])}</code></dt><dd>{t(l["definition"])}{img}</dd>')
        h.append("</dl></div>")
    h.append(FOOT)
    return "".join(h)


# ---------------------------------------------------------------- sommaire + lexique
def render_index(data, root):
    n, m = len(data["fiches"]), len(data["lexique"])
    h = [HEAD.replace("__TITLE__", MARQUE + " · Sommaire")]
    h.append(f'<div class="top"><span></span><a href="lexique.html">Lexique ({m} mot{"s" if m > 1 else ""}) →</a></div>')
    h.append(f'<p class="kicker">{MARQUE}</p><h1>Mon cahier de cours</h1>')
    h.append(f'<div class="meta">{n} fiche{"s" if n > 1 else ""} · {m} mot{"s" if m > 1 else ""} appris</div>')
    h.append('<input class="search" id="q" placeholder="Chercher une fiche…" oninput="filt()">')
    if not data["fiches"]:
        h.append('<p class="empty">Aucune fiche pour l\'instant.</p>')
    for x in reversed(data["fiches"]):
        proj = f' · {html.escape(x["projet"])}' if x.get("projet") else ""
        vign = f'<img src="{html.escape(x["image"])}" alt="">' if x.get("image") else ""
        h.append(f'<a class="fiche item" href="fiches/{html.escape(x["fichier"])}">{vign}<span class="txt"><b>{t(x["titre"])}</b>'
                 f'<small>{html.escape(x["date"])}{proj}</small><p>{t(x["phrase"])}</p></span></a>')
    h.append(FILTRE + FOOT)
    (root / "index.html").write_text("".join(h), encoding="utf-8")


def lettre(terme):
    c = ascii_lower(terme.lstrip(".~/_-"))[:1].upper()
    return c if c.isalpha() else "#"


def render_lexique(data, root):
    termes = sorted(data["lexique"], key=lambda s: ascii_lower(s.lstrip(".~/_-")))
    m = len(termes)
    h = [HEAD.replace("__TITLE__", MARQUE + " · Lexique")]
    h.append('<div class="top"><a href="index.html">← Sommaire</a><span></span></div>')
    h.append(f'<p class="kicker">{MARQUE}</p><h1>Mon lexique</h1>')
    h.append(f'<div class="meta">{m} mot{"s" if m > 1 else ""} appris, de fiche en fiche</div>')
    groupes = {}
    for terme in termes:
        groupes.setdefault(lettre(terme), []).append(terme)
    h.append('<nav class="letters">' + "".join(f'<a href="#l-{k}">{k}</a>' for k in groupes) + '</nav>')
    h.append('<input class="search" id="q" placeholder="Chercher un mot…" oninput="filt()">')
    if not termes:
        h.append('<p class="empty">Aucun mot pour l\'instant.</p>')
    h.append('<div class="card"><dl>')
    for k, liste in groupes.items():
        h.append(f'<div class="letter" id="l-{k}">{k}</div>')
        for terme in liste:
            l = data["lexique"][terme]
            img = f'<i>{t(l["image"])}</i>' if l.get("image") else ""
            liens = ", ".join(f'<a href="fiches/{html.escape(fi)}">{t(ti)}</a>' for fi, ti in l.get("vu_dans", [])[-5:])
            used = f'<div class="used">Vu dans : {liens}</div>' if liens else ""
            h.append(f'<div class="item"><dt><code>{html.escape(terme)}</code></dt><dd>{t(l["definition"])}{img}{used}</dd></div>')
    h.append('</dl></div>' + FILTRE + FOOT)
    (root / "lexique.html").write_text("".join(h), encoding="utf-8")


# ---------------------------------------------------------------- programme
def main():
    ap = argparse.ArgumentParser(description=f"Crée une fiche « {MARQUE} ».")
    ap.add_argument("fiche", nargs="?", help="fichier JSON de la fiche")
    ap.add_argument("--config", help="fichier de réglages (<dossier du skill>/config.json)")
    ap.add_argument("--root", help="dossier des cours (prioritaire sur la config)")
    ap.add_argument("--init", action="store_true", help="crée la config si elle manque et l'ouvre pour la remplir")
    ap.add_argument("--index", action="store_true", help="reconstruit seulement le sommaire et le lexique")
    ap.add_argument("--no-open", action="store_true", help="ne pas ouvrir la fiche dans le navigateur")
    args = ap.parse_args()

    if args.init:
        if not args.config:
            ap.error("--init a besoin de --config")
        init_config(args.config); return

    root = dossier_cours(args.root, lire_config(args.config))
    root.mkdir(parents=True, exist_ok=True)
    data = load_data(root)
    if args.index:
        render_index(data, root); render_lexique(data, root)
        print("OK ->", root / "index.html", "+", root / "lexique.html"); return
    if not args.fiche:
        ap.error("donne un fichier JSON, ou --index")

    src = Path(args.fiche)
    f = json.loads(src.read_text(encoding="utf-8-sig"))
    for champ in ("titre", "phrase"):
        if not f.get(champ):
            sys.exit(f"Champ obligatoire manquant dans le JSON : {champ}")
    now = datetime.datetime.now()
    fiches = root / "fiches"
    fiches.mkdir(parents=True, exist_ok=True)
    stem = f"{now:%Y-%m-%d-%H%M}-{slug(f['titre'])}"
    out, i = fiches / f"{stem}.html", 2
    while out.exists():
        stem = f"{now:%Y-%m-%d-%H%M}-{slug(f['titre'])}-{i}"; out = fiches / f"{stem}.html"; i += 1

    dessin, image_rel = render_dessin(f, stem, root, src.resolve().parent)
    out.write_text(render_fiche(f, now, dessin), encoding="utf-8")

    entree = {"titre": f["titre"], "projet": f.get("projet", ""), "phrase": f["phrase"],
              "date": date_fr(now), "fichier": out.name}
    if image_rel:
        entree["image"] = image_rel
    data["fiches"].append(entree)
    for l in f.get("lexique", []):
        e = data["lexique"].setdefault(l["terme"], {"definition": l["definition"], "image": l.get("image", ""), "vu_dans": []})
        e["vu_dans"].append([out.name, f["titre"]])
    (root / "donnees.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    render_index(data, root); render_lexique(data, root)
    print("OK ->", out)
    if not image_rel:
        print("Attention : fiche créée SANS dessin.")
    if not args.no_open:
        webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()
