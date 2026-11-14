import QtQuick 2.6
import Sailfish.Silica 1.0
import Sailfish.WebView 1.0

// Boutique Audible dans le navigateur integre de Sailfish (moteur Gecko).
WebViewPage {
    id: page
    property string startUrl: ""
    allowedOrientations: Orientation.All
    // La fleche de retour de Sailfish (en haut a gauche) captait les appuis
    // destines aux menus des sites : on la retire, le bouton Fermer la remplace.
    backNavigation: false
    showNavigationIndicator: false

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

    ProgressBar {
        anchors { left: parent.left; right: parent.right; top: toolbar.bottom }
        visible: web.loading
        indeterminate: true
        leftMargin: 0; rightMargin: 0
        height: Theme.paddingSmall
    }

    Rectangle {
        id: toolbar
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: Theme.itemSizeSmall
        color: Theme.rgba(Theme.overlayBackgroundColor, 0.9)

        Row {
            anchors.centerIn: parent
            spacing: Theme.paddingLarge
            IconButton {
                icon.source: "image://theme/icon-m-close"
                onClicked: pageStack.pop()
            }
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
