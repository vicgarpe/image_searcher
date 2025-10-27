# -*- coding: utf-8 -*-
import streamlit as st
from pathlib import Path
from modulos.bancos_imagenes import cargar_config, crear_banco_desde_config
from modulos.galeria import generate_gallery

st.set_page_config(page_title="Buscador de Imagenes", layout="wide")
st.title("Buscador de imagenes — Frontend (usa tu modulo como backend)")

cfg_path = st.text_input("Ruta del JSON de configuracion", "bancos_imagenes.json")
servicios = ["unsplash", "pexels", "pixabay", "openverse", "wikimedia"]

col1, col2, col3 = st.columns([2,1,1])
with col1:
    servicio = st.selectbox("Servicio", servicios, index=0)
with col2:
    query = st.text_input("Consulta", "gato")
with col3:
    per_page = st.number_input("Resultados", min_value=1, max_value=30, value=6)

dry_mode = st.radio("Modo", options=["auto (segun JSON)","forzar real","forzar dry"], index=0)

c1, c2 = st.columns([1,1])
with c1:
    run = st.button("Buscar")
with c2:
    make_gallery = st.button("Generar galeria HTML")

if run:
    try:
        config = cargar_config(cfg_path)
        banco = crear_banco_desde_config(config, servicio)
        dry_override = None
        if dry_mode == "forzar real":
            dry_override = False
        elif dry_mode == "forzar dry":
            dry_override = True
        with st.spinner("Buscando..."):
            result = banco.search(query, per_page=int(per_page), dry_run=dry_override)
        if result.get("dry"):
            st.subheader("Vista dry (no llama a internet)")
            st.json({
                "url": result["url"],
                "headers": result["headers"],
                "params": result["params"]
            })
        else:
            items = result.get("results", [])
            st.subheader(f"Resultados: {len(items)} (mostrando miniaturas guardadas)")
            cols = st.columns(3)
            for i, it in enumerate(items):
                with cols[i % 3]:
                    sp = it.get("saved_path")
                    if sp and Path(sp).exists():
                        st.image(sp, use_container_width=True)
                    st.caption(f"autor: {it.get('author') or '—'}")
                    if it.get("page_url"):
                        st.write(f"[Ver pagina]({it['page_url']})")
                    if it.get("license"):
                        st.code(it["license"])
    except Exception as e:
        st.error(str(e))

if make_gallery:
    try:
        out = generate_gallery(descargas_dir="descargas", output_html="galeria.html", service=None, embed_data_uris=True)
        st.success(f"Galeria generada: {out}")
        html = Path(out).read_text(encoding="utf-8")
        st.components.v1.html(html, height=700, scrolling=True)
        st.caption("Tambien puedes abrir el archivo galeria.html directamente en tu navegador.")
    except Exception as e:
        st.error(f"No se pudo generar la galeria: {e}")
