Name:       harbour-audiobook
Version:    0.7.8
Release:    1
Summary:    Audiobook, client natif pour Audible sur Sailfish OS
License:    AGPL-3.0-or-later
# Les modules Python embarques contiennent du code compile (pycryptodome).
BuildArch:  aarch64
AutoReqProv: no
%global debug_package %{nil}
%global __strip /bin/true
%global __os_install_post %{nil}
URL:        https://github.com/solboki/harbour-audiobook
Source0:    %{name}-%{version}.tar.gz
Requires:   sailfishsilica-qt5 >= 0.10.9
Requires:   libsailfishapp-launcher
Requires:   pyotherside-qml-plugin-python3-qt5 >= 1.5
Requires:   qt5-qtdeclarative-import-multimedia
Requires:   python3-base
BuildRequires: qt5-qttools-linguist

%description
Client natif pour Audible : bibliotheque, telechargement, lecteur avec
chapitres et synchronisation de la position. Les modules Python necessaires
(audible, snowcrypt et leurs dependances) sont embarques.

%prep
%setup -q

%build
lrelease -silent translations/*.ts

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_datadir}/%{name}
cp -r qml python lib %{buildroot}%{_datadir}/%{name}/
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
