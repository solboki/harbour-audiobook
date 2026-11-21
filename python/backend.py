# -*- coding: utf-8 -*-
"""Moteur Python de harbour-audiobook, appele depuis QML par PyOtherSide.

Les operations longues (bibliotheque, telechargements, positions) tournent
dans des fils d'execution separes et repondent par pyotherside.send().
"""

import json
import os
import queue
import shutil
import site
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

# Modules embarques dans le paquet (dossier lib/ a cote de python/). Ils passent
# en premier ; ceux installes par « pip install --user » restent un secours.
_LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
if os.path.isdir(_LIB) and _LIB not in sys.path:
    sys.path.insert(0, _LIB)
try:
    _user_site = site.getusersitepackages()
    if _user_site not in sys.path:
        sys.path.append(_user_site)
except Exception:
    pass

try:
    import pyotherside
except ImportError:  # execution hors de l'application (tests)
    class _Fake:
        @staticmethod
        def send(*args):
            print("send:", args)
    pyotherside = _Fake()

MISSING = []
try:
    import audible
    import httpx
    from audible.aescipher import decrypt_voucher_from_licenserequest
except ImportError as e:
    MISSING.append(e.name)
try:
    import snowcrypt.snowcrypt as snowcrypt
except ImportError as e:
    MISSING.append(e.name or "snowcrypt")

VERSION = "0.8.1"
HOME = Path.home()
DATA = HOME / ".local/share/harbour-audiobook"
CACHE = HOME / ".cache/harbour-audiobook"
COVERS = CACHE / "covers"
BOOKS_META = DATA / "books"
AUTH_FILE = DATA / "auth.json"
PROBE_AUTH = HOME / ".local/share/audible-probe/auth.json"
OLD_DATA = HOME / ".local/share/harbour-audible"   # nom des versions 0.1 a 0.5
LIBRARY_FILE = DATA / "library.json"
STATE_FILE = DATA / "state.json"
SETTINGS_FILE = DATA / "settings.json"
OUT_DIR = HOME / "Music/Audible"

DEFAULT_SETTINGS = {
    "sync_enabled": True,
    "skip_seconds": 30,
    "speed": 1.0,
    "start_page": "player",   # "player" ou "library"
    "sort_mode": "device",    # "device" ou "author"
    "last_asin": "",
    "browser": "internal",    # "internal" ou "external"
}

# Un seul fil pour le reseau « leger » (bibliotheque, positions) et un seul
# pour les telechargements : les telechargements passent l'un apres l'autre.
_net = ThreadPoolExecutor(max_workers=1)
_dl = ThreadPoolExecutor(max_workers=1)
_lock = threading.RLock()
_cancel = set()
_queued = set()
_login = {}


# --------------------------------------------------------------- outils
def _read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _err(e):
    msg = str(e) or e.__class__.__name__
    return msg[:300]


def _settings():
    s = dict(DEFAULT_SETTINGS)
    s.update(_read_json(SETTINGS_FILE, {}))
    return s


def _state():
    return _read_json(STATE_FILE, {})


def _book_path(asin):
    return OUT_DIR / f"{asin}.m4b"


def _auth():
    with _lock:
        return audible.Authenticator.from_file(AUTH_FILE)


def _save_auth(auth):
    with _lock:
        auth.to_file(AUTH_FILE, encryption=False)
        os.chmod(AUTH_FILE, 0o600)


class _Session:
    """Client Audible ouvert le temps d'une operation, jeton sauvegarde apres."""

    def __enter__(self):
        self.auth = _auth()
        self.client = audible.Client(auth=self.auth, timeout=30)
        return self

    def __exit__(self, *exc):
        try:
            self.client.close()
        finally:
            try:
                _save_auth(self.auth)
            except Exception:
                pass
        return False


# ---------------------------------------------------------- demarrage
def init():
    if not DATA.exists() and OLD_DATA.exists():
        # Reprise des donnees de l'ancien nom (connexion, positions, chapitres).
        shutil.copytree(OLD_DATA, DATA)
    DATA.mkdir(parents=True, exist_ok=True)
    COVERS.mkdir(parents=True, exist_ok=True)
    BOOKS_META.mkdir(parents=True, exist_ok=True)
    if not AUTH_FILE.exists() and PROBE_AUTH.exists():
        # Reprise de l'identification du script de test.
        shutil.copy2(PROBE_AUTH, AUTH_FILE)
        os.chmod(AUTH_FILE, 0o600)
    return {
        "version": VERSION,
        "missing": ", ".join(MISSING),
        "logged_in": AUTH_FILE.exists(),
        "settings": _settings(),
    }


