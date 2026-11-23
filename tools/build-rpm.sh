#!/bin/sh
# Construit le paquet RPM pour une architecture, a partir de lib/ deja prepare
# par tools/vendor.sh. Fonctionne hors du SDK Sailfish (rpmbuild et lrelease).
#
#   sh tools/build-rpm.sh aarch64|armv7hl|i486 [DOSSIER_DE_SORTIE]
set -e
ARCH="$1"; OUT="${2:-.}"
cd "$(dirname "$0")/.."
NAME=harbour-audiobook
VERSION=$(sed -n 's/^Version: *//p' $NAME.spec)
TOP=$(mktemp -d)
mkdir -p "$TOP/SOURCES" "$TOP/src/$NAME-$VERSION"
python3 tools/build_ts.py >/dev/null
cp -r qml python lib icons translations dbus $NAME.desktop "$TOP/src/$NAME-$VERSION/"
find "$TOP/src" -name __pycache__ -prune -exec rm -rf {} +
rm -f "$TOP/src/$NAME-$VERSION"/translations/*.qm
tar czf "$TOP/SOURCES/$NAME-$VERSION.tar.gz" -C "$TOP/src" "$NAME-$VERSION"
PATH="/usr/lib/qt5/bin:$PATH" rpmbuild --nodeps --target "$ARCH" --define "_topdir $TOP" \
  --define "_binary_payload w9.gzdio" -bb $NAME.spec >"$TOP/build.log" 2>&1 \
  || { cat "$TOP/build.log" >&2; exit 1; }
mkdir -p "$OUT"
cp "$TOP"/RPMS/*/$NAME-$VERSION-*.rpm "$OUT"/
ls "$OUT"/$NAME-$VERSION-*."$ARCH".rpm
rm -rf "$TOP"
