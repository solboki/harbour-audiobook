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

    // Barre du haut. A gauche, la fleche de Sailfish (fermer la page) reste en
    // place ; nos boutons sont places de part et d'autre de l'encoche.
    Rectangle {
        id: toolbar
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: Theme.itemSizeSmall
        color: Theme.rgba(Theme.overlayBackgroundColor, 0.9)

        Row {   // avant l'encoche, apres la fleche de Sailfish
            anchors { left: parent.left; leftMargin: Theme.itemSizeMedium; verticalCenter: parent.verticalCenter }
            IconButton {
                icon.source: "image://theme/icon-m-back"
                enabled: web.canGoBack
                onClicked: web.goBack()
            }
            IconButton {
                icon.source: "image://theme/icon-m-forward"
                enabled: web.canGoForward
                onClicked: web.goForward()
            }
        }
        Row {   // apres l'encoche
            anchors { right: parent.right; rightMargin: Theme.paddingMedium; verticalCenter: parent.verticalCenter }
            IconButton {
                icon.source: "image://theme/icon-m-refresh"
                onClicked: web.reload()
            }
            IconButton {   // ouvrir la meme page dans le navigateur du systeme
                icon.source: "image://theme/icon-m-website"
                onClicked: Qt.openUrlExternally(web.url)
            }
        }
    }
}
