#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Service Sailplay d'Audiobook : bouton « Parcourir » de la carte Musique.

Expose la bibliotheque a l'ecran de la voiture (contrat Content1 du SDK
Sailplay), les livres presents sur le telephone toujours en premier. Choisir
un livre l'envoie a l'application par la commande MPRIS OpenUri, en lancant
l'application si besoin ; un livre absent du telephone est alors telecharge
par l'application, puis lu. Le service est demarre a
la demande par D-Bus et s'arrete seul apres dix secondes d'inactivite.

Avec un Sailplay qui connait les indications de presentation, la page est
faite d'onglets (En cours, Telecharges, Nouveautes, Auteurs, Genres, Absents) et de cartes portant la
couverture et le statut de lecture de chaque livre. Avec un Sailplay plus
ancien, elle reste la liste simple des livres.

Le SDK est fourni par Sailplay (/opt/sailplay, GPL-3.0-or-later) : sans
Sailplay, ce service ne demarre pas et l'application n'en depend pas.
"""
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
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
MOSAICS = COVERS.parent / "mosaics"   # couvertures assemblees des auteurs et des genres
BOOKS = HOME / "Music/Audible"
FFMPEG = "/usr/bin/ffmpeg"
IDLE_SECONDS = 10
WATCH_SECONDS = 10   # filet de securite : telechargements, positions enregistrees
MAX_GROUPS = 200     # auteurs ou genres
MOSAIC_SIZE = 480
MOSAIC_DAYS = 60
TO_DOWNLOAD = "↓ "       # devant le sous-titre d'un livre absent du telephone
REQUEST_SECONDS = 90     # delai laisse a l'application pour commencer un telechargement

# Textes de l'ecran de la voiture : courts, une ligne par onglet.
_TEXTS = {
    "en": ("In progress", "New", "Authors", "All", "No books on the phone", "No results", "Downloaded", "Downloading…", "Genres", "Not on phone"),
    "fr": ("En cours", "Nouveautés", "Auteurs", "Tous", "Aucun livre sur le téléphone", "Aucun résultat", "Téléchargés", "Téléchargement…", "Genres", "Absents"),
    "de": ("Begonnen", "Neu", "Autoren", "Alle", "Keine Bücher auf dem Telefon", "Keine Ergebnisse", "Geladen", "Wird geladen…", "Genres", "Nicht geladen"),
    "es": ("En curso", "Novedades", "Autores", "Todos", "No hay libros en el teléfono", "Sin resultados", "Descargados", "Descargando…", "Géneros", "Sin descargar"),
    "it": ("In corso", "Novità", "Autori", "Tutti", "Nessun libro sul telefono", "Nessun risultato", "Scaricati", "Download…", "Generi", "Non scaricati"),
    "nl": ("Bezig", "Nieuw", "Auteurs", "Alle", "Geen boeken op de telefoon", "Geen resultaten", "Gedownload", "Downloaden…", "Genres", "Niet geladen"),
    "sv": ("Pågående", "Nytt", "Författare", "Alla", "Inga böcker på telefonen", "Inga resultat", "Nedladdade", "Laddar ned…", "Genrer", "Ej nedladdade"),
    "fi": ("Kesken", "Uudet", "Kirjailijat", "Kaikki", "Puhelimessa ei ole kirjoja", "Ei tuloksia", "Ladatut", "Ladataan…", "Lajit", "Lataamatta"),
    "pl": ("W trakcie", "Nowe", "Autorzy", "Wszystkie", "Brak książek w telefonie", "Brak wyników", "Pobrane", "Pobieranie…", "Gatunki", "Niepobrane"),
    "ru": ("В процессе", "Новые", "Авторы", "Все", "В телефоне нет книг", "Ничего не найдено", "Загруженные", "Загрузка…", "Жанры", "Не загружены"),
}
TEXT = dict(zip(("progress", "new", "authors", "all", "empty", "none", "downloaded", "downloading",
                 "genres", "absent"),
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


def downloading():
    """Livres dont l'application ecrit le fichier en ce moment (.<asin>.<ext>.part)."""
    if not BOOKS.is_dir():
        return set()
    return {p.name[1:].split(".", 1)[0] for p in BOOKS.glob(".*.part")}


