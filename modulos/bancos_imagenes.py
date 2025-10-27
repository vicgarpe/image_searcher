# -*- coding: utf-8 -*-
"""
modulos/bancos_imagenes.py

Openverse con OAuth2 client_credentials:
- client_id en JSON (client_id)
- client_secret en variable de entorno cuyo nombre viene en JSON (client_secret_env)
- Token se solicita en __init__ si default_dry=False y se renueva automaticamente.

Otros proveedores mantienen el comportamiento previo.
"""

import os
import json
import pathlib
import hashlib
import time
import requests

DESCARGAS_DIR = pathlib.Path("descargas")
DESCARGAS_DIR.mkdir(exist_ok=True)

def _slug(s, maxlen=60):
    s = "".join(ch if ch.isalnum() else "-" for ch in str(s))
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")[:maxlen] or "img"

def _filename_for_item(item):
    base = item.get("id")
    if not base:
        pu = item.get("preview_url", "")
        base = hashlib.sha1(pu.encode("utf-8")).hexdigest()[:12] if pu else "img"
    return f"{_slug(base)}.jpg"

def _download_image(url, carpeta, nombre):
    carpeta = pathlib.Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / nombre
    if destino.exists():
        return str(destino)
    r = requests.get(url, timeout=20, headers={"User-Agent": "MasterIA3D-Downloader/1.0"})
    r.raise_for_status()
    with open(destino, "wb") as f:
        f.write(r.content)
    return str(destino)

class BancoImagenes:
    def __init__(self, access_key, base_url, default_dry=True):
        self.access_key = access_key or ""
        self.base_url = base_url
        self.default_dry = default_dry

    def build_request(self, query, per_page=5):
        raise NotImplementedError("Implementa esto en la subclase")

    def parse_response(self, payload):
        raise NotImplementedError("Implementa esto en la subclase")

    def servicio_nombre(self):
        return type(self).__name__.replace("API", "").lower()

    def _dedup(self, items):
        seen = set()
        out = []
        for it in items:
            key = (it.get("id"), it.get("preview_url"))
            if key in seen:
                continue
            seen.add(key)
            out.append(it)
        return out

    def search(self, query, per_page=5, dry_run=None):
        if dry_run is None:
            dry_run = self.default_dry
        url, headers, params = self.build_request(query, per_page)
        if dry_run:
            return {"service": type(self).__name__, "url": url, "headers": headers, "params": params, "dry": True}
        r = requests.get(url, headers=headers, params=params, timeout=25)
        r.raise_for_status()
        data = r.json()
        items = self.parse_response(data)
        items = self._dedup(items)
        carpeta = DESCARGAS_DIR / self.servicio_nombre()
        for it in items:
            pu = it.get("preview_url")
            if pu:
                try:
                    nombre = _filename_for_item(it)
                    it["saved_path"] = _download_image(pu, carpeta, nombre)
                except Exception as e:
                    it["saved_path"] = None
                    it["download_error"] = str(e)
        return {"service": type(self).__name__, "results": items, "dry": False}

class PexelsAPI(BancoImagenes):
    def __init__(self, access_key, base_url="https://api.pexels.com/v1", default_dry=True):
        super().__init__(access_key, base_url, default_dry)
    def build_request(self, query, per_page=5):
        url = f"{self.base_url}/search"
        headers = {"Authorization": self.access_key}
        params = {"query": query, "per_page": per_page}
        return url, headers, params
    def parse_response(self, payload):
        out = []
        for p in payload.get("photos", []):
            out.append({
                "id": p.get("id"),
                "preview_url": (p.get("src") or {}).get("medium"),
                "page_url": p.get("url"),
                "author": p.get("photographer"),
                "license": "Pexels License",
            })
        return out

class PixabayAPI(BancoImagenes):
    def __init__(self, access_key, base_url="https://pixabay.com/api/", default_dry=True):
        super().__init__(access_key, base_url, default_dry)
    def build_request(self, query, per_page=5):
        url = self.base_url
        headers = {}
        params = {"key": self.access_key, "q": query, "image_type": "photo", "per_page": per_page}
        return url, headers, params
    def parse_response(self, payload):
        out = []
        for h in payload.get("hits", []):
            out.append({
                "id": h.get("id"),
                "preview_url": h.get("webformatURL") or h.get("previewURL"),
                "page_url": h.get("pageURL"),
                "author": h.get("user"),
                "license": "Pixabay License",
            })
        return out

class UnsplashAPI(BancoImagenes):
    def __init__(self, access_key, base_url="https://api.unsplash.com", default_dry=True):
        super().__init__(access_key, base_url, default_dry)
    def build_request(self, query, per_page=5):
        url = f"{self.base_url}/search/photos"
        headers = {"Authorization": f"Client-ID {self.access_key}"}
        params = {"query": query, "per_page": per_page}
        return url, headers, params
    def parse_response(self, payload):
        out = []
        for it in payload.get("results", []):
            user = it.get("user", {}) or {}
            urls = it.get("urls", {}) or {}
            links = it.get("links", {}) or {}
            out.append({
                "id": it.get("id"),
                "preview_url": urls.get("small") or urls.get("thumb"),
                "page_url": links.get("html"),
                "author": user.get("name"),
                "license": "Unsplash License (atribucion requerida)",
            })
        return out

