import QtQuick 2.6
import Sailfish.Silica 1.0

Page {
    id: page
    readonly property var skips: [10, 15, 30, 45, 60]

    RemorsePopup { id: remorse }

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: col.height + Theme.paddingLarge

        Column {
            id: col
            width: parent.width

            PageHeader { title: qsTr("Settings") }

            TextSwitch {
                text: qsTr("Sync position with Audible")
                description: qsTr("Sends the position on pause, every minute while listening and on exit. Offers the position from another device when it is more recent.")
                checked: app.settings.sync_enabled
                onClicked: app.updateSetting("sync_enabled", checked)
            }

            ComboBox {
                label: qsTr("On startup")
                description: qsTr("The player opens the last book you listened to.")
                currentIndex: app.settings.start_page === "library" ? 1 : 0
                menu: ContextMenu {
                    MenuItem { text: qsTr("player") }
                    MenuItem { text: qsTr("library") }
                }
                onCurrentIndexChanged: {
                    var v = currentIndex === 1 ? "library" : "player"
                    if (v !== app.settings.start_page) app.updateSetting("start_page", v)
                }
            }

            ComboBox {
                label: qsTr("Skip forward and back")
                currentIndex: Math.max(0, page.skips.indexOf(app.skipSeconds))
                menu: ContextMenu {
                    Repeater {
                        model: page.skips
                        MenuItem { text: qsTr("%1 s").arg(modelData) }
                    }
                }
                onCurrentIndexChanged: {
                    var v = page.skips[currentIndex]
                    if (v !== app.skipSeconds) app.updateSetting("skip_seconds", v)
                }
            }

            ComboBox {
                label: qsTr("Audible store")
                description: qsTr("The built-in browser keeps your Amazon sign-in separate for this app.")
                currentIndex: app.settings.browser === "external" ? 1 : 0
                menu: ContextMenu {
                    MenuItem { text: qsTr("built-in browser") }
                    MenuItem { text: qsTr("system browser") }
                }
                onCurrentIndexChanged: {
                    var v = currentIndex === 1 ? "external" : "internal"
                    if (v !== app.settings.browser) app.updateSetting("browser", v)
                }
            }

            SectionHeader { text: qsTr("Account") }

            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * x
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeSmall
                color: Theme.secondaryColor
                text: qsTr("Books are saved in Music/Audible. Signing out removes this device from your Audible account without deleting the books.")
            }
            Item { width: 1; height: Theme.paddingLarge }
            Button {
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Sign out")
                onClicked: remorse.execute(qsTr("Signing out"), function() {
                    py.call("backend.logout", [], function() {
                        app.loggedIn = false
                        app.library.clear()
                        pageStack.clear()
                        pageStack.push(Qt.resolvedUrl("LoginPage.qml"))
                    })
                })
            }

            SectionHeader { text: qsTr("Information") }
            Button {
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("About")
                onClicked: pageStack.push(Qt.resolvedUrl("AboutPage.qml"))
            }
        }
    }
}
