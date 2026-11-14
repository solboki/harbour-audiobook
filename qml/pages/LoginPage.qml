import QtQuick 2.6
import Sailfish.Silica 1.0

Page {
    id: page
    property string loginUrl: ""
    property bool waiting: false
    property bool manual: false        // methode de secours : navigateur externe
    property string error: ""

    readonly property var locales: [
        { code: "fr", name: qsTr("France") + " (audible.fr)" },
        { code: "de", name: qsTr("Germany") + " (audible.de)" },
        { code: "uk", name: qsTr("United Kingdom") + " (audible.co.uk)" },
        { code: "us", name: qsTr("United States") + " (audible.com)" },
        { code: "ca", name: qsTr("Canada") + " (audible.ca)" },
        { code: "it", name: qsTr("Italy") + " (audible.it)" },
        { code: "es", name: qsTr("Spain") + " (audible.es)" },
        { code: "au", name: qsTr("Australia") + " (audible.com.au)" }
    ]

    Component.onCompleted: {
        py.setHandler("login_done", function(r) {
            page.waiting = false
            if (r.ok) {
                app.loggedIn = true
                pageStack.replace(Qt.resolvedUrl("LibraryPage.qml"))
            } else {
                page.error = qsTranslate("backend", r.error)
                page.loginUrl = ""
            }
        })
    }

    // Prepare une session de connexion, puis l'execute.
    function start(then) {
        error = ""
        py.call("backend.login_start", [locales[localeBox.currentIndex].code], function(url) {
            page.loginUrl = url
            then(url)
        })
    }

    function finish(responseUrl) {
        error = ""
        py.call("backend.login_finish", [responseUrl], function(r) {
            if (r.ok) page.waiting = true
            else page.error = qsTranslate("backend", r.error)
        })
    }

    function loginInApp() {
        var c = Qt.createComponent(Qt.resolvedUrl("LoginWebPage.qml"))
        if (c.status !== Component.Ready) {
            console.log("Navigateur integre indisponible : " + c.errorString())
            manual = true
            error = qsTr("The built-in browser is not available. Use another browser.")
            return
        }
        start(function(url) {
            var p = pageStack.push(c, { loginUrl: url })
            p.codeReceived.connect(function(u) { page.finish(u) })
        })
    }

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: col.height + Theme.paddingLarge

        PullDownMenu {
            visible: !page.waiting
            MenuItem {
                text: page.manual ? qsTr("Sign in within the app")
                                  : qsTr("Sign in with another browser")
                onClicked: { page.manual = !page.manual; page.loginUrl = ""; page.error = "" }
            }
        }

        Column {
            id: col
            width: parent.width
            spacing: Theme.paddingLarge

            PageHeader { title: qsTr("Account sign-in") }

            Image {
                anchors.horizontalCenter: parent.horizontalCenter
                source: "/usr/share/icons/hicolor/256x256/apps/harbour-audiobook.png"
                width: Theme.iconSizeExtraLarge * 1.5
                height: width
                smooth: true
            }

            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * x
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: Theme.fontSizeLarge
                color: Theme.highlightColor
                text: qsTr("Welcome")
            }

            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * x
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: Theme.fontSizeSmall
                color: Theme.secondaryHighlightColor
                text: qsTr("Sign in with your Amazon or Audible account. The phone will be registered as a listening device, just like with the official app. Your password is only entered on Amazon's page: the app never sees it.")
            }

            ComboBox {
                id: localeBox
                label: qsTr("Store")
                enabled: !page.waiting && (!page.manual || page.loginUrl === "")
                menu: ContextMenu {
                    Repeater {
                        model: page.locales
                        MenuItem { text: modelData.name }
                    }
                }
            }

            // ---- connexion dans l'application (par defaut)
            Button {
                visible: !page.manual && !page.waiting
                anchors.horizontalCenter: parent.horizontalCenter
                preferredWidth: Theme.buttonWidthLarge
                text: qsTr("Sign in")
                onClicked: page.loginInApp()
            }

            // ---- methode de secours : navigateur externe et copier-coller
            Column {
                visible: page.manual && !page.waiting
                width: parent.width
                spacing: Theme.paddingMedium

                Button {
                    visible: page.loginUrl === ""
                    anchors.horizontalCenter: parent.horizontalCenter
                    preferredWidth: Theme.buttonWidthLarge
                    text: qsTr("Get the sign-in address")
                    onClicked: page.start(function(url) { })
                }

                SectionHeader { text: qsTr("1. Sign in"); visible: page.loginUrl !== "" }
                Label {
                    visible: page.loginUrl !== ""
                    x: Theme.horizontalPageMargin
                    width: parent.width - 2 * x
                    wrapMode: Text.Wrap
                    font.pixelSize: Theme.fontSizeSmall
                    text: qsTr("Open this address in a browser, on the phone or a computer, then sign in. You will end up on a “page not found”: this is expected.")
                }
                Row {
                    visible: page.loginUrl !== ""
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Theme.paddingMedium
                    Button { text: qsTr("Open"); onClicked: Qt.openUrlExternally(page.loginUrl) }
                    Button { text: qsTr("Copy"); onClicked: Clipboard.text = page.loginUrl }
                }

                SectionHeader { text: qsTr("2. Paste the final address"); visible: page.loginUrl !== "" }
                TextArea {
                    id: responseField
                    visible: page.loginUrl !== ""
                    width: parent.width
                    placeholderText: qsTr("Address of the “not found” page")
                    label: qsTr("Final address")
                    inputMethodHints: Qt.ImhUrlCharactersOnly | Qt.ImhNoPredictiveText
                }
                Row {
                    visible: page.loginUrl !== ""
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Theme.paddingMedium
                    Button { text: qsTr("Paste"); onClicked: responseField.text = Clipboard.text }
                    Button {
                        text: qsTr("Confirm")
                        enabled: responseField.text.length > 20
                        onClicked: page.finish(responseField.text)
                    }
                }
            }

            // ---- attente de l'enregistrement de l'appareil
            Column {
                visible: page.waiting
                width: parent.width
                spacing: Theme.paddingMedium
                BusyIndicator {
                    anchors.horizontalCenter: parent.horizontalCenter
                    size: BusyIndicatorSize.Medium
                    running: page.waiting
                }
                Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    font.pixelSize: Theme.fontSizeSmall
                    color: Theme.secondaryHighlightColor
                    text: qsTr("Registering the device…")
                }
            }

            Label {
                visible: page.error !== ""
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * x
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
                color: Theme.errorColor
                font.pixelSize: Theme.fontSizeSmall
                text: page.error
            }

            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * x
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                text: qsTr("Unofficial app, not affiliated with Audible or Amazon.")
            }
        }
    }
}
