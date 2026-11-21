import QtQuick 2.6
import Nemo.DBus 2.0

// Point d'entree D-Bus de l'application, utilise par le service Sailplay
// (bouton « Parcourir » de l'ecran de la voiture) pour lancer un livre.
// Charge par un Loader : si Nemo.DBus manque, l'application fonctionne sans.
DBusAdaptor {
    bus: DBus.SessionBus
    service: "org.solboki.AudiobookApp"
    path: "/app"
    iface: "org.solboki.AudiobookApp"
    xml: '<interface name="org.solboki.AudiobookApp">\n'
         + '  <method name="playBook">\n'
         + '    <arg name="asin" type="s" direction="in"/>\n'
         + '    <arg name="accepted" type="b" direction="out"/>\n'
         + '  </method>\n'
         + '</interface>\n'

    function playBook(asin) {
        app.playFromRemote(asin)
        return true
    }
}
