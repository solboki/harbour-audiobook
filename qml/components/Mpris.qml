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
    // Couverture affichee sur l'ecran verrouille et dans les commandes multimedias.
    metaData.artUrl: !app.book || !app.book.cover ? ""
                     : (app.book.cover.indexOf("http") === 0 ? app.book.cover
                                                             : "file://" + app.book.cover)
    metaData.duration: app.totalMs()

    // Position dans le livre entier, en millisecondes (Amber convertit pour D-Bus).
    // Lue a la demande, sans signal a chaque seconde de lecture.
    onPositionRequested: position = app.positionMs()
    onSeekRequested: {
        app.seekTo(Math.max(0, app.positionMs() + offset))
        mpris.seeked(app.positionMs())
    }
    onSetPositionRequested: {
        app.seekTo(Math.max(0, Math.min(position, app.totalMs())))
        mpris.seeked(app.positionMs())
    }

    onPlayRequested: app.play()
    onPauseRequested: app.pause()
    onPlayPauseRequested: app.toggle()
    onStopRequested: app.pause()
    onNextRequested: app.skip(app.skipSeconds * 1000)
    onPreviousRequested: app.skip(-app.skipSeconds * 1000)
}
