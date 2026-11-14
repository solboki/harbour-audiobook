import QtQuick 2.6
import Sailfish.Silica 1.0

Page {
    id: page

    function route() {
        if (!app.backendReady || app.missing !== "") return
        pageStack.replace(Qt.resolvedUrl(app.loggedIn ? "LibraryPage.qml" : "LoginPage.qml"),
                          {}, PageStackAction.Immediate)
    }
    Connections { target: app; onBackendReadyChanged: route() }
    onStatusChanged: if (status === PageStatus.Active) route()

    BusyIndicator {
        anchors.centerIn: parent
        size: BusyIndicatorSize.Large
        running: !app.backendReady
    }

    SilicaFlickable {
        anchors.fill: parent
        ViewPlaceholder {
        enabled: app.backendReady && app.missing !== ""
        text: qsTr("Missing Python modules")
        hintText: qsTr("Install them from a terminal:") + "\n"
                  + "python3 -m pip install --user audible snowcrypt\n\n(" + app.missing + ")"
        }
    }
}