def store_url():
    """Adresse de la boutique Audible du pays du compte."""
    domain = "fr"
    try:
        domain = _auth().locale.domain or "fr"
    except Exception:
        pass
    return f"https://www.audible.{domain}"


def set_setting(key, value):
    s = _settings()
    s[key] = value
    _write_json(SETTINGS_FILE, s)
    return s


# ------------------------------------------------------------- connexion
def login_start(locale):
    """Lance la connexion ; renvoie l'adresse a ouvrir dans un navigateur."""
    url_q = queue.Queue()
    answer = {"event": threading.Event(), "url": None}
    _login.clear()
    _login.update(answer=answer, result=None)

    def callback(url):
        url_q.put(url)
        answer["event"].wait()
        return answer["url"] or ""

    def run():
        try:
            auth = audible.Authenticator.from_login_external(
                locale=locale, login_url_callback=callback)
            DATA.mkdir(parents=True, exist_ok=True)
            _save_auth(auth)
            _login["result"] = {"ok": True}
        except Exception as e:
            _login["result"] = {"ok": False, "error": _err(e)}
            url_q.put(None)
        pyotherside.send("login_done", _login["result"])

    threading.Thread(target=run, daemon=True).start()
    url = url_q.get(timeout=60)
    if url is None:
        raise RuntimeError(_login["result"]["error"])
    return url


def login_finish(response_url):
    answer = _login.get("answer")
    if not answer:
        return {"ok": False, "error": "No login in progress."}
    if "openid.oa2.authorization_code" not in response_url:
        return {"ok": False, "error": "This address does not contain the authorization code. "
                "Copy the address of the “not found” page."}
    answer["url"] = response_url.strip()
    answer["event"].set()
    return {"ok": True, "pending": True}


def logout():
    try:
        auth = _auth()
        auth.deregister_device()
    except Exception:
        pass
    for p in (AUTH_FILE, LIBRARY_FILE):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    return True


# ---------------------------------------------------------- bibliotheque
def _flatten_people(lst):
    return ", ".join(p.get("name", "") for p in (lst or []) if p.get("name"))


def _item_view(it, state):
    asin = it.get("asin", "")
    cover_file = COVERS / f"{asin}.jpg"
    imgs = it.get("product_images") or {}
    remote_cover = imgs.get("500") or next(iter(imgs.values()), "")
    st = state.get(asin, {})
    runtime = int(it.get("runtime_length_min") or 0)
    progress = 0.0
    if st.get("position_ms") and runtime:
        progress = min(1.0, st["position_ms"] / (runtime * 60000.0))
    elif it.get("percent_complete"):
        try:
            progress = float(it["percent_complete"]) / 100.0
        except (TypeError, ValueError):
            progress = 0.0
    series = ""
    if it.get("series"):
        s = it["series"][0]
        series = s.get("title", "")
        if s.get("sequence"):
            series += f", tome {s['sequence']}"
    return {
        "asin": asin,
        "title": it.get("title") or "",
        "subtitle": it.get("subtitle") or "",
        "authors": _flatten_people(it.get("authors")),
        "narrators": _flatten_people(it.get("narrators")),
        "series": series,
        "runtime_min": runtime,
        "cover": str(cover_file) if cover_file.exists() else remote_cover,
        "remote_cover": remote_cover,
        "downloaded": _book_path(asin).exists(),
        "progress": progress,
        "finished": bool(it.get("is_finished") or st.get("finished")),
        "purchase_date": it.get("purchase_date") or "",
        "last_played": float(st.get("updated", 0)),
    }


def _library_views(items):
    state = _state()
    return [_item_view(it, state) for it in items
            if it.get("content_delivery_type") not in ("PodcastParent",)]


def library_cached():
    return _library_views(_read_json(LIBRARY_FILE, []))


def library_refresh():
    _net.submit(_library_refresh_job)
    return True


