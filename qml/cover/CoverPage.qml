import QtQuick 2.6
import Sailfish.Silica 1.0

CoverBackground {
    Image {
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        opacity: 0.35
        source: app.book && app.book.cover
                ? (app.book.cover.indexOf("http") === 0 ? app.book.cover : "file://" + app.book.cover)
                : ""
    }

    Column {
        anchors {
            left: parent.left; right: parent.right
            margins: Theme.paddingLarge
            verticalCenter: parent.verticalCenter
        }
        spacing: Theme.paddingSmall
        Label {
            width: parent.width
            wrapMode: Text.Wrap
            maximumLineCount: 4
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
            text: app.book ? app.book.title : "Audiobook"
        }
        Label {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: Theme.fontSizeExtraSmall
            color: Theme.secondaryColor
            visible: app.book !== null
            text: app.book ? app.fmt(player.position) : ""
        }
        Label {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: Theme.fontSizeExtraSmall
            color: Theme.highlightColor
            visible: app.sleepMode !== 0
            text: app.sleepMode === -1 ? qsTr("end of chapter")
                                       : qsTr("stop in %1").arg(app.fmt(app.sleepRemaining * 1000))
        }
    }

    CoverActionList {
        enabled: app.book !== null
        CoverAction {
            iconSource: "image://theme/icon-cover-previous"
            onTriggered: app.skip(-app.skipSeconds * 1000)
        }
        CoverAction {
            iconSource: app.playing ? "image://theme/icon-cover-pause" : "image://theme/icon-cover-play"
            onTriggered: app.toggle()
        }
    }
}
