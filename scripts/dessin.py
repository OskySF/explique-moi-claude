#!/usr/bin/env python3
"""dessin.py — génère un dessin Xiaohei via Cloudflare Workers AI (FLUX.2 klein 4B)
puis ajoute des annotations manuscrites (rouge / orange / bleu) par code.

  python dessin.py gen --config CONFIG --prompt "..." --out 01-brut.png [--seed 42] [--ref ref.png]
  python dessin.py annotate 01-brut.png 01-labels.json 01-final.png

Identifiants Cloudflare : variables d'environnement CF_ACCOUNT_ID et CF_API_TOKEN,
sinon la section "cloudflare" de CONFIG (<dossier du skill>/config.json, voir config.example.json).

labels.json = liste de :
  {"text": "idée", "x": 0.72, "y": 0.20, "color": "red|orange|blue|black",
   "size": 44, "rotate": -4, "arrow_to": [0.55, 0.40]}   (x, y en fraction de l'image)
"""
import argparse, base64, io, json, math, os, random, sys
import urllib.request, urllib.error
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SKILL_DIR = Path(__file__).resolve().parent.parent
FONT = SKILL_DIR / "fonts" / "Caveat-Bold.ttf"
DEFAULT_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"
COLORS = {"red": (215, 38, 61), "orange": (240, 128, 30), "blue": (43, 108, 176), "black": (20, 20, 20)}


# ---------------------------------------------------------------- configuration
def cloudflare(config):
    """Renvoie (account_id, api_token, model) depuis l'environnement ou la config du skill."""
    cfg = {}
    if config and Path(config).exists():
        cfg = json.loads(Path(config).read_text(encoding="utf-8-sig")).get("cloudflare") or {}
    account = os.environ.get("CF_ACCOUNT_ID") or cfg.get("account_id")
    token = os.environ.get("CF_API_TOKEN") or cfg.get("api_token")
    model = os.environ.get("CF_MODEL") or cfg.get("model") or DEFAULT_MODEL
    if not (account and token):
        sys.exit(f"Identifiants Cloudflare introuvables dans {config or '(aucune config fournie)'}. "
                 "Lance l'initialisation (fiche.py --init) ou définis CF_ACCOUNT_ID et CF_API_TOKEN.")
    return account, token, model


# ---------------------------------------------------------------- génération
def gen(prompt, out, width=1344, height=768, seed=None, ref=None, config=None):
    account, token, model = cloudflare(config)
    boundary = "----xiaohei" + str(random.randint(10**9, 10**10))
    parts = []

    def field(name, value):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())

    field("prompt", prompt)
    field("width", str(width))
    field("height", str(height))
    if seed is not None:
        field("seed", str(seed))
    if ref:
        from PIL import Image
        im = Image.open(ref).convert("RGB")
        im.thumbnail((512, 512))
        buf = io.BytesIO(); im.save(buf, "PNG")
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="input_image_0"; '
                      f'filename="ref.png"\r\nContent-Type: image/png\r\n\r\n').encode() + buf.getvalue() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}",
        data=b"".join(parts), method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"Erreur Cloudflare {e.code}: {e.read().decode()[:500]}")
    except urllib.error.URLError as e:
        sys.exit(f"Erreur réseau : {e.reason}")
    except OSError as e:  # connexion coupée ou délai dépassé en cours de réponse
        sys.exit(f"Erreur réseau : {e}. Réessaie dans un instant.")
    img = (data.get("result") or {}).get("image")
    if not img:
        sys.exit("Réponse inattendue: " + json.dumps(data)[:500])
    from PIL import Image
    im = Image.open(io.BytesIO(base64.b64decode(img))).convert("RGB")
    im = whiten(im)
    im.save(out)
    print("OK ->", out, im.size)


def whiten(im, thr=232):
    """Pousse le fond presque blanc vers du blanc pur."""
    from PIL import Image
    mask = Image.eval(im.convert("L"), lambda v: 255 if v > thr else 0)
    im.paste((255, 255, 255), mask=mask)
    return im


# ---------------------------------------------------------------- annotations
def wobbly_arrow(draw, p0, p1, color, width=4, rnd=random):
    (x0, y0), (x1, y1) = p0, p1
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1
    bend = rnd.uniform(-0.18, 0.18) * L
    cx, cy = mx - dy / L * bend, my + dx / L * bend
    pts = []
    for i in range(41):
        t = i / 40
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1 + rnd.uniform(-0.8, 0.8)
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1 + rnd.uniform(-0.8, 0.8)
        pts.append((x, y))
    draw.line(pts, fill=color, width=width, joint="curve")
    ax, ay = pts[-1]; bx, by = pts[-5]
    ang = math.atan2(ay - by, ax - bx)
    head = max(14, width * 4)
    for s in (-1, 1):
        a = ang + math.pi + s * rnd.uniform(0.40, 0.55)
        draw.line([(ax, ay), (ax + head * math.cos(a), ay + head * math.sin(a))], fill=color, width=width)


def annotate(src, spec_file, out):
    from PIL import Image, ImageDraw, ImageFont
    if not FONT.exists():
        sys.exit(f"Police introuvable : {FONT}")
    im = Image.open(src).convert("RGBA")
    W, H = im.size
    with open(spec_file, encoding="utf-8-sig") as fh:
        labels = json.load(fh)
    rnd = random.Random(7)
    arrows = ImageDraw.Draw(im)
    for lab in labels:
        col = COLORS.get(lab.get("color", "red"), COLORS["red"])
        size = int(lab.get("size", 46) * W / 1344)
        font = ImageFont.truetype(str(FONT), size)
        x, y = lab["x"] * W, lab["y"] * H
        if lab.get("arrow_to"):
            tx, ty = lab["arrow_to"][0] * W, lab["arrow_to"][1] * H
            ang = math.atan2(ty - y, tx - x)
            off = size * 0.9
            wobbly_arrow(arrows, (x + off * math.cos(ang) * 1.6, y + off * math.sin(ang)), (tx, ty),
                         col, width=max(3, size // 12), rnd=rnd)
        text = lab["text"]
        bbox = font.getbbox(text)
        tw, th = bbox[2] - bbox[0] + 20, bbox[3] - bbox[1] + 30
        layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((10 - bbox[0], 12 - bbox[1]), text, font=font, fill=col + (255,))
        layer = layer.rotate(lab.get("rotate", rnd.uniform(-4, 4)), expand=True, resample=Image.BICUBIC)
        im.alpha_composite(layer, (int(x - layer.width / 2), int(y - layer.height / 2)))
    im.convert("RGB").save(out)
    print("OK ->", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen")
    g.add_argument("--prompt", required=True); g.add_argument("--out", required=True)
    g.add_argument("--config", help="fichier de réglages (<dossier du skill>/config.json)")
    g.add_argument("--width", type=int, default=1344); g.add_argument("--height", type=int, default=768)
    g.add_argument("--seed", type=int); g.add_argument("--ref")
    a = sub.add_parser("annotate")
    a.add_argument("src"); a.add_argument("spec"); a.add_argument("out")
    args = ap.parse_args()
    if args.cmd == "gen":
        gen(args.prompt, args.out, args.width, args.height, args.seed, args.ref, args.config)
    else:
        annotate(args.src, args.spec, args.out)