# « media » fournit les couvertures (product_images) avec le parametre image_sizes.
LIBRARY_GROUPS = ("product_desc", "product_attrs", "contributors", "media", "series",
                  "percent_complete", "is_finished")


def _invalid_groups(exc, groups):
    msg = str(exc)
    if "Invalid response group" not in msg:
        return []
    return [g for g in groups if g in msg.split("requested", 1)[-1]]


def _library_refresh_job():
    try:
        items, page = [], 1
        groups = list(LIBRARY_GROUPS)
        with _Session() as s:
            while True:
                try:
                    r = s.client.get(
                        "library",
                        num_results=200,
                        page=page,
                        response_groups=", ".join(groups),
                        image_sizes="500",
                        sort_by="-PurchaseDate",
                    )
                except Exception as e:
                    bad = _invalid_groups(e, groups)
                    if not bad:
                        raise
                    # Audible refuse certains groupes : on les retire et on recommence.
                    groups = [g for g in groups if g not in bad]
                    continue
                batch = r.get("items", []) if isinstance(r, dict) else []
                items.extend(batch)
                if len(batch) < 200:
                    break
                page += 1
        _write_json(LIBRARY_FILE, items)
        pyotherside.send("library", _library_views(items))
    except Exception as e:
        pyotherside.send("library_error", _err(e))
        return
    _fetch_covers(items)


def _fetch_covers(items):
    with httpx.Client(timeout=20, follow_redirects=True) as c:
        for it in items:
            asin = it.get("asin")
            imgs = it.get("product_images") or {}
            url = imgs.get("500") or next(iter(imgs.values()), None)
            dest = COVERS / f"{asin}.jpg"
            if not url or dest.exists():
                continue
            try:
                r = c.get(url)
                r.raise_for_status()
                dest.write_bytes(r.content)
                pyotherside.send("cover", asin, str(dest))
            except Exception:
                continue


# ------------------------------------------------------- telechargement
LICENSE_HEADERS = {
    "X-ADP-SW": "37801821",
    "X-ADP-Transport": "WIFI",
    "X-ADP-LTO": "120",
    "X-Device-Type-Id": "A2CZJZGLK2JJVM",
    "device_idiom": "phone",
}


def _flatten_chapters(chapters, out=None, depth=0):
    out = [] if out is None else out
    for c in chapters or []:
        out.append({
            "title": c.get("title") or "",
            "start_ms": int(c.get("start_offset_ms") or 0),
            "length_ms": int(c.get("length_ms") or 0),
            "depth": depth,
        })
        if c.get("chapters"):
            _flatten_chapters(c["chapters"], out, depth + 1)
    out.sort(key=lambda c: c["start_ms"])
    return out


def _parse_meta(asin, content_metadata, acr=None):
    ci = content_metadata.get("chapter_info") or {}
    ref = content_metadata.get("content_reference") or {}
    return {
        "asin": asin,
        "acr": acr or ref.get("acr"),
        "format": ref.get("content_format"),
        "duration_ms": int(ci.get("runtime_length_ms") or 0),
        "chapters": _flatten_chapters(ci.get("chapters")),
    }


def _request_license(s, asin):
    import secrets
    body = {
        "supported_drm_types": ["Mpeg", "Adrm"],  # pas de Widevine
        "quality": "High",
        "consumption_type": "Download",
        "chapter_titles_type": "Flat",
        "response_groups": ("last_position_heard, pdf_url, content_reference, "
                            "chapter_info"),
    }
    headers = dict(LICENSE_HEADERS, **{"X-Amzn-RequestId": secrets.token_hex(20).upper()})
    lr = s.client.post(f"content/{asin}/licenserequest", body=body, headers=headers)
    cl = lr["content_license"]
    if cl.get("status_code") == "Denied":
        raise RuntimeError(cl.get("message") or "License refused by Audible.")
    voucher = None
    if "license_response" in cl:
        voucher = decrypt_voucher_from_licenserequest(s.auth, lr)
    return cl, voucher


def download(asin):
    if asin in _queued:
        return False
    _queued.add(asin)
    _cancel.discard(asin)
    pyotherside.send("dl_progress", asin, "queued", 0.0)
    _dl.submit(_download_job, asin)
    return True


def cancel_download(asin):
    _cancel.add(asin)
    return True


