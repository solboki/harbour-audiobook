import QtQuick 2.6
import Sailfish.Silica 1.0

// Ligne de la bibliotheque (utilisee comme delegue d'une liste).
ListItem {
    id: item
    signal openRequested()
    contentHeight: Theme.itemSizeExtraLarge
    menu: contextMenu

    function startDownload() { py.call("backend.download", [model.asin]) }

    onClicked: {
        if (model.downloaded) item.openRequested()
        else if (model.dlPhase === "") startDownload()
    }

    Image {
        id: coverImg
        x: Theme.horizontalPageMargin
        anchors.verticalCenter: parent.verticalCenter
        width: Theme.itemSizeLarge
        height: width
        fillMode: Image.PreserveAspectCrop
        source: model.cover ? (model.cover.indexOf("http") === 0 ? model.cover
                                                               : "file://" + model.cover) : ""
        asynchronous: true
        sourceSize.width: width
        sourceSize.height: height
        opacity: model.downloaded ? 1.0 : 0.6
        Rectangle {
            anchors.fill: parent
            color: Theme.rgba(Theme.highlightBackgroundColor, 0.2)
            visible: coverImg.status !== Image.Ready
        }
    }

    Column {
        anchors {
            left: coverImg.right; leftMargin: Theme.paddingLarge
            right: parent.right; rightMargin: Theme.horizontalPageMargin
            verticalCenter: parent.verticalCenter
        }
        Label {
            width: parent.width
            text: model.title
            truncationMode: TruncationMode.Fade
            color: item.highlighted || (app.book && app.book.asin === model.asin)
                   ? Theme.highlightColor : Theme.primaryColor
        }
        Label {
            width: parent.width
            text: app.sortMode === "author" && model.series !== "" ? model.series : model.authors
            truncationMode: TruncationMode.Fade
            font.pixelSize: Theme.fontSizeExtraSmall
            color: Theme.secondaryColor
        }
        Label {
            width: parent.width
            truncationMode: TruncationMode.Fade
            font.pixelSize: Theme.fontSizeExtraSmall
            color: model.dlPhase !== "" ? Theme.highlightColor : Theme.secondaryColor
            text: {
                if (model.dlPhase === "queued") return qsTr("Queued…")
                if (model.dlPhase === "license") return qsTr("Requesting license…")
                if (model.dlPhase === "download")
                    return qsTr("Downloading %1 %").arg(Math.round(model.dlFraction * 100))
                if (model.dlPhase === "decrypt")
                    return qsTr("Preparing %1 %").arg(Math.round(model.dlFraction * 100))
                var parts = [app.fmtDuration(model.runtime_min)]
                if (model.finished) parts.push(qsTr("finished"))
                else if (model.progress > 0.005)
                    parts.push(qsTr("%1 % listened").arg(Math.round(model.progress * 100)))
                if (app.sortMode === "author")
                    parts.push(model.downloaded ? qsTr("on the phone") : qsTr("to download"))
                return parts.join(" · ")
            }
        }
        Rectangle {   // barre de progression
            visible: model.progress > 0.005 || model.dlPhase !== ""
            width: parent.width
            height: Theme.paddingSmall / 2
            color: Theme.rgba(Theme.primaryColor, 0.15)
            Rectangle {
                height: parent.height
                color: Theme.highlightColor
                width: parent.width * (model.dlPhase !== "" ? model.dlFraction : model.progress)
            }
        }
    }

    Component {
        id: contextMenu
        ContextMenu {
            MenuItem {
                visible: !model.downloaded && model.dlPhase === ""
                text: qsTr("Download")
                onClicked: item.startDownload()
            }
            MenuItem {
                visible: model.dlPhase !== ""
                text: qsTr("Cancel download")
                onClicked: py.call("backend.cancel_download", [model.asin])
            }
            MenuItem {
                visible: model.downloaded
                enabled: !(app.book && app.book.asin === model.asin)
                text: qsTr("Delete from phone")
                onClicked: {
                    var asin = model.asin
                    item.remorseDelete(function() {
                        py.call("backend.delete_book", [asin], function() {
                            app.setItem(asin, { downloaded: false })
                        })
                    })
                }
            }
        }
    }
}
