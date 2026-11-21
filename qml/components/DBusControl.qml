import QtQuick 2.6
import Nemo.DBus 2.0

// Nom D-Bus de l'application (<organisation>.<application>, autorise par
// Sailjail). Il sert a Sailplay pour demarrer l'application depuis la voiture
// (activation D-Bus). Le livre choisi arrive, lui, par MPRIS (OpenUri).
// Charge par un Loader : si Nemo.DBus manque, l'application fonctionne sans.
DBusAdaptor {
    bus: DBus.SessionBus
    service: "org.solboki.harbour-audiobook"
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
