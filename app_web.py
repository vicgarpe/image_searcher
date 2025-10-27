# -*- coding: utf-8 -*-
# app_web.py — Frontend Flask con Bootstrap (dark) y mosaico responsive
# pip install flask

from flask import Flask, request, render_template_string, send_from_directory, Response, url_for
from pathlib import Path
from modulos.bancos_imagenes import cargar_config, crear_banco_desde_config
from modulos.galeria import generate_gallery
import json as _json

app = Flask(__name__)

# Layout base con un "hueco" para el contenido
BOOTSTRAP = """
<!doctype html>
<html lang="es" data-bs-theme="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title or "Buscador de imágenes" }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
      body { background-color: #0b0c10; }
      .navbar-brand { font-weight: 700; letter-spacing: .2px; }
      .masonry { column-count: 1; column-gap: 1rem; }
      @media (min-width: 576px) { .masonry { column-count: 2; } }
      @media (min-width: 992px) { .masonry { column-count: 3; } }
      @media (min-width: 1400px){ .masonry { column-count: 4; } }
      .masonry .card { break-inside: avoid; margin-bottom: 1rem; border-radius: 0.75rem; overflow: hidden; }
      .img-thumb { width: 100%; height: auto; display: block; }
      .badge { font-weight: 500; }
      .footer { color: #9aa0a6; }
      .form-select, .form-control { background-color: #111318; border-color: #2a2f3a; }
      .btn-primary { background: #4c6ef5; border: 0; }
      .btn-outline-light { border-color: #3c4048; }
      .card { background-color: #111318; border-color: #1c2027; box-shadow: 0 2px 12px rgba(0,0,0,.35); }
      .card a { text-decoration: none; }
      code { background: #0e1117; }
    </style>
  </head>
  <body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark border-bottom border-secondary">
      <div class="container">
        <a class="navbar-brand" href="{{ url_for('home') }}">Galería Libre</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div id="nav" class="collapse navbar-collapse">
          <ul class="navbar-nav me-auto mb-2 mb-lg-0">
            <li class="nav-item"><a class="nav-link {% if active=='buscar' %}active{% endif %}" href="{{ url_for('home') }}">Buscar</a></li>
            <li class="nav-item"><a class="nav-link {% if active=='galeria' %}active{% endif %}" href="{{ url_for('galeria') }}">Galería</a></li>
          </ul>
          <span class="navbar-text small">Frontend Flask · Backend Python</span>
        </div>
      </div>
    </nav>

    <main class="container py-4">
      {{ content|safe }}
    </main>

    <footer class="container pb-4 footer small">
      <hr class="border-secondary">
      <div class="d-flex justify-content-between">
        <div>Licencias y atribuciones según el proveedor (Unsplash/CC/Wikimedia…).</div>
        <div>Hecho con Flask + Bootstrap 5</div>
      </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  </body>
</html>
"""

# Contenido de la home (sin bloques ni extends)
INDEX = """
<form class="row gy-2 gx-2 align-items-end" method="get">
  <div class="col-12 col-md-3">
    <label class="form-label">Servicio</label>
    <select class="form-select" name="serv">
      {% for s in servicios %}
        <option value="{{s}}" {% if s==serv %}selected{% endif %}>{{s}}</option>
      {% endfor %}
    </select>
  </div>
  <div class="col-12 col-md-4">
    <label class="form-label">Consulta</label>
    <input class="form-control" type="text" name="q" value="{{q}}">
  </div>
  <div class="col-6 col-md-2">
    <label class="form-label">Resultados</label>
    <input class="form-control" type="number" name="n" min="1" max="50" value="{{n}}">
  </div>
  <div class="col-6 col-md-2">
    <label class="form-label">Modo</label>
    <select class="form-select" name="mode">
      <option value="auto" {% if mode=='auto' %}selected{% endif %}>auto (JSON)</option>
      <option value="real" {% if mode=='real' %}selected{% endif %}>real</option>
      <option value="dry"  {% if mode=='dry'  %}selected{% endif %}>dry</option>
    </select>
  </div>
  <div class="col-12 col-md-1">
    <button class="btn btn-primary w-100" type="submit">Buscar</button>
  </div>
</form>

{% if error %}
  <div class="alert alert-danger mt-3">{{ error }}</div>
{% endif %}

{% if dry %}
  <div class="alert alert-info mt-4">
    <div class="d-flex justify-content-between align-items-center">
      <strong>Vista "dry": no se llama a internet</strong>
      <a class="btn btn-sm btn-outline-light" href="{{ url_for('galeria') }}">Ver Galería</a>
    </div>
    <pre class="mt-3 mb-0"><code>{{ dry_json }}</code></pre>
  </div>
{% else %}
  {% if items %}
    <div class="d-flex justify-content-between align-items-center mt-4 mb-2">
      <h2 class="h5 mb-0">Resultados: {{ items|length }}</h2>
      <div class="d-flex gap-2">
        <a class="btn btn-outline-light btn-sm" href="{{ url_for('galeria', service=serv) }}">Galería ({{serv}})</a>
        <a class="btn btn-outline_light btn-sm" href="{{ url_for('galeria') }}">Galería (todo)</a>
      </div>
    </div>

    <div class="masonry">
      {% for it in items %}
        <div class="card">
          {% if it.saved_path %}
            <a href="{{ it.page_url or '#' }}" target="_blank" rel="noopener">
              <img class="img-thumb" src="{{ url_for('media', filename=it.saved_path) }}" loading="lazy" alt="">
            </a>
          {% endif %}
          <div class="card-body">
            <div class="d-flex flex-wrap gap-2 align-items-center">
              <span class="badge text-bg-secondary">{{ serv }}</span>
              {% if it.author %}<span class="badge text-bg-dark">autor: {{ it.author }}</span>{% endif %}
              {% if it.license %}<span class="badge text-bg-info">lic: {{ it.license }}</span>{% endif %}
              {% if it.page_url %}<a class="btn btn-sm btn-outline-light ms-auto" href="{{ it.page_url }}" target="_blank">Ver página</a>{% endif %}
            </div>
          </div>
        </div>
      {% endfor %}
    </div>
  {% else %}
    <div class="alert alert-warning mt-4">No hay resultados todavía. Prueba una búsqueda.</div>
  {% endif %}
{% endif %}
"""