class _Cancelled(Exception):
    pass


def _download_job(asin):
    raw = None
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        if asin in _cancel:
            raise _Cancelled()
        pyotherside.send("dl_progress", asin, "license", 0.0)
        with _Session() as s:
            cl, voucher = _request_license(s, asin)
            meta = cl["content_metadata"]
            book = _parse_meta(asin, meta, cl.get("acr"))
            lph = cl.get("last_position_heard") or {}
            book["remote_position"] = lph
            drm = cl.get("drm_type", "")
            url = meta["content_url"]["offline_url"]
            abytes = None
            if not voucher and drm == "Adrm":
                from audible.activation_bytes import get_activation_bytes
                abytes = get_activation_bytes(s.auth)
        _write_json(BOOKS_META / f"{asin}.json", book)

        ext = ".aaxc" if voucher else (".aax" if drm == "Adrm" else ".mp4")
        raw = OUT_DIR / f".{asin}{ext}.part"
        with httpx.stream("GET", url, follow_redirects=True, timeout=60,
                          headers={"User-Agent": "Audible/671 CFNetwork/1240.0.4"}) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0)) or 1
            done, last = 0, 0.0
            with open(raw, "wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    if asin in _cancel:
                        raise _Cancelled()
                    f.write(chunk)
                    done += len(chunk)
                    if time.time() - last > 0.5:
                        last = time.time()
                        pyotherside.send("dl_progress", asin, "download", done / total)

        final = _book_path(asin)
        tmp_final = OUT_DIR / f".{asin}.m4b.part"

        def progress(written, total_bytes):
            if asin in _cancel:
                raise _Cancelled()
            pyotherside.send("dl_progress", asin, "decrypt", written / max(total_bytes, 1))

        pyotherside.send("dl_progress", asin, "decrypt", 0.0)
        if voucher:
            snowcrypt.decrypt_aaxc(str(raw), str(tmp_final), voucher["key"], voucher["iv"],
                                   progress_callback=progress, progress_interval=4 << 20)
        elif abytes:
            snowcrypt.decrypt_aax(str(raw), str(tmp_final), abytes,
                                  progress_callback=progress, progress_interval=4 << 20)
        else:
            shutil.move(raw, tmp_final)
        os.replace(tmp_final, final)
        pyotherside.send("dl_done", asin, str(final))
    except _Cancelled:
        pyotherside.send("dl_error", asin, "")
    except Exception as e:
        pyotherside.send("dl_error", asin, _err(e))
    finally:
        _queued.discard(asin)
        _cancel.discard(asin)
        for p in OUT_DIR.glob(f".{asin}.*.part"):
            try:
                p.unlink()
            except OSError:
                pass


def delete_book(asin):
    try:
        _book_path(asin).unlink()
    except FileNotFoundError:
        pass
    return True


# -------------------------------------------------------------- lecture
def open_book(asin):
    """Donnees locales du livre ; la position Audible arrive ensuite par evenement."""
    book = _read_json(BOOKS_META / f"{asin}.json", None)
    st = _state().get(asin, {})
    item = next((i for i in library_cached() if i["asin"] == asin), {})
    result = {
        "asin": asin,
        "path": str(_book_path(asin)),
        "title": item.get("title", asin),
        "authors": item.get("authors", ""),
        "narrators": item.get("narrators", ""),
        "cover": item.get("cover", ""),
        "chapters": (book or {}).get("chapters", []),
        "duration_ms": (book or {}).get("duration_ms", 0),
        "position_ms": int(st.get("position_ms", 0)),
        "has_local": "position_ms" in st,
        "exists": _book_path(asin).exists(),
    }
    if not result["exists"]:
        return result
    _net.submit(_open_job, asin, book is None)
    return result


def _open_job(asin, need_meta):
    """Complete les chapitres si besoin, puis compare la position Audible."""
    try:
        with _Session() as s:
            if need_meta:
                m = s.client.get(
                    f"content/{asin}/metadata",
                    response_groups="chapter_info, content_reference",
                    quality="High", drm_type="Adrm", chapter_titles_type="Flat")
                book = _parse_meta(asin, m.get("content_metadata", {}))
                _write_json(BOOKS_META / f"{asin}.json", book)
                pyotherside.send("chapters", asin, book["chapters"], book["duration_ms"])
            if _settings()["sync_enabled"]:
                remote = _remote_positions(s, [asin]).get(asin)
                if remote:
                    _compare_remote(asin, remote)
    except Exception as e:
        pyotherside.send("sync_error", _err(e))


def _parse_ts(value):
    if not value:
        return None
    v = str(value).strip().replace("Z", "+00:00").replace(" ", "T")
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        try:
            dt = datetime.fromisoformat(v.split(".")[0])
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _remote_positions(s, asins):
    out = {}
    for i in range(0, len(asins), 25):  # 25 titres au plus par appel
        chunk = asins[i:i + 25]
        r = s.client.get("annotations/lastpositions", asins=",".join(chunk))
        for a in (r or {}).get("asin_last_position_heard_annots", []):
            lph = a.get("last_position_heard") or {}
            if lph.get("status", "Exists") != "Exists" or lph.get("position_ms") is None:
                continue
            try:
                pos = int(float(lph["position_ms"]))
            except (TypeError, ValueError):
                continue
            out[a.get("asin")] = {"position_ms": pos,
                                  "updated": _parse_ts(lph.get("last_updated"))}
    return out


def _compare_remote(asin, remote):
    st = _state().get(asin, {})
    rpos, rts = remote["position_ms"], remote["updated"]
    if st.get("pushed_ms") is not None and rpos == st["pushed_ms"]:
        return  # c'est notre propre envoi
    if "position_ms" not in st:
        pyotherside.send("remote_position", asin, rpos, "apply", rts or 0)
        return
    if abs(rpos - st["position_ms"]) < 5000:
        return
    if rts is None or rts > st.get("updated", 0):
        pyotherside.send("remote_position", asin, rpos, "propose", rts or 0)


def save_position(asin, position_ms, duration_ms=0, push=False):
    position_ms = int(position_ms)
    with _lock:
        state = _state()
        st = state.setdefault(asin, {})
        st["position_ms"] = position_ms
        st["updated"] = time.time()
        if duration_ms and position_ms > duration_ms - 30000:
            st["finished"] = True
        _write_json(STATE_FILE, state)
    if push and _settings()["sync_enabled"]:
        _net.submit(_push_job, asin, position_ms)
    return True


def _push_job(asin, position_ms):
    try:
        _push(asin, position_ms)
        pyotherside.send("pushed", asin, position_ms)
    except Exception as e:
        pyotherside.send("sync_error", _err(e))


def _push(asin, position_ms):
    book = _read_json(BOOKS_META / f"{asin}.json", {})
    acr = book.get("acr")
    if not acr:
        raise RuntimeError("Unknown content reference (ACR) for this book.")
    with _Session() as s:
        s.client.put(f"lastpositions/{asin}",
                     body={"acr": acr, "asin": asin, "position_ms": int(position_ms)})
    with _lock:
        state = _state()
        state.setdefault(asin, {})["pushed_ms"] = int(position_ms)
        _write_json(STATE_FILE, state)


def push_now(asin, position_ms, duration_ms=0):
    """Envoi synchrone, utilise a la fermeture de l'application."""
    save_position(asin, position_ms, duration_ms, push=False)
    if not _settings()["sync_enabled"]:
        return True
    try:
        _push(asin, position_ms)
        return True
    except Exception:
        return False


def sync_library_positions():
    """Recupere les positions Audible des livres telecharges (pour la liste)."""
    _net.submit(_sync_library_job)
    return True


def _sync_library_job():
    if not _settings()["sync_enabled"]:
        return
    asins = [p.stem for p in OUT_DIR.glob("*.m4b")]
    if not asins:
        return
    try:
        with _Session() as s:
            remote = _remote_positions(s, asins)
        with _lock:
            state = _state()
            changed = False
            for asin, r in remote.items():
                st = state.setdefault(asin, {})
                if st.get("pushed_ms") == r["position_ms"]:
                    continue
                if r["updated"] and r["updated"] > st.get("updated", 0):
                    st["position_ms"] = r["position_ms"]
                    st["updated"] = r["updated"]
                    changed = True
            if changed:
                _write_json(STATE_FILE, state)
        if changed:
            pyotherside.send("library", library_cached())
    except Exception as e:
        pyotherside.send("sync_error", _err(e))
