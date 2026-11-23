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
# Sur x86, src/cpuid.c lit le registre XCR0 avec la fonction _xgetbv(), qui
# n'existe qu'a partir de GCC 9 ; Debian 10 fournit GCC 8, et le module
# _cpuid_c ne se chargerait pas (symbole _xgetbv introuvable). On la remplace
# par l'instruction xgetbv en assembleur, de meme effet. Elle reste protegee
# par le test OSXSAVE qui la precede. Sans effet sur ARM.
case "$ARCH" in
  armv7hl) PLATFORM=linux/arm/v7 ;;
  i486)    PLATFORM=linux/386 ;;
  *) echo "architecture inconnue : $ARCH" >&2; exit 1 ;;
esac
mkdir -p "$OUT"
docker run --rm --platform "$PLATFORM" -v "$(cd "$OUT" && pwd):/out" python:3.11-buster sh -ec '
  cd /tmp
  pip download -q --no-deps --no-binary=:all: pycryptodome==4.4.0 -d src
  tar xzf src/pycryptodome-4.4.0.tar.gz
  sed -i "s|return (uint64_t)_xgetbv(0);|uint32_t lo, hi; __asm__ volatile (\"xgetbv\" : \"=a\" (lo), \"=d\" (hi) : \"c\" (0)); return ((uint64_t)hi << 32) \| lo;|" pycryptodome-4.4.0/src/cpuid.c
  grep -n "xgetbv" pycryptodome-4.4.0/src/cpuid.c
  pip wheel -q --no-deps ./pycryptodome-4.4.0 -w /out
  mkdir t && cd t && python3 -m zipfile -e /out/pycryptodome-*.whl .
  python3 -c "from Crypto.Cipher import AES; print(\"AES ok\", AES.new(bytes(16), AES.MODE_CBC, bytes(16)).encrypt(bytes(16)).hex())"
' >&2
ls "$OUT"/pycryptodome-*.whl
