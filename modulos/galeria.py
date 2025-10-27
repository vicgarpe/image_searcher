# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Iterable, Optional
import os, base64, mimetypes

IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

HTML_TEMPLATE_DARK = """<!doctype html>
<html lang="es" data-bs-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  body {{ background-color: #0b0c10; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; padding: 1rem;}}
  h1 {{ font-size: 1.2rem; margin: 0 0 1rem 0; }}
  .grid {{ column-count: 1; column-gap: 12px; }}
  @media (min-width: 576px) {{ .grid {{ column-count: 2; }} }}
  @media (min-width: 992px) {{ .grid {{ column-count: 3; }} }}
  @media (min-width: 1400px){{ .grid {{ column-count: 4; }} }}
  .card {{ break-inside: avoid; margin-bottom: 12px; border: 1px solid #1c2027; border-radius: 12px; overflow: hidden; background: #111318; box-shadow: 0 2px 12px rgba(0,0,0,.35); }}
  .card img {{ width: 100%; height: auto; display: block; background:#111; }}
  .meta {{ padding: .5rem .75rem; font-size: .85rem; color: #cbd5e1; background: #0f1217; }}
  .muted {{ color: #94a3b8; font-size: .8rem; }}
  .service {{ font-weight: 600; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="grid">
{cards}
</div>
</body>
</html>"""

HTML_TEMPLATE_LIGHT = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; padding: 1rem;}}
  h1 {{ font-size: 1.4rem; margin: 0 0 1rem 0; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }}
  .card {{ border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,.05); }}
  .card img {{ width: 100%; height: 180px; object-fit: cover; display: block; }}
  .meta {{ padding: .5rem .75rem; font-size: .85rem; color: #374151; background: #fafafa; }}
  .muted {{ color: #6b7280; font-size: .8rem; }}
  .service {{ font-weight: 600; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="grid">
{cards}
</div>
</body>
</html>"""

CARD = """<div class="card">
  <img src="{src}" alt="">
  <div class="meta">
    <div class="service">{service}</div>
    <div class="muted">{relpath}</div>
  </div>
</div>"""

def _iter_images(descargas_dir: Path, service: Optional[str]):
    descargas_dir = descargas_dir.resolve()
    if service:
        root = descargas_dir / service
        if root.exists():
            for p in sorted(root.rglob("*")):
                if p.suffix.lower() in IMG_EXTS:
                    yield p
        return
    if descargas_dir.exists():
        for p in sorted(descargas_dir.rglob("*")):
            if p.suffix.lower() in IMG_EXTS:
                yield p

def _to_data_uri(path: Path) -> str:
    try:
        mime, _ = mimetypes.guess_type(path.name)
        if not mime:
            mime = "image/jpeg"
        b = path.read_bytes()
        b64 = base64.b64encode(b).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return ""

def generate_gallery(descargas_dir: str = "descargas", output_html: str = "galeria.html",
                     service: Optional[str] = None, title: Optional[str] = None,
                     embed_data_uris: bool = False, dark: bool = True) -> str:
    desc_dir = Path(descargas_dir).resolve()
    out = Path(output_html).resolve()
    images = list(_iter_images(desc_dir, service))

    if not title:
        title = "Galeria de imagenes" + (f" – {service}" if service else "")

    cards = []
    for img in images:
        ip = img.resolve()
        if embed_data_uris:
            src = _to_data_uri(ip)
        else:
            try:
                src = os.path.relpath(ip, start=out.parent)
            except Exception:
                src = str(ip)

        try:
            rel_to_desc = ip.relative_to(desc_dir)
            service_name = rel_to_desc.parts[0] if len(rel_to_desc.parts) > 0 else "desconocido"
            rel_inside_desc = str(rel_to_desc).replace("\\", "/")
        except Exception:
            service_name = "desconocido"
            rel_inside_desc = ip.name

        cards.append(CARD.format(src=str(src).replace("\\","/"),
                                 service=service_name,
                                 relpath=rel_inside_desc))

    template = HTML_TEMPLATE_DARK if dark else HTML_TEMPLATE_LIGHT
    html = template.format(title=title, cards="\n".join(cards))
    out.write_text(html, encoding="utf-8")
    return str(out)
