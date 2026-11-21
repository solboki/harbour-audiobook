import QtQuick 2.6
import Nemo.Policy 1.0
import Sailfish.Media 1.0

// Boutons des ecouteurs (filaires ou Bluetooth). Sous Sailfish, une application
// doit reserver les boutons aupres du gestionnaire de ressources, en tant que
// lecteur, puis ecouter les touches multimedias. Les boutons « suivant » et
// « precedent » sautent en avant ou en arriere, comme dans la voiture.
// Charge par un Loader : si ces modules manquent, l'application fonctionne sans.
Item {
    Permissions {
        enabled: app.book !== null
        autoRelease: true
        applicationClass: "player"

        Resource {
            id: keysResource
            type: Resource.HeadsetButtons
            optional: true
        }
    }

    MediaKey {   // bouton unique des ecouteurs filaires
        enabled: keysResource.acquired
        key: Qt.Key_ToggleCallHangup
        onReleased: app.toggle()
    }
    MediaKey {
        enabled: keysResource.acquired
        key: Qt.Key_MediaTogglePlayPause
        onReleased: app.toggle()
    }
    MediaKey {
        enabled: keysResource.acquired
        key: Qt.Key_MediaPlay
        onReleased: app.play()
    }
    MediaKey {
        enabled: keysResource.acquired
        key: Qt.Key_MediaPause
        onReleased: app.pause()
    }
    MediaKey {
        enabled: keysResource.acquired
        key: Qt.Key_MediaStop
        onReleased: app.pause()
    }
    MediaKey {
        enabled: keysResource.acquired
        key: Qt.Key_MediaNext
        onReleased: app.skip(app.skipSeconds * 1000)
    }
    MediaKey {
        enabled: keysResource.acquired
        key: Qt.Key_MediaPrevious
        onReleased: app.skip(-app.skipSeconds * 1000)
    }
}
