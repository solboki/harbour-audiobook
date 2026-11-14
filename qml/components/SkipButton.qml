import QtQuick 2.6
import Sailfish.Silica 1.0

// Bouton rond « -30 » / « +30 »
BackgroundItem {
    id: root
    property int seconds: 30
    width: Theme.itemSizeMedium
    height: width

    Rectangle {
        anchors.centerIn: parent
        width: parent.width * 0.8
        height: width
        radius: width / 2
        color: "transparent"
        border.width: Math.max(2, Theme.paddingSmall / 3)
        border.color: root.highlighted ? Theme.highlightColor : Theme.primaryColor
        Label {
            anchors.centerIn: parent
            text: (root.seconds > 0 ? "+" : "−") + Math.abs(root.seconds)
            font.pixelSize: Theme.fontSizeSmall
            color: root.highlighted ? Theme.highlightColor : Theme.primaryColor
        }
    }
}
