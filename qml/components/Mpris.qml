import QtQuick 2.6
import Amber.Mpris 1.0

// Commandes des ecouteurs, de l'ecran verrouille et des montres (MPRIS).
// Charge par un Loader : si le module Amber.Mpris manque, l'application
// fonctionne sans.
MprisPlayer {
    id: mpris
    serviceName: "harbour-audiobook"
    identity: "Audiobook"
    // Permet aux telecommandes (ecran CarPlay de Sailplay notamment) de
    // reconnaitre l'application et de la relancer.
    desktopEntry: "harbour-audiobook"
    supportedUriSchemes: ["file"]
    supportedMimeTypes: ["audio/mp4"]

    canControl: true
    canPlay: app.book !== null
    canPause: app.book !== null
    canGoNext: app.book !== null
    canGoPrevious: app.book !== null
    canSeek: app.book !== null

    playbackStatus: app.playing ? Mpris.Playing : (app.book ? Mpris.Paused : Mpris.Stopped)

    metaData.title: app.book ? app.book.title : ""
    metaData.contributingArtist: app.book ? app.book.authors : ""
    metaData.albumTitle: app.chapterIndex >= 0 ? app.chapters[app.chapterIndex].title : ""
    // Fichier du livre : le service Sailplay y reconnait le livre en lecture
    // pour le signaler sur l'ecran de la voiture.
    metaData.url: app.book && app.book.path ? "file://" + encodeURI(app.book.path) : ""
    // Couverture affichee sur l'ecran verrouille et dans les commandes multimedias.
    metaData.artUrl: !app.book || !app.book.cover ? ""
                     : (app.book.cover.indexOf("http") === 0 ? app.book.cover
                                                             : "file://" + app.book.cover)
    // La voiture (Sailplay) et l'ecran verrouille travaillent sur le chapitre en
    // cours : duree et position sont celles du chapitre, et le changement de
    // chapitre remet la barre a zero. Sans chapitres, on retombe sur le livre.
    readonly property bool byChapter: app.chapters.length > 0 && app.chapterIndex >= 0
    readonly property real segStart: byChapter ? app.chapterStart(app.chapterIndex) : 0
    readonly property real segLength: byChapter ? app.chapterEnd(app.chapterIndex) - segStart
                                                : app.totalMs()
    function relative(absMs) {
        if (!byChapter) return absMs
        return Math.max(0, absMs - app.chapterStart(app.chapterAt(absMs)))
    }

    metaData.duration: segLength

    // Position en millisecondes (Amber convertit pour D-Bus), lue a la demande.
    onPositionRequested: position = Math.max(0, app.positionMs() - segStart)
    onSeekRequested: {
        var target = Math.max(0, app.positionMs() + offset)
        app.seekTo(target)
        mpris.seeked(relative(target))
    }
    onSetPositionRequested: {
        var target = segStart + Math.max(0, Math.min(position, segLength))
        app.seekTo(target)
        mpris.seeked(relative(target))
    }

    // « Ouvrir ce fichier » : utilise par le service Sailplay quand on choisit
    // un livre sur l'ecran de la voiture (bouton Parcourir).
    onOpenUriRequested: {
        var name = ("" + uri).split("/").pop()
        if (name.slice(-4) === ".m4b") app.playFromRemote(decodeURIComponent(name.slice(0, -4)))
    }

    onPlayRequested: app.play()
    onPauseRequested: app.pause()
    onPlayPauseRequested: app.toggle()
    onStopRequested: app.pause()
    onNextRequested: app.skip(app.skipSeconds * 1000)
    onPreviousRequested: app.skip(-app.skipSeconds * 1000)
}
