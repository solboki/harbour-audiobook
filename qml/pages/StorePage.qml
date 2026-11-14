import QtQuick 2.6
import Sailfish.Silica 1.0
import Sailfish.WebView 1.0

// Boutique Audible dans le navigateur integre de Sailfish (moteur Gecko).
WebViewPage {
    id: page
    property string startUrl: ""
    allowedOrientations: Orientation.All

    Component.onDestruction: app.storeVisited = true   // actualiser la bibliotheque au retour

    WebView {
        id: web
        anchors {
            top: toolbar.bottom; left: parent.left; right: parent.right
            bottom: parent.bottom
        }
        z: -1
        url: page.startUrl
    }

    ProgressBar {   // chargement, tout en bas de l'ecran
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        visible: web.loading
        indeterminate: true
        leftMargin: 0; rightMargin: 0
        height: Theme.paddingSmall
    }

    // Barre du haut. La fleche de Sailfish (fermer la page) reste en haut a
    // gauche ; nos boutons sont sous l'encoche, repartis sur toute la largeur.
    Rectangle {
        id: toolbar
        anchors { left: parent.left; right: parent.right; top: parent.top }
        // Hauteur de l'encoche fournie par Sailfish ; marge fixe si elle est inconnue.
        readonly property real cutout: {
            try { return Screen.topCutout.height || 0 } catch (e) { return 0 }
        }
        height: Theme.itemSizeSmall + (cutout > 0 ? cutout : Theme.paddingLarge * 2)
        color: Theme.rgba(Theme.overlayBackgroundColor, 0.9)

        Row {   // sous l'encoche, boutons repartis a parts egales sur la largeur
            readonly property int count: 4
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: Theme.itemSizeSmall
            IconButton {
                width: parent.width / parent.count; height: parent.height
                icon.source: "image://theme/icon-m-back"
                enabled: web.canGoBack
                onClicked: web.goBack()
            }
            IconButton {
                width: parent.width / parent.count; height: parent.height
                icon.source: "image://theme/icon-m-forward"
                enabled: web.canGoForward
                onClicked: web.goForward()
            }
            IconButton {
                width: parent.width / parent.count; height: parent.height
                icon.source: "image://theme/icon-m-refresh"
                onClicked: web.reload()
            }
            IconButton {   // ouvrir la meme page dans le navigateur du systeme
                width: parent.width / parent.count; height: parent.height
                icon.source: "image://theme/icon-m-website"
                onClicked: Qt.openUrlExternally(web.url)
            }
        }
    }
}
