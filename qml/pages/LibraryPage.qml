import QtQuick 2.6
import Sailfish.Silica 1.0
import "../components"

Page {
    id: page
    property bool refreshing: false
    // au lancement, aller au lecteur si le reglage le demande
    property bool openPlayerOnStart: app.settings.start_page !== "library"
                                     && (app.settings.last_asin || "") !== ""

    function refresh() {
        refreshing = true
        app.lastSyncError = ""
        py.call("backend.library_refresh", [])
    }

    // Le lecteur est une page « attachee » : on y accede par un glissement
    // vers la gauche ou par l'indicateur en haut a droite de l'ecran.
    function ensurePlayerAttached() {
        if (status !== PageStatus.Active || !app.book) return
        if (!pageStack.nextPage(page))
            pageStack.pushAttached(Qt.resolvedUrl("PlayerPage.qml"))
        if (openPlayerOnStart) {
            openPlayerOnStart = false
            pageStack.navigateForward(PageStackAction.Immediate)
        }
    }

    function openPlayer(asin) {
        app.openBook(asin, true)
        if (pageStack.nextPage(page)) pageStack.navigateForward()
        else wantPlayer = true
    }
    property bool wantPlayer: false

    onStatusChanged: {
        if (status !== PageStatus.Active) return
        ensurePlayerAttached()
        if (app.storeVisited) {   // retour de la boutique : nouveaux achats possibles
            app.storeVisited = false
            refresh()
        }
    }
    Connections {
        target: app
        onBookChanged: {
            page.ensurePlayerAttached()
            if (page.wantPlayer && pageStack.nextPage(page)) {
                page.wantPlayer = false
                pageStack.navigateForward()
            }
        }
        onLastSyncErrorChanged: if (app.lastSyncError !== "") page.refreshing = false
    }
    Connections {
        target: app.library
        onCountChanged: page.refreshing = false
    }

    // La liste est reconstruite a chaque actualisation : si l'on etait en haut,
    // on y revient, en-tete compris, au lieu de rester un peu descendu.
    property bool wasAtTop: true
    function scrollToTop() { list.contentY = list.originY - list.topMargin }
    Connections {
        target: app
        onLibraryAboutToRebuild: page.wasAtTop = list.contentY - list.originY < Theme.itemSizeLarge
        onLibraryRebuilt: if (page.wasAtTop) Qt.callLater(page.scrollToTop)
    }

    Component.onCompleted: {
        py.call("backend.library_cached", [], function(items) {
            app.fillLibrary(items)
            // le dernier livre est charge (sans lecture) pour que le lecteur soit pret
            if (app.settings.last_asin) app.openBook(app.settings.last_asin, false)
            page.refresh()
        })
    }
    Timer {  // positions Audible des livres telecharges, une fois la liste chargee
        interval: 3000; running: true
        onTriggered: py.call("backend.sync_library_positions", [])
    }

    SilicaListView {
        id: list
        anchors.fill: parent
        model: app.library

        PullDownMenu {
            busy: page.refreshing
            MenuItem {
                text: qsTr("Settings")
                onClicked: pageStack.push(Qt.resolvedUrl("SettingsPage.qml"))
            }
            MenuItem {
                text: qsTr("Audible store")
                onClicked: app.openStore()
            }
            MenuItem {
                text: app.onlyDownloaded ? qsTr("Show whole library")
                                         : qsTr("Show books on the phone")
                onClicked: app.onlyDownloaded = !app.onlyDownloaded
            }
            MenuItem {
                text: qsTr("Refresh")
                onClicked: page.refresh()
            }
        }

        header: Column {
            width: list.width
            PageHeader {
                title: app.onlyDownloaded ? qsTr("On the phone") : qsTr("Library")
                description: qsTr("%1 titles").arg(app.library.count)
            }
            ComboBox {
                label: qsTr("Sort by")
                currentIndex: app.sortMode === "author" ? 1 : 0
                menu: ContextMenu {
                    MenuItem { text: qsTr("on the phone first") }
                    MenuItem { text: qsTr("author") }
                }
                onCurrentIndexChanged: {
                    var m = currentIndex === 1 ? "author" : "device"
                    if (m !== app.sortMode) app.updateSetting("sort_mode", m)
                }
            }
            SearchField {
                width: parent.width
                placeholderText: qsTr("Title, author or series")
                text: app.search
                onTextChanged: app.search = text
                EnterKey.onClicked: focus = false
            }
            Label {
                visible: app.lastSyncError !== ""
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * x
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.errorColor
                text: app.lastSyncError
            }
        }

        section {
            property: "section"
            criteria: ViewSection.FullString
            delegate: SectionHeader { text: section }
        }

        delegate: BookItem {
            onOpenRequested: page.openPlayer(model.asin)
        }

        ViewPlaceholder {
            enabled: app.library.count === 0 && !page.refreshing
            text: app.search !== "" ? qsTr("No results") : qsTr("Library is empty")
            hintText: app.search !== "" ? "" : qsTr("Pull down to refresh")
        }
        VerticalScrollDecorator { }
    }

    BusyIndicator {
        anchors.centerIn: parent
        size: BusyIndicatorSize.Large
        running: page.refreshing && app.library.count === 0
    }
}
