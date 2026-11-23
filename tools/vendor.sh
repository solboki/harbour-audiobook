#!/bin/sh
# Telecharge les modules Python embarques dans le paquet (dossier lib/),
# dans les versions testees, pour Python 3.11.
#
#   sh tools/vendor.sh [aarch64|armv7hl|i486]
#
# Seul PyCryptodome contient du code compile. Pour aarch64, la version
# officielle est telechargee. Pour armv7hl et i486, il n'en existe pas : il
# faut fournir dans CRYPTO_WHEEL le chemin d'un paquet compile par
# tools/build-crypto.sh.
set -e
ARCH="${1:-aarch64}"
cd "$(dirname "$0")/.."
rm -rf lib build-vendor && mkdir -p lib build-vendor/whl build-vendor/src
pip download -q --no-deps -d build-vendor/whl \
  anyio==4.16.0 audible==0.13.1 beautifulsoup4==4.15.0 certifi==2026.10.23 \
  h11==0.16.0 httpcore==1.0.9 httpx==0.28.1 idna==3.20 pyasn1==0.6.5 rsa==4.9.1 \
  snowcrypt==0.2.1.post0 soupsieve==4.1.1 typing_extensions==4.16.0
if [ "$ARCH" = aarch64 ]; then
  pip download -q --no-deps --only-binary=:all: --platform manylinux2014_aarch64 \
    --python-version 3.11 --implementation cp --abi abi3 -d build-vendor/whl pycryptodome==4.4.0
elif [ -n "$CRYPTO_WHEEL" ] && [ -f "$CRYPTO_WHEEL" ]; then
  cp "$CRYPTO_WHEEL" build-vendor/whl/
else
  echo "CRYPTO_WHEEL manquant pour $ARCH (voir tools/build-crypto.sh)" >&2
  exit 1
fi
pip download -q --no-deps --no-binary=:all: -d build-vendor/src pbkdf2==1.3 pyaes==1.6.1
for w in build-vendor/whl/*.whl; do python3 -m zipfile -e "$w" lib/; done
for t in build-vendor/src/*.tar.gz; do tar xzf "$t" -C build-vendor/src; done
cp build-vendor/src/pbkdf2-1.3/pbkdf2.py lib/
cp -r build-vendor/src/pyaes-1.6.1/pyaes lib/
cp build-vendor/src/pyaes-1.6.1/LICENSE.txt lib/pyaes-LICENSE.txt 2>/dev/null || true
# Pillow ne sert qu'a afficher un CAPTCHA lors d'une connexion par mot de passe,
# que l'application n'utilise pas : un module vide le remplace.
mkdir -p lib/PIL
printf '"""Remplacant minimal de Pillow (non utilise par harbour-audiobook)."""\n' > lib/PIL/__init__.py
cat > lib/PIL/Image.py <<'PY'
"""Remplacant minimal de Pillow : seul l'affichage d'un CAPTCHA l'utiliserait."""


def open(*args, **kwargs):
    raise RuntimeError("Pillow n'est pas embarque dans harbour-audiobook.")
PY
find lib -name '__pycache__' -prune -exec rm -rf {} +
rm -rf build-vendor
echo "lib/ pret pour $ARCH : $(du -sh lib | cut -f1)"