def library_books(playing="", requested=()):
    """Toute la bibliotheque : les livres presents sur le telephone (ou en cours
    de telechargement) d'abord, puis du plus recemment ecoute au plus ancien."""
    present = {p.stem for p in BOOKS.glob("*.m4b")} if BOOKS.is_dir() else set()
    loading = (downloading() | set(requested)) - present
    library = {it.get("asin"): it for it in _read_json(DATA / "library.json", [])
               if isinstance(it, dict) and it.get("asin")
               and it.get("content_delivery_type") not in ("PodcastParent",)}
    state = _read_json(DATA / "state.json", {})
    books = []
    for asin in present | set(library):
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
        genres = []
        for entry in it.get("category_ladders") or []:
            ladder = entry.get("ladder") if isinstance(entry, dict) else None
            name = ladder[0].get("name") if ladder and isinstance(ladder[0], dict) else ""
            if name and name not in genres:
                genres.append(name)
        series = " ".join(s.get("title") or "" for s in (it.get("series") or []) if isinstance(s, dict))
        subtitle = " · ".join(x for x in (", ".join(authors), progress) if x)
        if asin in loading:
            subtitle = TEXT["downloading"]
        elif asin not in present:
            subtitle = TO_DOWNLOAD + subtitle
        local = COVERS / (asin + ".jpg")
        books.append({
            "asin": asin,
            "title": it.get("title") or asin,
            "authors": authors,
            "subtitle": subtitle,
            "search": " ".join([it.get("title") or "", series] + authors).casefold(),
            "played": float(st.get("updated", 0)),
            "added": str(it.get("purchase_date") or ""),
            "cover": _cover(asin, it),
            "playback": playback,
            "local_cover": str(local) if local.exists() else "",
            "genres": genres,
            # Un livre en cours de telechargement compte deja comme telecharge.
            "downloaded": asin in present or asin in loading,
            "loading": asin in loading,
        })
    books.sort(key=lambda b: (not b["downloaded"], -b["played"], b["title"].casefold()))
    return books


def first_downloaded(books, key=None, reverse=False):
    """Tri d'une page : les livres presents sur le telephone restent en tete."""
    if key is not None:
        books = sorted(books, key=key, reverse=reverse)
    return sorted(books, key=lambda b: not b["downloaded"])


def book_item(book):
    hints = {"image": book["cover"], "playback": book["playback"]} if HINTS else {}
    return content_item(book["asin"], book["title"][:1024], book["subtitle"][:1024],
                        kind="action", action="content.select", parameters={"asin": book["asin"]},
                        **hints)


def folder_item(identity, title, image=""):
    return content_item(identity, title[:1024], **({"image": image} if HINTS and image else {}))


def mosaic_target(paths):
    name = hashlib.sha1("\n".join(paths).encode("utf-8")).hexdigest()[:20] + ".jpg"
    return MOSAICS / name


def make_mosaic(paths):
    """Assemble deux a quatre couvertures en une image carree, avec ffmpeg
    (installe avec Sailplay). Renvoie True si l'image existe a la fin."""
    target = mosaic_target(paths)
    if target.exists():
        return True
    half = MOSAIC_SIZE // 2
    # Deux livres : deux moities ; trois : une moitie et deux quarts ; quatre : quatre quarts.
    boxes = {2: [(0, 0, half, MOSAIC_SIZE), (half, 0, half, MOSAIC_SIZE)],
             3: [(0, 0, half, MOSAIC_SIZE), (half, 0, half, half), (half, half, half, half)],
             4: [(0, 0, half, half), (half, 0, half, half), (0, half, half, half), (half, half, half, half)]}[len(paths)]
    command = [FFMPEG, "-v", "error", "-y"]
    for path in paths:
        command += ["-i", path]
    parts = ["[%d]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d[p%d]" % (i, w, h, w, h, i)
             for i, (x, y, w, h) in enumerate(boxes)]
    parts.append("".join("[p%d]" % i for i in range(len(boxes)))
                 + "xstack=inputs=%d:layout=%s" % (len(boxes), "|".join("%d_%d" % (x, y) for x, y, w, h in boxes)))
    partial = target.with_suffix(".part")
    try:
        MOSAICS.mkdir(parents=True, exist_ok=True)
        subprocess.run(command + ["-filter_complex", ";".join(parts), "-frames:v", "1", "-q:v", "3",
                                  "-f", "mjpeg", str(partial)],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=20, check=True)
        os.replace(partial, target)
        return True
    except Exception:
        try:
            partial.unlink()
        except OSError:
            pass
        return False


