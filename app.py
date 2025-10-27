# -*- coding: utf-8 -*-
import argparse
import json
from modulos.bancos_imagenes import cargar_config, crear_banco_desde_config

def main():
    parser = argparse.ArgumentParser(description="Demo bancos de imagenes (real o dry segun JSON o CLI).")
    parser.add_argument("--json", default="bancos_imagenes.json", help="Ruta del JSON de configuracion.")
    parser.add_argument("--servicio", required=True, help="pexels|pixabay|unsplash|openverse|wikimedia")
    parser.add_argument("--query", default="gato")
    parser.add_argument("--per-page", type=int, default=5)
    parser.add_argument("--dry-run", dest="dry_run", choices=["auto","true","false"], default="auto",
                        help="auto=usar JSON; true/false anula el valor del JSON")
    args = parser.parse_args()

    config = cargar_config(args.json)
    banco = crear_banco_desde_config(config, args.servicio)

    dry_override = None
    if args.dry_run == "true":
        dry_override = True
    elif args.dry_run == "false":
        dry_override = False

    result = banco.search(args.query, per_page=args.per_page, dry_run=dry_override)

    if result.get("dry"):
        print(f"[{result['service']}] (dry=True)")
        print("URL    :", result["url"])
        print("Headers:", json.dumps(result["headers"], ensure_ascii=False))
        print("Params :", json.dumps(result["params"], ensure_ascii=False))
    else:
        items = result.get("results", [])
        print(f"[{result['service']}] (dry=False) -> {len(items)} resultados")
        descargadas = [it.get("saved_path") for it in items if it.get("saved_path")]
        print(f"Imagenes descargadas: {len(descargadas)}")
        for it in items:
            sp = it.get("saved_path")
            if sp:
                print(f"- {sp}")

if __name__ == "__main__":
    main()
