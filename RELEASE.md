## Audiobook 0.9.3

### New: the whole library on the car screen, with covers, playback status and tabs

The Browse button of [Sailplay](https://github.com/0312birdzhang/harbour-sailplay) now lists the whole library, not only the books on the phone:

- touching a book that is not on the phone downloads it, then plays it; such books are marked with "↓", then "Downloading…";
- books on the phone always come first.

With a Sailplay that supports the experimental presentation hints of the Browse page, books are shown as large cards, easy to read and to pick while driving:

- tabs at the top: In progress, Downloaded, New, Authors, All (a tab only appears when it has something to show);
- one card per book with its cover, author and progress, and a badge for its playback status: not started, started, playing, finished;
- the book being played is highlighted, and the page follows playback and downloads;
- search covers titles, authors and series.

With other versions of Sailplay, the Browse button shows a simple list.

### Reminder of the main features

Native Sailfish library, background download, player with chapters, speed and sleep timer, position sync with Audible, lock screen and headset controls, car screens through Sailplay with the Browse button, Sailjail sandbox, interface in ten languages.

### Installation

```
devel-su pkcon install-local harbour-audiobook-0.9.3-1.<arch>.rpm
```

All the Python modules the app needs are bundled. Requires Sailfish OS 5. Packages are provided for `aarch64`, `armv7hl` and `i486`: pick the one matching `uname -m` on your device (`armv7l` means `armv7hl`).

Unofficial app, not affiliated with Audible or Amazon. Audible is a trademark of Audible, Inc.