def clean_mosaics():
    """Retire les images assemblees anciennes ; elles sont refaites a la demande."""
    limit = time.time() - MOSAIC_DAYS * 86400
    try:
        for path in MOSAICS.iterdir():
            if path.stat().st_mtime < limit:
                path.unlink()
    except OSError:
        pass


def author_names(book):
    # Audible range aussi les traducteurs parmi les auteurs (« Nom — Translator »).
    return [n[:240] for n in book["authors"] if " — " not in n and " - " not in n] or \
        [n[:240] for n in book["authors"]]


def genre_names(book):
    return [n[:240] for n in book["genres"]]


def groups_of(books, names):
    """Auteurs ou genres par ordre alphabetique, chacun avec ses livres
    (ceux du telephone en premier, comme dans la liste recue)."""
    groups = {}
    for book in books:
        for name in names(book):
            groups.setdefault(name, []).append(book)
    return sorted(groups.items(), key=lambda entry: entry[0].casefold())[:MAX_GROUPS]


def group_covers(members):
    """Couvertures (quatre au plus) a montrer sur la carte d'un auteur ou d'un genre."""
    return [b["local_cover"] for b in members if b["local_cover"]][:4]


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    loop = GLib.MainLoop()
    idle = [0]
    # Version des pages : augmentee quand leur contenu change, pour que la
    # voiture recharge la page affichee. Toutes les pages portent la meme.
    shown = {"version": 1, "playing": "", "signature": None, "check": 0}
    mosaics = {"wanted": [], "failed": set(), "busy": False}
    closing = [False]
    waiting = set()  # livres choisis dans la voiture et pas encore telecharges
    requested = {}  # asin -> heure de la demande de telechargement faite depuis la voiture

    def current_books():
        limit = time.monotonic() - REQUEST_SECONDS
        for asin in [a for a, moment in requested.items() if moment < limit]:
            del requested[asin]
        return library_books(shown["playing"], requested)

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

    def in_progress(book):
        # Un livre demande depuis la voiture y attend la fin de son telechargement.
        return book["playback"] in ("playing", "started") or book["loading"]

    def group_image(members):
        """Plusieurs couvertures sur la carte ; en attendant leur assemblage, une seule."""
        covers = group_covers(members)
        if len(covers) > 1:
            target = mosaic_target(covers)
            if target.exists():
                return str(target)
            if os.access(FFMPEG, os.X_OK) and covers not in mosaics["wanted"] and tuple(covers) not in mosaics["failed"]:
                mosaics["wanted"].append(covers)
        return covers[0] if covers else next((b["cover"] for b in members if b["cover"]), "")

    def build_mosaics():
        """Assemble les images demandees hors de la boucle principale, puis
        republie la racine pour que la voiture recharge la page avec elles."""
        if mosaics["busy"] or not mosaics["wanted"]:
            return
        mosaics["busy"] = True
        wanted, mosaics["wanted"] = mosaics["wanted"], []

        def work():
            failed = [tuple(covers) for covers in wanted if not make_mosaic(covers)]
            GLib.idle_add(done, failed)

        def done(failed):
            mosaics["busy"] = False
            mosaics["failed"].update(failed)
            if len(failed) < len(wanted) and not closing[0]:
                shown["version"] += 1
                backend.publish({"content": page("root", 0, 50)})
            return False

        threading.Thread(target=work, daemon=True).start()

    def group_page(identity, title, books, names, offset, limit):
        """Cartes des auteurs ou des genres ; les images ne sont faites que pour la page demandee."""
        groups = groups_of(books, names)
        chunk = [folder_item(identity[:-1] + ":" + name, name, group_image(members))
                 for name, members in groups[offset:offset + limit]]
        build_mosaics()
        return listing(identity, title, [None] * offset + chunk + [None] * max(0, len(groups) - offset - limit),
                       offset, limit, layout="grid")

    def member_page(identity, books, names, offset, limit):
        name = identity.split(":", 1)[1]
        chosen = first_downloaded((b for b in books if name in names(b)), key=lambda b: b["title"].casefold())
        if not chosen:
            raise Fault("NotFound", "content folder is unavailable")
        return listing(identity, name, [book_item(b) for b in chosen], offset, limit)

    def tabs(books):
        """Onglets de la racine : seulement ceux qui ont quelque chose a montrer."""
        folders = []
        if any(in_progress(b) for b in books):
            folders.append(folder_item("progress", TEXT["progress"]))
        if any(b["downloaded"] for b in books):
            folders.append(folder_item("downloaded", TEXT["downloaded"]))
        if any(b["playback"] == "unplayed" for b in books):
            folders.append(folder_item("new", TEXT["new"]))
        if len(groups_of(books, author_names)) > 1:
            folders.append(folder_item("authors", TEXT["authors"]))
        if len(groups_of(books, genre_names)) > 1:
            folders.append(folder_item("genres", TEXT["genres"]))
        if any(not b["downloaded"] for b in books):
            folders.append(folder_item("absent", TEXT["absent"]))
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
        books = current_books()
        if query:
            q = query.casefold()
            found = [book_item(b) for b in books if q in b["search"]]
            return listing(identity, query, found, offset, limit, empty=TEXT["none"])
        if identity == "root":
            return root_page(books, offset, limit)
        if not HINTS:
            raise Fault("NotFound", "content folder is unavailable")
        if identity == "progress":
            chosen = sorted((b for b in books if in_progress(b)), key=lambda b: (not b["loading"], not b["downloaded"]))
            return listing(identity, TEXT["progress"], [book_item(b) for b in chosen], offset, limit)
        if identity == "downloaded":
            chosen = [b for b in books if b["downloaded"]]
            return listing(identity, TEXT["downloaded"], [book_item(b) for b in chosen], offset, limit)
        if identity == "new":
            chosen = first_downloaded((b for b in books if b["playback"] == "unplayed"),
                                      key=lambda b: b["added"], reverse=True)
            return listing(identity, TEXT["new"], [book_item(b) for b in chosen], offset, limit)
        if identity == "absent":
            chosen = sorted((b for b in books if not b["downloaded"]), key=lambda b: b["title"].casefold())
            return listing(identity, TEXT["absent"], [book_item(b) for b in chosen], offset, limit)
        if identity == "authors":
            return group_page(identity, TEXT["authors"], books, author_names, offset, limit)
        if identity == "genres":
            return group_page(identity, TEXT["genres"], books, genre_names, offset, limit)
        if identity.startswith("author:"):
            return member_page(identity, books, author_names, offset, limit)
        if identity.startswith("genre:"):
            return member_page(identity, books, genre_names, offset, limit)
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

    def selected(asin):
        """Resultat d'un choix. Pour un livre a telecharger, on demande a la
        voiture de rester sur la page et de montrer l'onglet « En cours », ou
        le livre attend ; un Sailplay qui ignore cette indication n'en tient pas compte."""
        result = {"asin": asin}
        if asin in waiting:
            waiting.discard(asin)
            result["presentation"] = dbus.Dictionary({"open": "progress"}, signature="sv")
        return result

    def open_uri(service, asin, invocation):
        uri = (BOOKS / (asin + ".m4b")).as_uri()
        player = backend.bus.get_object(service, MPRIS_PATH, introspect=False)
        player.OpenUri(uri, dbus_interface=MPRIS_PLAYER, timeout=30,
                       reply_handler=lambda *a: invocation.complete(selected(asin)),
                       error_handler=lambda e: invocation.fail("Failed", str(e)))

    def select(parameters, invocation):
        asin = str(parameters.get("asin", ""))
        if not asin or "/" in asin or not any(b["asin"] == asin for b in current_books()):
            raise Fault("NotFound", "book is not in the library")
        if not (BOOKS / (asin + ".m4b")).exists():
            # L'application le telecharge puis le lit ; la page l'annonce des maintenant.
            requested[asin] = time.monotonic()
            if HINTS:
                check_soon()
                waiting.add(asin)
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
        return [(b["asin"], b["playback"], b["cover"], b["title"], b["downloaded"], b["loading"],
                 b["authors"], b["genres"]) for b in current_books()]

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
        clean_mosaics()
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
        closing[0] = True
        if idle[0]:
            GLib.source_remove(idle[0])
        backend.close()


if __name__ == "__main__":
    main()
