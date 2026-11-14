import QtQuick 2.6
import Sailfish.Silica 1.0

Page {
    SilicaListView {
        id: list
        anchors.fill: parent
        model: app.chapters
        header: PageHeader { title: qsTr("Chapters") }
        Component.onCompleted: positionViewAtIndex(Math.max(0, app.chapterIndex), ListView.Center)

        delegate: ListItem {
            readonly property bool current: index === app.chapterIndex
            contentHeight: Theme.itemSizeSmall
            onClicked: {
                app.seekTo(modelData.start_ms)
                if (!app.playing) app.play()
                pageStack.pop()
            }
            Label {
                anchors {
                    left: parent.left; leftMargin: Theme.horizontalPageMargin
                                                   + modelData.depth * Theme.paddingLarge
                    right: dur.left; rightMargin: Theme.paddingMedium
                    verticalCenter: parent.verticalCenter
                }
                text: modelData.title
                truncationMode: TruncationMode.Fade
                color: current || highlighted ? Theme.highlightColor : Theme.primaryColor
                font.bold: current
            }
            Label {
                id: dur
                anchors {
                    right: parent.right; rightMargin: Theme.horizontalPageMargin
                    verticalCenter: parent.verticalCenter
                }
                text: app.fmt(modelData.length_ms)
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
            }
        }
        VerticalScrollDecorator { }
    }
}
