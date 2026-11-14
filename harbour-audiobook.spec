Name:       harbour-audiobook
Version:    0.6.0
Release:    1
Summary:    Audiobook, client natif pour Audible sur Sailfish OS
License:    AGPL-3.0-or-later
BuildArch:  noarch
URL:        https://github.com/solboki/harbour-audiobook
Source0:    %{name}-%{version}.tar.gz
Requires:   sailfishsilica-qt5 >= 0.10.9
Requires:   libsailfishapp-launcher
Requires:   pyotherside-qml-plugin-python3-qt5 >= 1.5
Requires:   qt5-qtdeclarative-import-multimedia
Requires:   python3-base
BuildRequires: qt5-qttools-linguist

%description
Bibliotheque Audible, telechargement, lecteur avec chapitres et
synchronisation de la position. Necessite les modules Python audible et
snowcrypt (python3 -m pip install --user audible snowcrypt).

%prep
%setup -q

%build
lrelease -silent translations/*.ts

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_datadir}/%{name}
cp -r qml python %{buildroot}%{_datadir}/%{name}/
mkdir -p %{buildroot}%{_datadir}/%{name}/translations
cp translations/*.qm %{buildroot}%{_datadir}/%{name}/translations/
install -D -m 644 %{name}.desktop %{buildroot}%{_datadir}/applications/%{name}.desktop
for s in 86x86 108x108 128x128 172x172 256x256; do
  install -D -m 644 icons/$s/%{name}.png %{buildroot}%{_datadir}/icons/hicolor/$s/apps/%{name}.png
done

%files
%{_datadir}/%{name}
%{_datadir}/applications/%{name}.desktop
%{_datadir}/icons/hicolor/*/apps/%{name}.png
