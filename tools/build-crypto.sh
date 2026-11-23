#!/bin/sh
# Compile PyCryptodome pour une architecture 32 bits, dans un conteneur Debian
# 10 « buster » (glibc 2.28, plus ancienne que celle de Sailfish OS, donc
# compatible) avec Python 3.11, emule par QEMU si besoin.
#
#   sh tools/build-crypto.sh armv7hl|i486 DOSSIER_DE_SORTIE
#
# Affiche le chemin du paquet .whl produit.
set -e
ARCH="$1"; OUT="${2:-build-crypto}"
# En 32 bits Intel, l'instruction xgetbv (detection d'AES-NI) n'est compilee
# en ligne qu'avec -mxsave ; sans elle, le module _cpuid_c ne se charge pas.
# PyCryptodome verifie le support par le processeur avant de l'utiliser.
CFLAGS_EXTRA=""
case "$ARCH" in
  armv7hl) PLATFORM=linux/arm/v7 ;;
  i486)    PLATFORM=linux/386; CFLAGS_EXTRA="-mxsave" ;;
  *) echo "architecture inconnue : $ARCH" >&2; exit 1 ;;
esac
mkdir -p "$OUT"
docker run --rm --platform "$PLATFORM" -e CFLAGS="$CFLAGS_EXTRA" -v "$(cd "$OUT" && pwd):/out" python:3.11-buster \
  sh -c 'pip wheel -q --no-deps --no-binary=:all: pycryptodome==4.4.0 -w /out && \
         mkdir /tmp/t && cd /tmp/t && python3 -m zipfile -e /out/pycryptodome-*.whl . && \
         python3 -c "from Crypto.Cipher import AES; print(\"AES ok\", AES.new(bytes(16), AES.MODE_CBC, bytes(16)).encrypt(bytes(16)).hex())"' >&2
ls "$OUT"/pycryptodome-*.whl
