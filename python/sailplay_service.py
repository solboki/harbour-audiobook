#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Service Sailplay d'Audiobook : bouton « Parcourir » de la carte Musique.

Expose les livres presents sur le telephone a l'ecran de la voiture (contrat
Content1 du SDK Sailplay). Choisir un livre l'envoie a l'application par la
commande MPRIS OpenUri, en lancant l'application si besoin. Le service est demarre a
la demande par D-Bus et s'arrete seul apres dix secondes d'inactivite.

Le SDK est fourni par Sailplay (/opt/sailplay, GPL-3.0-or-later) : sans
Sailplay, ce service ne demarre pas et l'application n'en depend pas.
"""
import json
import os
import signal
import subprocess
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
# L'application est pilotee par MPRIS (commande standard OpenUri), le canal
# deja utilise par la voiture pour la lecture.
MPRIS_PREFIX = "org.mpris.MediaPlayer2."
DESKTOP_ENTRY = "harbour-audiobook"
MPRIS_PATH = "/org/mpris/MediaPlayer2"
MPRIS_PLAYER = "org.mpris.MediaPlayer2.Player"
# Lancement dans le bac a sable de l'application, comme le fait Sailplay.
LAUNCH = ["/usr/bin/sailjail", "-p", "harbour-audiobook.desktop", "--",
          "/usr/bin/sailfish-qml", "harbour-audiobook"]
LAUNCH_TIMEOUT = 40

HOME = Path.home()
DATA = HOME / ".local/share/org.solboki/harbour-audiobook"
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

    def find_player():
        """Nom du lecteur MPRIS d'Audiobook, reconnu a son DesktopEntry."""
        for name in backend.bus.list_names():
            name = str(name)
            if not name.startswith(MPRIS_PREFIX):
                continue
            try:
                obj = backend.bus.get_object(name, MPRIS_PATH, introspect=False)
                entry = obj.Get("org.mpris.MediaPlayer2", "DesktopEntry",
                                dbus_interface="org.freedesktop.DBus.Properties", timeout=2)
            except dbus.exceptions.DBusException:
                continue
            if str(entry) == DESKTOP_ENTRY or name.endswith(DESKTOP_ENTRY):
                return name
        return None

    def open_uri(service, asin, invocation):
        uri = (BOOKS / (asin + ".m4b")).as_uri()
        player = backend.bus.get_object(service, MPRIS_PATH, introspect=False)
        player.OpenUri(uri, dbus_interface=MPRIS_PLAYER, timeout=30,
                       reply_handler=lambda *a: invocation.complete({"asin": asin}),
                       error_handler=lambda e: invocation.fail("Failed", str(e)))

    def select(parameters, invocation):
        asin = str(parameters.get("asin", ""))
        if not asin or not (BOOKS / (asin + ".m4b")).exists():
            raise Fault("NotFound", "book is not on the phone")
        service = find_player()
        if service:
            open_uri(service, asin, invocation)
            return
        # Application arretee : on la lance, puis on attend son lecteur MPRIS.
        subprocess.Popen(LAUNCH, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        state = {"done": False, "tries": 0}

        def poll():
            if state["done"]:
                return False
            state["tries"] += 1
            found = find_player()
            if found:
                state["done"] = True
                # laisse a l'application le temps de charger son moteur
                GLib.timeout_add(1500, lambda: (open_uri(found, asin, invocation), False)[1])
                return False
            if state["tries"] >= LAUNCH_TIMEOUT:
                state["done"] = True
                invocation.fail("Failed", "Audiobook did not start")
                return False
            return True

        GLib.timeout_add_seconds(1, poll)

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
