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
- Car screens through [Sailplay](https://github.com/0312birdzhang/harbour-sailplay): the app is listed
  as an SDK player, and the Browse button of the Music card lists the books on
  the phone and starts the chosen one. The progress bar follows the current
  chapter.
- Audible store in the built-in browser or in the system browser.
- Interface in English, French, German, Spanish, Italian, Dutch, Swedish,
  Finnish, Polish and Russian.

## Installation

Download the RPM from the releases page and install it:

```bash
devel-su pkcon install-local harbour-audiobook-0.8.4-1.aarch64.rpm
```

The Python modules the app needs (audible, snowcrypt and their dependencies)
are bundled in the package, so nothing else has to be installed. The package
targets 64-bit devices (aarch64) running Sailfish OS 5 with Python 3.11.

Sailjail sandboxing is disabled for now.

## Building

The app itself is QML and Python, so it builds without the Sailfish SDK, on
any machine with `rpmbuild`, `pip` and Qt's `lrelease`:

```bash
sh tools/vendor.sh               # fetches the bundled Python modules into lib/
python3 tools/build_ts.py        # regenerates the translation files
rpmbuild --target aarch64 -bb harbour-audiobook.spec
```

Pillow, used by the audible module only to display a CAPTCHA during password
sign-in, is replaced by an empty stub: the app signs in through the browser.

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

Le paquet RPM embarque tous les modules Python nécessaires : il s'installe
seul, sans étape préalable.

L'application n'est pas officielle et n'a aucun lien avec Audible ni Amazon.
Elle n'accède qu'aux livres achetés sur votre propre compte.