# Contenido de la página de galería (sin bloques ni extends)
GALERIA = """
<div class="d-flex justify-content-between align-items-center mb-3">
  <h1 class="h4 mb-0">Galería HTML ({{ 'todas las fuentes' if not service else service }})</h1>
  <div class="d-flex gap-2">
    <a class="btn btn-outline-light btn-sm" href="{{ url_for('home') }}">Volver a buscar</a>
    <a class="btn btn-primary btn-sm" href="{{ url_for('galeria', service=service) }}">Regenerar</a>
  </div>
</div>
<iframe src="{{ url_for('galeria_raw', service=service) }}" style="width:100%; height:75vh; border:1px solid #222; border-radius: .5rem;"></iframe>
<p class="text-secondary small mt-3">El HTML se genera desde <code>descargas/</code>. Abre la galería en nueva pestaña si lo prefieres:
  <a class="link-light" href="{{ url_for('galeria_raw', service=service) }}" target="_blank" rel="noopener">abrir</a>.
</p>
"""

def render_page(content_tpl: str, **context):
    # renderiza el contenido con su propio contexto, y lo inyecta en el layout BOOTSTRAP
    content_html = render_template_string(content_tpl, **context)
    return render_template_string(BOOTSTRAP, content=content_html, **context)

@app.route("/")
def home():
    servicios = ["unsplash", "pexels", "pixabay", "openverse", "wikimedia"]
    serv = request.args.get("serv", "unsplash")
    q = request.args.get("q", "gato")
    try:
        n = int(request.args.get("n", 12))
    except Exception:
        n = 12
    mode = request.args.get("mode", "auto")

    cfg = cargar_config("bancos_imagenes.json")
    banco = crear_banco_desde_config(cfg, serv)

    dry_override = None
    if mode == "real":
        dry_override = False
    elif mode == "dry":
        dry_override = True

    try:
        res = banco.search(q, per_page=n, dry_run=dry_override)
    except Exception as e:
        return render_page(INDEX, servicios=servicios, serv=serv, q=q, n=n, mode=mode,
                           dry=False, items=[], error=str(e), active="buscar", title="Buscador de imágenes")

    if res.get("dry"):
        return render_page(INDEX, servicios=servicios, serv=serv, q=q, n=n, mode=mode,
                           dry=True, dry_json=_json.dumps(res, indent=2, ensure_ascii=False),
                           error=None, active="buscar", title="Buscador de imágenes")
    else:
        return render_page(INDEX, servicios=servicios, serv=serv, q=q, n=n, mode=mode,
                           dry=False, items=res.get("results", []), error=None, active="buscar",
                           title="Buscador de imágenes")

# Sirve ficheros de la carpeta descargas
@app.route("/media/<path:filename>")
def media(filename):
    p = Path(filename)
    if p.is_absolute():
        try:
            rel = p.resolve().relative_to(Path.cwd().resolve())
        except Exception:
            return Response("Not allowed", status=403)
        p = rel
    if p.parts and p.parts[0] == "descargas":
        return send_from_directory(str(Path.cwd()), str(p).replace("\\", "/"), as_attachment=False)
    else:
        return send_from_directory(str(Path("descargas").resolve()), str(p), as_attachment=False)

# HTML de galería "raw"
@app.route("/descargas/<path:filename>")
def descargas(filename):
    # Serve files directly under ./descargas for gallery relative links
    return send_from_directory(str(Path("descargas").resolve()), filename, as_attachment=False)

@app.route("/galeria_raw")
def galeria_raw():
    service = request.args.get("service")
    out = generate_gallery(descargas_dir="descargas", output_html="galeria.html",
                           service=service, title="Galería")
    html = Path(out).read_text(encoding="utf-8")
    return Response(html, mimetype="text/html")

# Página con iframe de la galería
@app.route("/galeria")
def galeria():
    service = request.args.get("service")
    return render_page(GALERIA, service=service, active="galeria", title="Galería")

if __name__ == "__main__":
    app.run(debug=True)
