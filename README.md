# Audiobook

**A native client for Audible on Sailfish OS.**
*Client natif pour Audible sur Sailfish OS. [Version française plus bas.](#français)*

Audiobook lets you browse your Audible library, download your audiobooks and
listen to them in a native Silica player, with your listening position kept in
sync with the official Audible apps on your other devices.

> Unofficial app, not affiliated with Audible or Amazon. Audible is a trademark
> of Audible, Inc. The app only accesses books purchased on your own account.

## Features

- Sign-in with your Amazon or Audible account inside the app (the phone is
  registered as a listening device, like the official app). A fallback lets you
  sign in with any other browser.
- Library with covers, search (title, author, series), books on the phone first,
  or sorting by author.
- Background download and decryption to standard M4B files, stored in
  `~/Music/Audible`.
- Player attached to the library (swipe left, or tap the indicator at the top
  right): chapters, skip back and forward, speed from 0.8× to 2×, sleep timer
  (minutes or end of chapter), active cover, headphone buttons (MPRIS).
- Listening position sync with Audible: sent on pause, every minute and on exit;
  a more recent position from another device is offered when opening a book.
- Audible store in the built-in browser or in the system browser.
- Interface in English, French, German, Spanish, Italian, Dutch, Swedish,
  Finnish, Polish and Russian.

## Installation

The app relies on two Python modules that are not packaged for Sailfish OS.
Install them once, as the `defaultuser` user:

```bash
python3 -m pip install --user audible snowcrypt
```

Then install the RPM from the releases page:

```bash
devel-su pkcon install-local harbour-audiobook-0.6.0-1.noarch.rpm
```

Sailjail sandboxing is disabled for now, so that the app can load the modules
installed with pip.

## Building

The package is `noarch` (QML and Python only), so it builds without the
Sailfish SDK, on any machine with `rpmbuild` and Qt's `lrelease`:

```bash
python3 tools/build_ts.py        # regenerates the translation files
rpmbuild -bb harbour-audiobook.spec
```

Translations live in `tools/catalog.py`, one line per text and one column per
language. Corrections from native speakers are welcome.

## Credits

- [audible](https://github.com/mkb79/Audible) and
  [audible-cli](https://github.com/mkb79/audible-cli) by mkb79 (AGPL-3.0):
  access to the Audible API, reference for license requests.
- [snowcrypt](https://github.com/snowskeleton/snowcrypt) by snowskeleton
  (Apache 2.0): decryption of AAX and AAXC files.
- [PyOtherSide](https://github.com/thp/pyotherside) by Thomas Perl (ISC).
- [HTTPX](https://github.com/encode/httpx) (BSD-3-Clause) and
  [PyCryptodome](https://www.pycryptodome.org) (BSD-2-Clause).
- Qt, Sailfish Silica, Sailfish WebView and Amber MPRIS.

Designed by Boris Solodki and developed with the assistance of Claude
(Anthropic).

## License

GNU Affero General Public License v3.0 or later, see [LICENSE](LICENSE).

---

## Français

Audiobook est un client natif pour Audible sur Sailfish OS. Il affiche votre
bibliothèque, télécharge vos livres audio et les lit dans un lecteur Silica, en
synchronisant la position d'écoute avec les applications officielles d'Audible
sur vos autres appareils.

Avant d'installer le paquet RPM, installez une fois les deux modules Python
nécessaires avec `python3 -m pip install --user audible snowcrypt`.

L'application n'est pas officielle et n'a aucun lien avec Audible ni Amazon.
Elle n'accède qu'aux livres achetés sur votre propre compte.
