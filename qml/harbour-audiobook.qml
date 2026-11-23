import QtQuick 2.6
import Sailfish.Silica 1.0
import QtMultimedia 5.6
import io.thp.pyotherside 1.5
import "pages"
import "cover"

ApplicationWindow {
    id: app

    // ------------------------------------------------------------ etat
    property bool backendReady: false
    property bool loggedIn: false
    property string missing: ""
    property string version: ""
    property var settings: ({ sync_enabled: true, skip_seconds: 30, speed: 1.0 })
    property int skipSeconds: settings.skip_seconds || 30
    property real speed: settings.speed || 1.0

    property var book: null            // livre charge dans le lecteur
    property var chapters: []
    property int durationMs: 0
    property int chapterIndex: -1
    property var proposal: null        // position Audible proposee {position_ms, ts}
    property var downloads: ({})       // asin -> {phase, fraction}
    property string lastSyncError: ""
    property bool playing: player.playbackState === Audio.PlayingState
    property int pendingSeek: -1
    property bool storeVisited: false

    // minuterie de sommeil : 0 = inactive, -1 = fin du chapitre, sinon minutes
    property int sleepMode: 0
    property int sleepRemaining: 0     // secondes

    property alias library: libraryModel
    ListModel { id: libraryModel }

    initialPage: Component { StartPage { } }
    cover: Component { CoverPage { } }
    allowedOrientations: defaultAllowedOrientations

    // ------------------------------------------------------ utilitaires
    function fmt(ms) {
        if (ms < 0) ms = 0
        var s = Math.floor(ms / 1000)
        var h = Math.floor(s / 3600)
        var m = Math.floor((s % 3600) / 60)
        var sec = s % 60
        var mm = (h > 0 && m < 10) ? "0" + m : "" + m
        return (h > 0 ? h + ":" : "") + mm + ":" + (sec < 10 ? "0" : "") + sec
    }
    function fmtDuration(min) {
        var h = Math.floor(min / 60), m = min % 60
        return h > 0 ? qsTr("%1 h %2").arg(h).arg((m < 10 ? "0" : "") + m) : qsTr("%1 min").arg(m)
    }

    // Bibliotheque : tableau maitre en JavaScript, puis modele trie et filtre.
    property var libraryItems: []
    property string sortMode: settings.sort_mode || "device"   // "device" ou "author"
    property bool onlyDownloaded: false
    property string search: ""
    onSortModeChanged: rebuildLibrary()
    onOnlyDownloadedChanged: rebuildLibrary()
    onSearchChanged: searchTimer.restart()
    Timer { id: searchTimer; interval: 250; onTriggered: app.rebuildLibrary() }

    function fillLibrary(items) {
        for (var i = 0; i < items.length; i++) {
            var d = downloads[items[i].asin]
            items[i].dlPhase = d ? d.phase : ""
            items[i].dlFraction = d ? d.fraction : 0
        }
        libraryItems = items
        rebuildLibrary()
    }

    function onDevice(it) { return it.downloaded || it.dlPhase !== "" }
    function firstAuthor(it) { return (it.authors || "").split(",")[0].trim() }
    function surnameKey(name) {
        var parts = name.split(" ")
        return (parts[parts.length - 1] + " " + name).toLowerCase()
    }

    // Signales a la page Bibliotheque pour qu'elle garde sa position en haut.
    signal libraryAboutToRebuild()
    signal libraryRebuilt()

    function rebuildLibrary() {
        var s = search.toLowerCase()
        var list = []
        for (var i = 0; i < libraryItems.length; i++) {
            var it = libraryItems[i]
            if (onlyDownloaded && !onDevice(it)) continue
            if (s !== "" && it.title.toLowerCase().indexOf(s) < 0
                    && it.authors.toLowerCase().indexOf(s) < 0
                    && it.series.toLowerCase().indexOf(s) < 0) continue
            it.order = i
            list.push(it)
        }
        if (sortMode === "author") {
            list.sort(function(a, b) {
                var ka = surnameKey(firstAuthor(a)), kb = surnameKey(firstAuthor(b))
                if (ka !== kb) return ka < kb ? -1 : 1
                var sa = a.series + a.title, sb = b.series + b.title
                return sa.localeCompare(sb)
            })
            for (var j = 0; j < list.length; j++)
                list[j].section = firstAuthor(list[j]) || qsTr("Unknown author")
        } else {
            list.sort(function(a, b) {
                var da = onDevice(a) ? 0 : 1, db = onDevice(b) ? 0 : 1
                if (da !== db) return da - db
                if (da === 0 && a.last_played !== b.last_played)
                    return b.last_played - a.last_played   // derniers ecoutes en tete
                return a.order - b.order                  // sinon ordre d'achat
            })
            for (var k = 0; k < list.length; k++)
                list[k].section = onDevice(list[k]) ? qsTr("On your phone")
                                                    : qsTr("Available to download")
        }
        libraryAboutToRebuild()
        libraryModel.clear()
        libraryModel.append(list)
        libraryRebuilt()
    }

    function indexOfAsin(asin) {
        for (var i = 0; i < libraryModel.count; i++)
            if (libraryModel.get(i).asin === asin) return i
        return -1
    }
    function setItem(asin, props) {
        var regroup = false
        for (var j = 0; j < libraryItems.length; j++) {
            if (libraryItems[j].asin === asin) {
                var it = libraryItems[j]
                var before = onDevice(it)
                for (var k in props) it[k] = props[k]
                regroup = before !== onDevice(it)
                break
            }
        }
        if (regroup) { rebuildLibrary(); return }
        var i = indexOfAsin(asin)
        if (i < 0) return
        for (var p in props) libraryModel.setProperty(i, p, props[p])
    }

    // --------------------------------------------------------- lecteur
    function openBook(asin, autoplay) {
        if (autoplay === undefined) autoplay = true
        if (book && book.asin === asin) { if (autoplay && !playing) play(); return }
        if (book) savePosition(true)
        py.call("backend.open_book", [asin], function(b) {
            if (!b.exists) return
            updateSetting("last_asin", asin)
            setItem(asin, { last_played: Date.now() / 1000 })
            proposal = null
            book = b
            chapters = b.chapters
            durationMs = b.duration_ms
            pendingSeek = b.position_ms
            player.source = "file://" + b.path
            if (autoplay) player.play()
        })
    }
    function play() { if (book) player.play() }
    function pause() { if (book) player.pause() }
    function toggle() { if (playing) pause(); else play() }
    function seekTo(ms) {
        ms = Math.max(0, Math.min(ms, totalMs() - 1000))
        if (player.status === Audio.Loaded || player.status === Audio.Buffered
                || player.status === Audio.Buffering || player.status === Audio.EndOfMedia)
            player.seek(ms)
        else
            pendingSeek = ms
    }
    function skip(deltaMs) { seekTo(player.position + deltaMs) }
    function totalMs() { return durationMs > 0 ? durationMs : player.duration }
    function positionMs() { return pendingSeek >= 0 ? pendingSeek : player.position }

    function chapterAt(ms) {
        var idx = -1
        for (var i = 0; i < chapters.length; i++) {
            if (chapters[i].start_ms <= ms + 500) idx = i
            else break
        }
        return idx
    }
    function chapterStart(i) { return i >= 0 && i < chapters.length ? chapters[i].start_ms : 0 }
    function chapterEnd(i) {
        if (i < 0 || chapters.length === 0) return totalMs()
        if (i + 1 < chapters.length) return chapters[i + 1].start_ms
        return totalMs()
    }
    function previousChapter() {
        var i = chapterIndex
        // plus de 5 s dans le chapitre : retour a son debut
        if (i >= 0 && player.position - chapterStart(i) > 5000) seekTo(chapterStart(i))
        else if (i > 0) seekTo(chapterStart(i - 1))
        else seekTo(0)
    }
    function nextChapter() {
        if (chapterIndex + 1 < chapters.length) seekTo(chapterStart(chapterIndex + 1))
    }

    function savePosition(push) {
        if (!book || player.position <= 0) return
        py.call("backend.save_position", [book.asin, player.position, totalMs(), push])
        var t = totalMs()
        if (t > 0) setItem(book.asin, { progress: player.position / t })
    }

    function setSleep(mode) {
        sleepMode = mode
        sleepRemaining = mode > 0 ? mode * 60 : 0
    }

    // Boutique Audible : navigateur integre (WebView de Sailfish) ou externe.
    function openStore() {
        py.call("backend.store_url", [], function(url) {
            if (settings.browser === "external") { Qt.openUrlExternally(url); return }
            var c = Qt.createComponent(Qt.resolvedUrl("pages/StorePage.qml"))
            if (c.status === Component.Ready) {
                pageStack.push(c, { startUrl: url })
            } else {
                console.log("Navigateur integre indisponible : " + c.errorString())
                Qt.openUrlExternally(url)
            }
        })
    }

    function updateSetting(key, value) {
        py.call("backend.set_setting", [key, value], function(s) { settings = s })
    }

    Audio {
        id: player
        autoLoad: true
        playbackRate: app.speed
        onStatusChanged: {
            if ((status === Audio.Loaded || status === Audio.Buffered) && app.pendingSeek > 0) {
                seek(app.pendingSeek)
                app.pendingSeek = -1
            }
            if (status === Audio.EndOfMedia) app.savePosition(true)
        }
        onPositionChanged: {
            var c = app.chapterAt(position)
            if (c !== app.chapterIndex) {
                if (app.sleepMode === -1 && app.chapterIndex >= 0 && c === app.chapterIndex + 1
                        && app.playing) {
                    pause()
                    app.sleepMode = 0
                }
                app.chapterIndex = c
            }
        }
        onPlaybackStateChanged: {
            if (playbackState === Audio.PausedState) app.savePosition(true)
        }
        onDurationChanged: if (app.durationMs <= 0) app.durationMs = duration
    }

    Timer {   // sauvegarde locale
        interval: 10000; repeat: true; running: app.playing
        onTriggered: app.savePosition(false)
    }
    Timer {   // envoi a Audible
        interval: 60000; repeat: true; running: app.playing
        onTriggered: app.savePosition(true)
    }
    Timer {   // minuterie de sommeil
        interval: 1000; repeat: true; running: app.playing && app.sleepMode > 0
        onTriggered: {
            app.sleepRemaining -= 1
            if (app.sleepRemaining <= 0) {
                player.pause()
                app.sleepMode = 0
            }
        }
    }

    // Livre demande depuis la voiture (Sailplay) : lu des que le moteur est pret.
    property string remoteAsin: ""
    property bool remoteRequested: false   // la voiture a choisi un livre : ne pas recharger le dernier
    // Livre choisi dans la voiture mais absent du telephone : telecharge, puis lu.
    property string remoteDownload: ""
    function playFromRemote(asin) {
        remoteRequested = true
        if (!backendReady) { remoteAsin = asin; return }
        remoteDownload = ""
        if (book && book.asin === asin) { play(); return }
        py.call("backend.is_downloaded", [asin], function(present) {
            if (present) { openBook(asin, true); return }
            remoteDownload = asin
            py.call("backend.download", [asin])
        })
    }
    onBackendReadyChanged: if (backendReady && remoteAsin !== "") {
        var asin = remoteAsin
        remoteAsin = ""
        playFromRemote(asin)
    }

    Loader {  // service D-Bus pour Sailplay, si Nemo.DBus est disponible
        source: "components/DBusControl.qml"
        onStatusChanged: if (status === Loader.Error) console.log("Nemo.DBus indisponible")
    }

    Loader {  // boutons des ecouteurs (ressource HeadsetButtons de Sailfish)
        source: "components/HeadsetKeys.qml"
        onStatusChanged: if (status === Loader.Error) console.log("Boutons des ecouteurs indisponibles")
    }

    Loader {  // ecran verrouille et voiture (MPRIS), si disponible
        source: "components/Mpris.qml"
        onStatusChanged: if (status === Loader.Error) console.log("MPRIS indisponible")
    }

    // ---------------------------------------------------------- moteur
    Python {
        id: py
        Component.onCompleted: {
            addImportPath(Qt.resolvedUrl("../python"))

            setHandler("library", function(items) { app.fillLibrary(items) })
            setHandler("library_error", function(msg) { app.lastSyncError = qsTranslate("backend", msg) })
            setHandler("cover", function(asin, path) { app.setItem(asin, { cover: path }) })
            setHandler("dl_progress", function(asin, phase, fraction) {
                var d = app.downloads; d[asin] = { phase: phase, fraction: fraction }
                app.downloads = d
                app.setItem(asin, { dlPhase: phase, dlFraction: fraction })
            })
            setHandler("dl_done", function(asin, path) {
                var d = app.downloads; delete d[asin]; app.downloads = d
                app.setItem(asin, { dlPhase: "", dlFraction: 0, downloaded: true })
                if (asin === app.remoteDownload) {
                    app.remoteDownload = ""
                    app.openBook(asin, true)
                }
            })
            setHandler("dl_error", function(asin, msg) {
                var d = app.downloads; delete d[asin]; app.downloads = d
                app.setItem(asin, { dlPhase: "", dlFraction: 0 })
                if (asin === app.remoteDownload) app.remoteDownload = ""
                if (msg) app.lastSyncError = qsTranslate("backend", msg)
            })
            setHandler("chapters", function(asin, chs, dur) {
                if (app.book && app.book.asin === asin) {
                    app.chapters = chs
                    if (dur > 0) app.durationMs = dur
                    app.chapterIndex = app.chapterAt(player.position)
                }
            })
            setHandler("remote_position", function(asin, pos, mode, ts) {
                if (!app.book || app.book.asin !== asin) return
                if (mode === "apply") app.seekTo(pos)
                else app.proposal = { position_ms: pos, ts: ts }
            })
            setHandler("sync_error", function(msg) { app.lastSyncError = qsTranslate("backend", msg) })
            setHandler("pushed", function(asin, pos) { app.lastSyncError = "" })

            importModule("backend", function() {
                call("backend.init", [], function(r) {
                    app.version = r.version
                    app.missing = r.missing
                    app.loggedIn = r.logged_in
                    app.settings = r.settings
                    app.backendReady = true
                })
            })
        }
        onError: console.log("Python : " + traceback)
    }

    Component.onDestruction: {
        if (book && player.position > 0)
            py.call_sync("backend.push_now", [book.asin, player.position, totalMs()])
    }
}
