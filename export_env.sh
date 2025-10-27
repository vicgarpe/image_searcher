#!/bin/bash

## Comprobamos el tipo de ecución
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    echo "Estableciendo variables para el shell actual."
else
    echo "ERROR: Este script debe ser ejecutado con 'source' para funcionar correctamente."
    echo "Usa: source $0"
    exit 1
fi

set -a
source SECRETOS
set +a

echo "Environment exported to app."
