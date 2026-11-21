#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Service Sailplay d'Audiobook : bouton « Parcourir » de la carte Musique.

Expose les livres presents sur le telephone a l'ecran de la voiture (contrat
Content1 du SDK Sailplay). Choisir un livre demande a l'application Audiobook
de l'ouvrir et de le lire, en la lancant si besoin. Le service est demarre a
la demande par D-Bus et s'arrete seul apres dix secondes d'inactivite.

Le SDK est fourni par Sailplay (/opt/sailplay, GPL-3.0-or-later) : sans
Sailplay, ce service ne demarre pas et l'application n'en depend pas.
"""
import json
import os
import signal
import sys
from pathlib import Path

sys.path.insert(0, "/opt/sailplay")

import dbus  # noqa: E402
import dbus.mainloop.glib  # noqa: E402
from gi.repository import GLib  # noqa: E402

from sailplay_sdk.content import ContentBackend, wire_content  # noqa: E402
from sailplay_sdk.content_model import content_item, content_page  # noqa: E402
from sailplay_sdk.model import Fault  # noqa: E402

SERVICE = "org.solboki.Audiobook"
APPLICATION_ID = "harbour-audiobook"
APP_SERVICE = "org.solboki.AudiobookApp"   # l'application elle-meme
APP_PATH = "/app"
APP_INTERFACE = "org.solboki.AudiobookApp"

HOME = Path.home()
DATA = HOME / ".local/share/harbour-audiobook"
BOOKS = HOME / "Music/Audible"
IDLE_SECONDS = 10

_FR = os.environ.get("LANG", "").startswith("fr")
TEXT = {
    "empty": "Aucun livre sur le téléphone" if _FR else "No books on the phone",
    "none": "Aucun résultat" if _FR else "No results",
}


def _read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def _people(lst):
    return ", ".join(p.get("name", "") for p in (lst or []) if p.get("name"))


def downloaded_books():
    """Livres presents sur le telephone, du plus recemment ecoute au plus ancien."""
    present = {p.stem for p in BOOKS.glob("*.m4b")} if BOOKS.is_dir() else set()
    library = {it.get("asin"): it for it in _read_json(DATA / "library.json", [])}
    state = _read_json(DATA / "state.json", {})
    books = []
    for asin in present:
        it = library.get(asin, {})
        st = state.get(asin, {})
        runtime_ms = int(it.get("runtime_length_min") or 0) * 60000
        progress = ""
        if st.get("finished"):
            progress = "100 %"
        elif runtime_ms and st.get("position_ms"):
            progress = "%d %%" % min(99, round(100 * st["position_ms"] / runtime_ms))
        authors = _people(it.get("authors"))
        books.append({
            "asin": asin,
            "title": it.get("title") or asin,
            "subtitle": " · ".join(x for x in (authors, progress) if x),
            "search": " ".join((it.get("title") or "", authors)).casefold(),
            "played": float(st.get("updated", 0)),
        })
    books.sort(key=lambda b: (-b["played"], b["title"].casefold()))
    return books


def book_item(book):
    return content_item(book["asin"], book["title"][:1024], book["subtitle"][:1024],
                        kind="action", action="content.select", parameters={"asin": book["asin"]})


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    loop = GLib.MainLoop()
    idle = [0]

    def lifecycle(backend):
        if idle[0]:
            GLib.source_remove(idle[0])
            idle[0] = 0
        if not backend.session_count and not backend.pending_count:
            def quit_if_idle():
                idle[0] = 0
                if not backend.session_count and not backend.pending_count:
                    loop.quit()
                return False
            idle[0] = GLib.timeout_add_seconds(IDLE_SECONDS, quit_if_idle)

    def page(identity, offset, limit, query=""):
        books = downloaded_books()
        if query:
            q = query.casefold()
            books = [b for b in books if q in b["search"]]
        chunk = books[offset:offset + limit]
        empty = TEXT["none"] if query else TEXT["empty"]
        return content_page(identity, "Audiobook" if not query else query,
                            [book_item(b) for b in chunk], search_enabled=True,
                            offset=offset, has_more=offset + limit < len(books),
                            message="" if books else empty,
                            message_kind="none" if books else "info")

    def browse(parameters, invocation):
        if parameters["id"] != "root":
            raise Fault("NotFound", "content folder is unavailable")
        result = page("root", parameters["offset"], parameters["limit"], parameters.get("query", ""))
        invocation.complete({"content": wire_content(result)})

    def select(parameters, invocation):
        asin = str(parameters.get("asin", ""))
        if not asin or not (BOOKS / (asin + ".m4b")).exists():
            raise Fault("NotFound", "book is not on the phone")
        # L'appel lance l'application si elle ne tourne pas (activation D-Bus).
        app = backend.bus.get_object(APP_SERVICE, APP_PATH)
        app.playBook(asin, dbus_interface=APP_INTERFACE, timeout=60,
                     reply_handler=lambda *a: invocation.complete({"asin": asin}),
                     error_handler=lambda e: invocation.fail("Failed", str(e)))

    root = page("root", 0, 50)
    root["offset"] = 0
    backend = ContentBackend(SERVICE, APPLICATION_ID,
                             {"content.browse": browse, "content.search": browse,
                              "content.select": select},
                             {"content": root}, on_lifecycle=lifecycle)
    backend.bus.call_on_disconnection(lambda connection: loop.quit())
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, lambda number, frame: loop.quit())
    lifecycle(backend)
    try:
        loop.run()
    finally:
        if idle[0]:
            GLib.source_remove(idle[0])
        backend.close()


if __name__ == "__main__":
    main()
