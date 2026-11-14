import QtQuick 2.6
import Amber.Mpris 1.0

// Commandes des ecouteurs, de l'ecran verrouille et des montres (MPRIS).
// Charge par un Loader : si le module Amber.Mpris manque, l'application
// fonctionne sans.
MprisPlayer {
    serviceName: "harbour-audiobook"
    identity: "Audiobook"
    supportedUriSchemes: ["file"]
    supportedMimeTypes: ["audio/mp4"]

    canControl: true
    canPlay: app.book !== null
    canPause: app.book !== null
    canGoNext: app.book !== null
    canGoPrevious: app.book !== null
    canSeek: false

    playbackStatus: app.playing ? Mpris.Playing : (app.book ? Mpris.Paused : Mpris.Stopped)

    metaData.title: app.book ? app.book.title : ""
    metaData.contributingArtist: app.book ? app.book.authors : ""
    metaData.albumTitle: app.chapterIndex >= 0 ? app.chapters[app.chapterIndex].title : ""
    // Couverture affichee sur l'ecran verrouille et dans les commandes multimedias.
    metaData.artUrl: !app.book || !app.book.cover ? ""
                     : (app.book.cover.indexOf("http") === 0 ? app.book.cover
                                                             : "file://" + app.book.cover)
    metaData.duration: app.totalMs()

    onPlayRequested: app.play()
    onPauseRequested: app.pause()
    onPlayPauseRequested: app.toggle()
    onStopRequested: app.pause()
    onNextRequested: app.skip(app.skipSeconds * 1000)
    onPreviousRequested: app.skip(-app.skipSeconds * 1000)
}
