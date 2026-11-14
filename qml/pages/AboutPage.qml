import QtQuick 2.6
import Sailfish.Silica 1.0

Page {
    id: page

    readonly property var credits: [
        { name: "audible", role: qsTr("Access to the Audible API: sign-in, library, licenses, positions"),
          authors: "mkb79", license: "AGPL-3.0", url: "https://github.com/mkb79/Audible" },
        { name: "audible-cli", role: qsTr("Reference for license requests and downloads"),
          authors: "mkb79", license: "AGPL-3.0", url: "https://github.com/mkb79/audible-cli" },
        { name: "snowcrypt", role: qsTr("Decryption of AAX and AAXC files in Python"),
          authors: "snowskeleton", license: "Apache 2.0", url: "https://github.com/snowskeleton/snowcrypt" },
        { name: "PyOtherSide", role: qsTr("Bridge between the QML interface and the Python engine"),
          authors: "Thomas Perl", license: "ISC", url: "https://github.com/thp/pyotherside" },
        { name: "HTTPX", role: qsTr("Network requests"),
          authors: "Tom Christie, Encode", license: "BSD-3-Clause", url: "https://github.com/encode/httpx" },
        { name: "PyCryptodome", role: qsTr("Cryptographic functions"),
          authors: "Helder Eijs", license: "BSD-2-Clause", url: "https://www.pycryptodome.org" },
        { name: "Qt, Qt Multimedia", role: qsTr("Interface and audio playback"),
          authors: qsTr("The Qt Company and contributors"), license: "LGPL-3.0", url: "https://www.qt.io" },
        { name: "Sailfish Silica, WebView, Amber MPRIS", role: qsTr("Native Sailfish OS components"),
          authors: "Jolla", license: "", url: "https://sailfishos.org" }
    ]

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: col.height + Theme.paddingLarge

        Column {
            id: col
            width: parent.width
            spacing: Theme.paddingMedium

            PageHeader { title: qsTr("About") }

            Image {
                anchors.horizontalCenter: parent.horizontalCenter
                source: "/usr/share/icons/hicolor/172x172/apps/harbour-audiobook.png"
                width: Theme.iconSizeExtraLarge
                height: width
            }
            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Audiobook " + app.version
                color: Theme.highlightColor
                font.pixelSize: Theme.fontSizeLarge
            }
            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * x
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: Theme.fontSizeSmall
                text: qsTr("Native Audible client for Sailfish OS: library, downloads, player with chapters and listening position sync.")
            }

            SectionHeader { text: qsTr("Development") }
            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * x
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeSmall
                text: qsTr("Designed by Boris Solodki and developed with the assistance of Claude (Anthropic). Free software released under the AGPL-3.0 license.")
            }

            SectionHeader { text: qsTr("Tools and libraries") }
            Repeater {
                model: page.credits
                BackgroundItem {
                    width: col.width
                    height: entry.height + 2 * Theme.paddingSmall
                    onClicked: Qt.openUrlExternally(modelData.url)
                    Column {
                        id: entry
                        x: Theme.horizontalPageMargin
                        width: parent.width - 2 * x
                        anchors.verticalCenter: parent.verticalCenter
                        Label {
                            width: parent.width
                            text: modelData.name
                            color: highlighted ? Theme.highlightColor : Theme.primaryColor
                        }
                        Label {
                            width: parent.width
                            wrapMode: Text.Wrap
                            font.pixelSize: Theme.fontSizeExtraSmall
                            color: Theme.secondaryColor
                            text: modelData.role
                        }
                        Label {
                            width: parent.width
                            wrapMode: Text.Wrap
                            font.pixelSize: Theme.fontSizeExtraSmall
                            color: Theme.secondaryHighlightColor
                            text: modelData.authors
                                  + (modelData.license ? " · " + modelData.license : "")
                                  + " · " + modelData.url.replace("https://", "")
                        }
                    }
                }
            }

            SectionHeader { text: qsTr("Disclaimer") }
            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * x
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                text: qsTr("Unofficial app, not affiliated with Audible or Amazon. Audible is a trademark of Audible, Inc. The app only accesses books purchased on your own account.")
            }
        }
    }
}
