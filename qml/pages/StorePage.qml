import QtQuick 2.6
import Sailfish.Silica 1.0
import Sailfish.WebView 1.0

// Boutique Audible dans le navigateur integre de Sailfish (moteur Gecko).
WebViewPage {
    id: page
    property string startUrl: ""
    allowedOrientations: Orientation.All
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

    ProgressBar {   // chargement, tout en bas de l'ecran
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        visible: web.loading
        indeterminate: true
        leftMargin: 0; rightMargin: 0
        height: Theme.paddingSmall
    }

    // Barre du haut : deux boutons aux extremites, de part et d'autre de l'encoche.
    Rectangle {
        id: toolbar
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: Theme.itemSizeSmall
        color: Theme.rgba(Theme.overlayBackgroundColor, 0.9)

        IconButton {   // page precedente du site, ou retour a l'application
            anchors { left: parent.left; leftMargin: Theme.paddingMedium; verticalCenter: parent.verticalCenter }
            icon.source: "image://theme/icon-m-back"
            onClicked: web.canGoBack ? web.goBack() : pageStack.pop()
        }
        IconButton {   // ouvrir la meme page dans le navigateur du systeme
            anchors { right: parent.right; rightMargin: Theme.paddingMedium; verticalCenter: parent.verticalCenter }
            icon.source: "image://theme/icon-m-website"
            onClicked: Qt.openUrlExternally(web.url)
        }
    }
}
