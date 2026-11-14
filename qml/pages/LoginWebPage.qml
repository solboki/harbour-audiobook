import QtQuick 2.6
import Sailfish.Silica 1.0
import Sailfish.WebView 1.0

// Page de connexion Amazon dans le navigateur integre. Des que Amazon
// redirige vers l'adresse contenant le code d'autorisation, celle-ci est
// recuperee automatiquement : plus de copier-coller.
WebViewPage {
    id: page
    property string loginUrl: ""
    property bool captured: false
    signal codeReceived(string url)
    allowedOrientations: Orientation.All
    showNavigationIndicator: false

    WebView {
        id: web
        anchors {
            top: toolbar.bottom; left: parent.left; right: parent.right
            bottom: parent.bottom
        }
        z: -1
        url: page.loginUrl
        onUrlChanged: {
            var u = "" + url
            if (!page.captured && u.indexOf("openid.oa2.authorization_code") >= 0) {
                page.captured = true
                page.codeReceived(u)
                pageStack.pop()
            }
        }
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
    }
}
