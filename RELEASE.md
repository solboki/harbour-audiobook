## Audiobook 0.9.2

### New: packages for every Sailfish OS architecture

Audiobook is now built for the three Sailfish OS architectures. Pick the package matching `uname -m` on your device:

- `aarch64`: 64-bit ARM devices, such as the Jolla Phone;
- `armv7hl`: 32-bit ARM devices (`uname -m` shows `armv7l`);
- `i486`: Intel tablets.

The packages are now built automatically by GitHub Actions. The 32-bit packages have not yet been tested on a real device: your feedback is welcome.

### Reminder of the main features

Native Sailfish library, background download, player with chapters, speed and sleep timer, position sync with Audible, lock screen and headset controls, car screens through [Sailplay](https://github.com/0312birdzhang/harbour-sailplay) with the Browse button, Sailjail sandbox, interface in ten languages.

### Installation

```
devel-su pkcon install-local harbour-audiobook-0.9.2-1.<arch>.rpm
```

All the Python modules the app needs are bundled. Requires Sailfish OS 5.

Unofficial app, not affiliated with Audible or Amazon. Audible is a trademark of Audible, Inc.