class OpenverseAPI(BancoImagenes):
    def __init__(self, access_key="", base_url="https://api.openverse.org", default_dry=True,
                 client_id=None, client_secret_env=None, token_url="https://api.openverse.org/v1/auth_tokens/token/"):
        super().__init__(access_key, base_url, default_dry)
        self.client_id = client_id
        self.client_secret_env = client_secret_env
        self.token_url = token_url
        self._token = None
        self._token_expiry = 0
        if not self.default_dry:
            self._ensure_token()
    def _get_client_secret(self):
        if not self.client_secret_env:
            return None
        return os.getenv(self.client_secret_env)
    def _ensure_token(self):
        now = time.time()
        if self._token and now < self._token_expiry - 60:
            return
        if self.access_key:
            self._token = self.access_key
            self._token_expiry = now + 8*3600
            return
        if self.client_id and self._get_client_secret():
            self._request_token()
    def _request_token(self):
        secret = self._get_client_secret()
        if not (self.client_id and secret):
            return
        data = {"grant_type":"client_credentials","client_id":self.client_id,"client_secret":secret}
        r = requests.post(self.token_url, data=data, timeout=20)
        r.raise_for_status()
        payload = r.json()
        self._token = payload.get("access_token")
        exp = int(payload.get("expires_in", 8*3600))
        self._token_expiry = time.time() + max(60, exp)
    def refresh_token(self):
        self._request_token()
    def build_request(self, query, per_page=5):
        self._ensure_token()
        url = f"{self.base_url}/v1/images/"
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        params = {"q": query, "page_size": per_page}
        return url, headers, params
    def parse_response(self, payload):
        out = []
        for r in payload.get("results", []):
            out.append({
                "id": r.get("id"),
                "preview_url": r.get("thumbnail") or r.get("url"),
                "page_url": r.get("foreign_landing_url"),
                "author": r.get("creator"),
                "license": f"{r.get('license')}-{r.get('license_version')}",
            })
        return out

class WikimediaCommonsAPI(BancoImagenes):
    def __init__(self, base_url="https://commons.wikimedia.org/w/api.php", default_dry=True, user_agent=None):
        super().__init__(access_key="", base_url=base_url, default_dry=default_dry)
        self.user_agent = user_agent or "victor (mailto:vicgarpe@uchceu.es)"
    def build_request(self, query, per_page=5):
        url = self.base_url
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": per_page,
            "gsrnamespace": 6,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "format": "json"
        }
        return url, headers, params
    def parse_response(self, payload):
        out = []
        pages = (payload.get("query") or {}).get("pages") or {}
        for _, p in pages.items():
            ii = (p.get("imageinfo") or [{}])[0]
            meta = (ii.get("extmetadata") or {})
            out.append({
                "id": p.get("pageid"),
                "preview_url": ii.get("url"),
                "page_url": f"https://commons.wikimedia.org/wiki/{p.get('title','')}",
                "author": (meta.get("Artist") or {}).get("value"),
                "license": (meta.get("LicenseShortName") or {}).get("value"),
            })
        return out

def cargar_config(origen_json):
    if isinstance(origen_json, dict):
        return origen_json
    with open(origen_json, "r", encoding="utf-8") as f:
        return json.load(f)

def crear_banco_desde_config(config, servicio):
    s = servicio.lower()
    if s not in config:
        raise ValueError(f"Servicio no definido en el JSON: {servicio}")
    entry = config[s]
    base_url = entry.get("base_url", "")
    env_name = entry.get("access_key_env", "")
    default_dry = bool(entry.get("dry", True))
    access_key = os.getenv(env_name, "") if env_name else ""

    if s == "pexels":
        return PexelsAPI(access_key, base_url or "https://api.pexels.com/v1", default_dry)
    if s == "pixabay":
        return PixabayAPI(access_key, base_url or "https://pixabay.com/api/", default_dry)
    if s == "unsplash":
        return UnsplashAPI(access_key, base_url or "https://api.unsplash.com", default_dry)
    if s == "openverse":
        client_id = entry.get("client_id")
        client_secret_env = entry.get("client_secret_env")
        token_url = entry.get("token_url") or "https://api.openverse.org/v1/auth_tokens/token/"
        return OpenverseAPI(access_key, base_url or "https://api.openverse.org", default_dry,
                            client_id=client_id, client_secret_env=client_secret_env, token_url=token_url)
    if s in ("wikimedia", "commons", "wikimedia commons"):
        ua = entry.get("user_agent")
        return WikimediaCommonsAPI(base_url or "https://commons.wikimedia.org/w/api.php", default_dry, user_agent=ua)
    raise ValueError(f"Servicio no soportado: {servicio}")
