#!/bin/bash

# 20251027 vgp - Script para publicar el proyecto en github con modificaciones.

# Creamos una carpeta temporal para copiar el repositorio
# y despues hacer el commit y push desde ahi.
# la variable DRY=1 realiza la copia sin hacer el push al repositorio remoto.
DRY=0
TEMP_DIR=$(mktemp -d)
REPO_URL="git@github.com:vicgarpe/image_searcher.git"
REPO_DIR="$TEMP_DIR/image_searcher"

# Copiamos toda la carpeta actual excluyendo los archivos que
# indicamos en la variable EXCLUDE_FILES.
EXCLUDE_FILES="publicar.sh altas_en_api.org descargas SECRETOS"
rsync -av --exclude=$(echo $EXCLUDE_FILES | tr ' ' '\n' | sed 's/^/--exclude=/') ./ "$REPO_DIR/"

# Cambiamos al directorio del repositorio temporal y hacemos el commit y push.
cd "$REPO_DIR" || { echo "No se pudo cambiar al directorio del repositorio"; exit 1; }
git init
git remote add origin "$REPO_URL"
git checkout -b main

# Creamos el archivo SECRETOS con las variables de entorno necesarias. 
# Pero en blanco para no subir datos sensibles al repositorio.
cat <<EOL > SECRETOS
UNSPLASH_KEY=
PEXELS_KEY=
WIKEMEDIA_KEY=
PIXABAY_API_KEY=
OPENVERSE_CLIENT_SECRET=
EOL

# Creamos el .gitignore para ignorar la carpeta .venv y descargas 
# y todas las típicas de archivos temporales y relacionados con vcode.
cat <<EOL > .gitignore
.venv/
descargas/
__pycache__/
*.pyc
.vscode/
EOL

echo "Carpeta de proyecto copiada a $REPO_DIR"
echo "------------------------------------------------------"

# Hacemos el commit y push de los cambios al repositorio remoto.
if [ "$DRY" -eq 0 ]; then
    echo "Sin modo DRY pasamos a realizar el push."
    git add .
    git commit -m "Actualización del proyecto"
    git push -u origin main --force

    exit 0
else
    echo "Modo DRY activo. No se realizará el push al repositorio remoto."
    exit 0
fi

# Limpiamos el directorio temporal
if [ "$DRY" -eq 0 ]; then
    echo "Limpieza del directorio temporal."
    rm -rf "$TEMP_DIR"
fi


