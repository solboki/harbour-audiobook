import QtQuick 2.6
import Sailfish.Silica 1.0
import "../components"

Page {
    id: page

    readonly property var speeds: [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.75, 2.0]
    readonly property var sleeps: [0, 15, 30, 45, 60, 90, -1]

    property int chapStart: app.chapterStart(app.chapterIndex)
    property int chapEnd: app.chapterEnd(app.chapterIndex)
    property int chapLen: Math.max(1, chapEnd - chapStart)

    function speedLabel(v) { return ("" + v).replace(".", Qt.locale().decimalPoint) + " ×" }

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: col.height + Theme.paddingLarge

        PullDownMenu {
            MenuItem {
                text: qsTr("Settings")
                onClicked: pageStack.push(Qt.resolvedUrl("SettingsPage.qml"))
            }
            MenuItem {
                text: qsTr("Chapters")
                enabled: app.chapters.length > 0
                onClicked: pageStack.push(Qt.resolvedUrl("ChaptersPage.qml"))
            }
        }

        Column {
            id: col
            width: parent.width
            spacing: Theme.paddingMedium

            PageHeader {
                title: app.book ? app.book.title : ""
                description: app.book ? app.book.authors : ""
            }

            Image {
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.min(parent.width - 4 * Theme.horizontalPageMargin,
                                page.height * 0.38)
                height: width
                fillMode: Image.PreserveAspectFit
                source: app.book && app.book.cover
                        ? (app.book.cover.indexOf("http") === 0 ? app.book.cover
                                                                : "file://" + app.book.cover) : ""
                sourceSize.width: width
            }

            // position proposee par Audible
            Rectangle {
                visible: app.proposal !== null
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * x
                height: visible ? propCol.height + 2 * Theme.paddingMedium : 0
                radius: Theme.paddingSmall
                color: Theme.rgba(Theme.highlightBackgroundColor, 0.25)
                Column {
                    id: propCol
                    anchors.centerIn: parent
                    width: parent.width - 2 * Theme.paddingMedium
                    spacing: Theme.paddingSmall
                    Label {
                        width: parent.width
                        wrapMode: Text.Wrap
                        font.pixelSize: Theme.fontSizeSmall
                        text: app.proposal
                              ? qsTr("Audible reports a more recent position: %1").arg(app.fmt(app.proposal.position_ms))
                                + (app.proposal.ts > 0 ? " (" + new Date(app.proposal.ts * 1000)
                                   .toLocaleString(Qt.locale(), Locale.ShortFormat) + ")" : "")
                              : ""
                    }
                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: Theme.paddingMedium
                        Button {
                            text: qsTr("Go there")
                            preferredWidth: Theme.buttonWidthExtraSmall
                            onClicked: { app.seekTo(app.proposal.position_ms); app.proposal = null }
                        }
                        Button {
                            text: qsTr("Ignore")
                            preferredWidth: Theme.buttonWidthExtraSmall
                            onClicked: app.proposal = null
                        }
                    }
                }
            }

            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * x
                horizontalAlignment: Text.AlignHCenter
                truncationMode: TruncationMode.Fade
                color: Theme.highlightColor
                text: app.chapterIndex >= 0 ? app.chapters[app.chapterIndex].title : " "
            }

            Slider {
                id: slider
                width: parent.width
                minimumValue: 0
                maximumValue: page.chapLen
                valueText: app.fmt(value) + " / " + app.fmt(page.chapLen)
                onPressedChanged: if (!pressed) app.seekTo(page.chapStart + value)
                function sync() {
                    if (!pressed) value = Math.max(0, Math.min(page.chapLen,
                                                               player.position - page.chapStart))
                }
                Component.onCompleted: sync()
                Connections {
                    target: player
                    onPositionChanged: slider.sync()
                }
            }

            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                text: {
                    var t = app.totalMs()
                    if (t <= 0) return " "
                    var rest = (t - player.position) / app.speed
                    return qsTr("%1 % · %2 left").arg(Math.round(100 * player.position / t)).arg(app.fmt(rest))
                           + (app.speed !== 1.0 ? qsTr(" at %1").arg(page.speedLabel(app.speed)) : "")
                }
            }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Theme.paddingMedium
                IconButton {
                    icon.source: "image://theme/icon-m-previous"
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: app.previousChapter()
                }
                SkipButton {
                    seconds: -app.skipSeconds
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: app.skip(-app.skipSeconds * 1000)
                }
                IconButton {
                    icon.source: app.playing ? "image://theme/icon-l-pause" : "image://theme/icon-l-play"
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: app.toggle()
                }
                SkipButton {
                    seconds: app.skipSeconds
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: app.skip(app.skipSeconds * 1000)
                }
                IconButton {
                    icon.source: "image://theme/icon-m-next"
                    anchors.verticalCenter: parent.verticalCenter
                    enabled: app.chapterIndex + 1 < app.chapters.length
                    onClicked: app.nextChapter()
                }
            }

            ComboBox {
                label: qsTr("Speed")
                currentIndex: Math.max(0, page.speeds.indexOf(app.speed))
                menu: ContextMenu {
                    Repeater {
                        model: page.speeds
                        MenuItem { text: page.speedLabel(modelData) }
                    }
                }
                onCurrentIndexChanged: {
                    var v = page.speeds[currentIndex]
                    if (v !== app.speed) app.updateSetting("speed", v)
                }
            }

            ComboBox {
                id: sleepBox
                label: qsTr("Sleep timer")
                currentIndex: 0
                menu: ContextMenu {
                    Repeater {
                        model: page.sleeps
                        MenuItem {
                            text: modelData === 0 ? qsTr("off")
                                  : modelData === -1 ? qsTr("end of chapter") : qsTr("%1 min").arg(modelData)
                            onClicked: app.setSleep(modelData)
                        }
                    }
                }
                Component.onCompleted: currentIndex = Math.max(0, page.sleeps.indexOf(app.sleepMode))
                Connections {
                    target: app
                    onSleepModeChanged: if (app.sleepMode === 0) sleepBox.currentIndex = 0
                }
            }

            Label {
                visible: app.sleepMode > 0
                anchors.horizontalCenter: parent.horizontalCenter
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                text: qsTr("Stops in %1").arg(app.fmt(app.sleepRemaining * 1000))
            }
        }
    }
}
