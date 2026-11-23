#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Service Sailplay d'Audiobook : bouton « Parcourir » de la carte Musique.

Expose les livres presents sur le telephone a l'ecran de la voiture (contrat
Content1 du SDK Sailplay). Choisir un livre l'envoie a l'application par la
commande MPRIS OpenUri, en lancant l'application si besoin. Le service est demarre a
la demande par D-Bus et s'arrete seul apres dix secondes d'inactivite.

Avec un Sailplay qui connait les indications de presentation, la page est
faite d'onglets (En cours, Nouveautes, Auteurs, Tous) et de cartes portant la
couverture et le statut de lecture de chaque livre. Avec un Sailplay plus
ancien, elle reste la liste simple des livres.

Le SDK est fourni par Sailplay (/opt/sailplay, GPL-3.0-or-later) : sans
Sailplay, ce service ne demarre pas et l'application n'en depend pas.
"""
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, "/opt/sailplay")

import dbus  # noqa: E402
import dbus.mainloop.glib  # noqa: E402
from gi.repository import GLib  # noqa: E402

from sailplay_sdk.content import ContentBackend, wire_content  # noqa: E402
from sailplay_sdk.content_model import content_item, content_page  # noqa: E402
from sailplay_sdk.model import Fault  # noqa: E402

try:  # indications de presentation : images, statut de lecture, cartes, onglets
    from sailplay_sdk.content import content_result  # noqa: E402
    HINTS = True
except ImportError:  # Sailplay plus ancien : liste simple
    HINTS = False

    def content_result(value):
        return {"content": wire_content(value)}

SERVICE = "org.solboki.Audiobook"
APPLICATION_ID = "harbour-audiobook"
# L'application est pilotee par MPRIS (commande standard OpenUri), le canal
# deja utilise par la voiture pour la lecture.
MPRIS_PREFIX = "org.mpris.MediaPlayer2."
DESKTOP_ENTRY = "harbour-audiobook"
MPRIS_PATH = "/org/mpris/MediaPlayer2"
MPRIS_PLAYER = "org.mpris.MediaPlayer2.Player"
PROPERTIES = "org.freedesktop.DBus.Properties"
# Lancement dans le bac a sable de l'application, comme le fait Sailplay.
LAUNCH = ["/usr/bin/sailjail", "-p", "harbour-audiobook.desktop", "--",
          "/usr/bin/sailfish-qml", "harbour-audiobook"]
LAUNCH_TIMEOUT = 40

HOME = Path.home()
DATA = HOME / ".local/share/org.solboki/harbour-audiobook"
# Lues par Sailplay, hors du bac a sable de l'application.
COVERS = HOME / ".cache/org.solboki/harbour-audiobook/covers"
BOOKS = HOME / "Music/Audible"
IDLE_SECONDS = 10
WATCH_SECONDS = 10   # filet de securite : telechargements, positions enregistrees
MAX_AUTHORS = 200

# Textes de l'ecran de la voiture : courts, une ligne par onglet.
_TEXTS = {
    "en": ("In progress", "New", "Authors", "All", "No books on the phone", "No results"),
    "fr": ("En cours", "Nouveautés", "Auteurs", "Tous", "Aucun livre sur le téléphone", "Aucun résultat"),
    "de": ("Begonnen", "Neu", "Autoren", "Alle", "Keine Bücher auf dem Telefon", "Keine Ergebnisse"),
    "es": ("En curso", "Novedades", "Autores", "Todos", "No hay libros en el teléfono", "Sin resultados"),
    "it": ("In corso", "Novità", "Autori", "Tutti", "Nessun libro sul telefono", "Nessun risultato"),
    "nl": ("Bezig", "Nieuw", "Auteurs", "Alle", "Geen boeken op de telefoon", "Geen resultaten"),
    "sv": ("Pågående", "Nytt", "Författare", "Alla", "Inga böcker på telefonen", "Inga resultat"),
    "fi": ("Kesken", "Uudet", "Kirjailijat", "Kaikki", "Puhelimessa ei ole kirjoja", "Ei tuloksia"),
    "pl": ("W trakcie", "Nowe", "Autorzy", "Wszystkie", "Brak książek w telefonie", "Brak wyników"),
    "ru": ("В процессе", "Новые", "Авторы", "Все", "В телефоне нет книг", "Ничего не найдено"),
}
TEXT = dict(zip(("progress", "new", "authors", "all", "empty", "none"),
                _TEXTS.get(os.environ.get("LANG", "")[:2], _TEXTS["en"])))

_cache = {}


def _read_json(path, default):
    """Fichier JSON, relu seulement quand il a change."""
    path = Path(path)
    try:
        stat = path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
        if _cache.get(path, (None, None))[0] != stamp:
            _cache[path] = (stamp, json.loads(path.read_text(encoding="utf-8")))
        return _cache[path][1]
    except Exception:
        return default


def _names(lst):
    return [p["name"] for p in (lst or []) if isinstance(p, dict) and p.get("name")]


def _cover(asin, it):
    local = COVERS / (asin + ".jpg")
    if local.exists():
        return str(local)
    images = it.get("product_images") or {}
    remote = images.get("500") or next(iter(images.values()), "")
    ok = (isinstance(remote, str) and remote.startswith("https://") and len(remote) <= 2048
          and not any(ord(c) < 32 for c in remote))
    return remote if ok else ""


def downloaded_books(playing=""):
    """Livres presents sur le telephone, du plus recemment ecoute au plus ancien."""
    present = {p.stem for p in BOOKS.glob("*.m4b")} if BOOKS.is_dir() else set()
    library = {it.get("asin"): it for it in _read_json(DATA / "library.json", [])}
    state = _read_json(DATA / "state.json", {})
    books = []
    for asin in present:
        it = library.get(asin, {})
        st = state.get(asin, {})
        runtime_ms = int(it.get("runtime_length_min") or 0) * 60000
        # Meme calcul que la bibliotheque de l'application.
        fraction = 0.0
        if st.get("position_ms") and runtime_ms:
            fraction = min(1.0, st["position_ms"] / runtime_ms)
        elif it.get("percent_complete"):
            try:
                fraction = float(it["percent_complete"]) / 100.0
            except (TypeError, ValueError):
                fraction = 0.0
        finished = bool(it.get("is_finished") or st.get("finished"))
        started = fraction > 0 or bool(st.get("position_ms"))
        if asin == playing:
            playback = "playing"
        elif finished:
            playback = "finished"
        else:
            playback = "started" if started else "unplayed"
        progress = "100 %" if finished else ("%d %%" % min(99, round(100 * fraction)) if fraction else "")
        authors = _names(it.get("authors"))
        series = " ".join(s.get("title") or "" for s in (it.get("series") or []) if isinstance(s, dict))
        books.append({
            "asin": asin,
            "title": it.get("title") or asin,
            "authors": authors,
            "subtitle": " · ".join(x for x in (", ".join(authors), progress) if x),
            "search": " ".join([it.get("title") or "", series] + authors).casefold(),
            "played": float(st.get("updated", 0)),
            "added": str(it.get("purchase_date") or ""),
            "cover": _cover(asin, it),
            "playback": playback,
        })
    books.sort(key=lambda b: (-b["played"], b["title"].casefold()))
    return books


def book_item(book):
    hints = {"image": book["cover"], "playback": book["playback"]} if HINTS else {}
    return content_item(book["asin"], book["title"][:1024], book["subtitle"][:1024],
                        kind="action", action="content.select", parameters={"asin": book["asin"]},
                        **hints)


def folder_item(identity, title, image=""):
    return content_item(identity, title[:1024], **({"image": image} if HINTS and image else {}))


def authors_of(books):
    """Auteurs par ordre alphabetique, avec la couverture de leur livre le plus recent."""
    authors = {}
    for book in books:
        # Audible range aussi les traducteurs parmi les auteurs (« Nom — Translator »).
        names = [n for n in book["authors"] if " — " not in n and " - " not in n] or book["authors"]
        for name in names:
            authors.setdefault(name[:240], book["cover"])
    return sorted(authors.items(), key=lambda entry: entry[0].casefold())[:MAX_AUTHORS]


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    loop = GLib.MainLoop()
    idle = [0]
    # Version des pages : augmentee quand leur contenu change, pour que la
    # voiture recharge la page affichee. Toutes les pages portent la meme.
    shown = {"version": 1, "playing": "", "signature": None, "check": 0}

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

    def listing(identity, title, entries, offset, limit, layout="wide", empty="", search=True):
        chunk = entries[offset:offset + limit]
        return content_page(identity, title, chunk, search_enabled=search,
                            offset=offset, has_more=offset + limit < len(entries),
                            message="" if entries else empty,
                            message_kind="none" if entries else "info", version=shown["version"],
                            **({"layout": layout} if HINTS else {}))

    def tabs(books):
        """Onglets de la racine : seulement ceux qui ont quelque chose a montrer."""
        folders = []
        if any(b["playback"] in ("playing", "started") for b in books):
            folders.append(folder_item("progress", TEXT["progress"]))
        if any(b["playback"] == "unplayed" for b in books):
            folders.append(folder_item("new", TEXT["new"]))
        if len(authors_of(books)) > 1:
            folders.append(folder_item("authors", TEXT["authors"]))
        folders.append(folder_item("all", TEXT["all"]))
        return folders

    def root_page(books, offset=0, limit=50):
        if not HINTS:  # liste simple, comme avant les onglets
            return listing("root", "Audiobook", [book_item(b) for b in books], offset, limit,
                           empty=TEXT["empty"])
        if not books:
            return content_page("root", "Audiobook", search_enabled=True, message=TEXT["empty"],
                                message_kind="info", version=shown["version"])
        return content_page("root", "Audiobook", tabs(books)[offset:offset + limit], search_enabled=True,
                            version=shown["version"], tabs=True)

    def page(identity, offset, limit, query=""):
        books = downloaded_books(shown["playing"])
        if query:
            q = query.casefold()
            found = [book_item(b) for b in books if q in b["search"]]
            return listing(identity, query, found, offset, limit, empty=TEXT["none"])
        if identity == "root":
            return root_page(books, offset, limit)
        if not HINTS:
            raise Fault("NotFound", "content folder is unavailable")
        if identity == "progress":
            chosen = [b for b in books if b["playback"] in ("playing", "started")]
            return listing(identity, TEXT["progress"], [book_item(b) for b in chosen], offset, limit)
        if identity == "new":
            chosen = sorted((b for b in books if b["playback"] == "unplayed"),
                            key=lambda b: b["added"], reverse=True)
            return listing(identity, TEXT["new"], [book_item(b) for b in chosen], offset, limit)
        if identity == "all":
            chosen = sorted(books, key=lambda b: b["title"].casefold())
            return listing(identity, TEXT["all"], [book_item(b) for b in chosen], offset, limit)
        if identity == "authors":
            folders = [folder_item("author:" + name, name, cover) for name, cover in authors_of(books)]
            return listing(identity, TEXT["authors"], folders, offset, limit, layout="grid")
        if identity.startswith("author:"):
            name = identity[len("author:"):]
            chosen = sorted((b for b in books if any(a[:240] == name for a in b["authors"])),
                            key=lambda b: b["title"].casefold())
            if chosen:
                return listing(identity, name, [book_item(b) for b in chosen], offset, limit)
        raise Fault("NotFound", "content folder is unavailable")

    def browse(parameters, invocation):
        result = page(parameters["id"], parameters["offset"], parameters["limit"],
                      parameters.get("query", ""))
        invocation.complete(content_result(result))

    def find_player():
        """Nom du lecteur MPRIS d'Audiobook, reconnu a son DesktopEntry."""
        for name in backend.bus.list_names():
            name = str(name)
            if not name.startswith(MPRIS_PREFIX):
                continue
            if name.startswith(MPRIS_PREFIX + DESKTOP_ENTRY + "."):
                return name  # nom donne par Amber : pas besoin d'interroger les autres lecteurs
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

    def playing_asin():
        """Livre en cours de lecture dans l'application, d'apres son lecteur MPRIS."""
        service = find_player()
        if not service:
            return ""
        try:
            obj = backend.bus.get_object(service, MPRIS_PATH, introspect=False)
            values = obj.GetAll(MPRIS_PLAYER, dbus_interface=PROPERTIES, timeout=2)
        except dbus.exceptions.DBusException:
            return ""
        if str(values.get("PlaybackStatus", "")) != "Playing":
            return ""
        name = unquote(str(values.get("Metadata", {}).get("xesam:url", "")).rsplit("/", 1)[-1])
        if name.endswith(".m4b"):
            return name[:-4]
        # Application d'avant la 0.9.3 : le livre en lecture est le dernier enregistre.
        state = _read_json(DATA / "state.json", {})
        return max(state, key=lambda asin: float(state[asin].get("updated", 0)), default="")

    def signature():
        return [(b["asin"], b["playback"], b["cover"], b["title"], b["authors"])
                for b in downloaded_books(shown["playing"])]

    def check():
        """Republie la racine, avec une nouvelle version, quand les pages ont change."""
        shown["check"] = 0
        shown["playing"] = playing_asin()
        current = signature()
        if current != shown["signature"]:
            shown["signature"] = current
            shown["version"] += 1
            backend.publish({"content": page("root", 0, 50)})
        return False

    def check_soon(*args, **kwargs):
        if not shown["check"]:
            shown["check"] = GLib.timeout_add(700, check)

    backend = ContentBackend(SERVICE, APPLICATION_ID,
                             {"content.browse": browse, "content.search": browse,
                              "content.select": select},
                             {"content": page("root", 0, 50)}, on_lifecycle=lifecycle)
    if HINTS:  # le statut « en lecture » suit le lecteur de l'application
        shown["playing"] = playing_asin()
        shown["signature"] = signature()
        if shown["playing"]:
            shown["version"] += 1
            backend.publish({"content": page("root", 0, 50)})
        backend.bus.add_signal_receiver(check_soon, signal_name="PropertiesChanged",
                                        dbus_interface=PROPERTIES, path=MPRIS_PATH, arg0=MPRIS_PLAYER)
        GLib.timeout_add_seconds(WATCH_SECONDS, lambda: (check_soon(), True)[1])
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
