#!/bin/bash
set -euo pipefail
DIR="$(dirname "$(dirname "$0")")/images"
URL="https://dl-cdn.alpinelinux.org/alpine/v3.21/releases/x86_64/alpine-virt-3.21.3-x86_64.iso"
mkdir -p "$DIR"
echo "Descargando $URL ..."
curl -Lo "$DIR/alpine-virt-3.21.3-x86_64.iso" "$URL"
echo "OK: $DIR/alpine-virt-3.21.3-x86_64.iso"
ls -lh "$DIR/alpine-virt-3.21.3-x86_64.iso"
