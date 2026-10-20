# Architecture

This document covers how Vaporware SoundObserver's pipeline, plugin interfaces, and UI
widgets fit together, and how to extend it with a new input or output engine.
For what the app does and how to run it, see the [top-level README](../README.md).

---

## Pipeline: dual-cadence, multi-source

`pipeline/pipeline.py`'s `Pipeline(QThread)` is the single background thread
that owns the mic and dispatches audio to whichever recognizers are enabled.
It runs two independent cadences off the same `run()` loop:

- **`STT_CHUNK_SECONDS = 8`** — drives VoiceBox STT and Apple Native STT.
  Phrase-level transcription needs several seconds of speech to be
  meaningful, so both STT engines share this longer window.
- **`YAMNET_CHUNK_SECONDS = 1`** — drives YAMNet. Ambient sound
  classification is designed around short (~1s) windows, so it runs on its
  own much faster cadence for a responsive-feeling Sounds feed.

Both cadences read from the same live mic stream but need independent
buffers — an 8s STT chunk and a 1s YAMNet window can't share one
clear-on-read buffer without one starving the other. `pipeline/microphone.py`'s
`Microphone` solves this with **named, independently-flushable buffers**:
the `sd.InputStream` callback appends each incoming block to every named
buffer, and `flush(name)` clears only that buffer. `Pipeline.run()` opens
`buffers=["stt", "yamnet"]` and flushes each on its own timer.

Within a chunk callback, enabled sources run **synchronously and
sequentially** (not fanned out to their own threads). This matches the
project's simplicity-first style — VoiceBox's network round trip, Apple's
on-device inference, and YAMNet's tflite inference all comfortably fit
inside their respective windows, so added concurrency wasn't worth the
complexity. A slow/hung source will delay the next chunk of *its own*
cadence, same as it always has for VoiceBox — not a new risk introduced by
adding more sources.

Two signals carry pipeline state out to the UI:

- **`source_activity(str)`** — emitted the instant a source is dispatched
  (e.g. `"voicebox"`, `"apple"`, `"yamnet"`), *before* the blocking call
  returns. `window.py` pulses that input's LED on this signal — the LED
  reflects "audio was sent to this engine," not "the engine returned a
  result." This keeps the LED honest about activity even when a chunk comes
  back empty (e.g. silence).
- **`audio_event(dict)`** — emitted on a successful result. Every payload
  carries `event` (`"SpeechTranscribed"` or `"SoundDetected"`), `mode`, and
  a `source` key identifying which engine produced it, plus the
  event-specific fields (`text`/`duration` or `label`/`confidence`).

Both STT and YAMNet dispatch are gated by the same Mode 1
(`PrivacyMode.ANONYMIZED_REALTIME`) check that VoiceBox transcription
always used — Modes 2/3 remain no-ops project-wide until speaker
diarization is built.

---

## Plugin interfaces

Adding a new recognition engine means implementing one of two small abstract
interfaces and wiring it into `Pipeline` + the Inputs column — nothing else
in the pipeline needs to change.

### `BaseTranscriber` (`pipeline/transcribers/base.py`)

```python
class BaseTranscriber(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes: bytes, filename: str, language: str | None = None) -> TranscriptionResult: ...
```

Takes WAV bytes, returns `TranscriptionResult(text, duration)` or `None`.
Existing implementations:
- `voicebox.py` — `POST /transcribe` to a local VoiceBox instance. Treats a
  response body missing the `text` field as still-downloading-the-model
  (VoiceBox can return 202), not a hard failure.
- `apple_native.py` — writes the chunk to a temp WAV file and runs it
  through `SFSpeechRecognizer` + `SFSpeechURLRecognitionRequest` with
  `requiresOnDeviceRecognition = True`. The Cocoa completion handler fires
  on a framework-owned queue, so a `threading.Event` blocks the calling
  (pipeline) thread until it arrives — this keeps the interface identical
  to VoiceBox's synchronous shape. Authorization
  (`SFSpeechRecognizer.requestAuthorization_`) is requested lazily on first
  use, which is what triggers macOS's one-time permission dialog.

### `BaseClassifier` (`pipeline/classifiers/base.py`)

```python
class BaseClassifier(ABC):
    @abstractmethod
    def classify(self, samples: np.ndarray, sample_rate: int) -> ClassificationResult | None: ...
```

Takes a raw waveform, returns `ClassificationResult(label, confidence)` or
`None`. `yamnet.py` is the only implementation: lazy-downloads the
MediaPipe-hosted YAMNet `.tflite` model (~4MB, raw-waveform input — no
manual mel-spectrogram step needed) and its class map CSV to
`~/.cache/vaporwaresoundobserver/yamnet/` on first use, loads it via
`ai_edge_litert.interpreter.Interpreter`, and filters results below a fixed
confidence floor (`CONFIDENCE_FLOOR = 0.3`) or matching `SILENCE_LABELS` so
ambient noise doesn't spam the Sounds feed.

### Adding a new input engine

1. Implement `BaseTranscriber` or `BaseClassifier`.
2. In `Pipeline`, add a `set_<name>(engine, enabled: bool)` setter (mirror
   `set_apple_stt`/`set_yamnet`) and dispatch it from `_process_stt_chunk`
   or a new cadence if it needs one.
3. In `window.py`, add an `IORow` to `_build_inputs_column`, wire its
   `toggled` signal to lazily construct the engine and call the new
   `Pipeline` setter, and add its name to the `source_activity` → LED
   lookup dict in `_on_source_activity`.
4. Add a persisted toggle property to `config/settings.py` (copy the
   `apple_stt_enabled` pattern) and read it as the `IORow`'s initial
   `checked` state.

### Adding a new output engine

Outputs aren't behind an abstract interface — each is just a
`speak(text, ...)` function in `outputs/` (see `apple_tts.py` for the
minimal shape, `voicebox_tts.py` for one with a network round trip). To add
one:

1. Write `outputs/<name>.py` with a `speak(text: str, ...)` function.
   If it does any network I/O, dispatch it from `window.py` on a plain
   `threading.Thread(daemon=True)` (see `_on_tts_requested`/
   `_voicebox_tts_worker`) — never block the Qt main thread. Report errors
   back via the `_tts_error` signal (thread-safe: Qt queues the signal
   delivery onto the main thread automatically).
2. Add an `IORow` to `_build_outputs_column`, a persisted toggle in
   `config/settings.py`, and a branch in `_on_tts_requested` that checks
   `row.is_on()` before dispatching and calls `row.pulse()` on dispatch.

---

## Widgets

Three small custom-painted widgets in `app/widgets/` do all the visual work
— no built-in Qt checkbox/indicator widgets are used for I/O rows, to keep
a consistent look:

- **`LedIndicator`** (`led_indicator.py`) — a `QPainter`-drawn circle with
  two modes on one widget: `set_state(color, lit)` for a steady state (used
  for MQTT/Spacebrew connection status), and `pulse(color, ms)` for a
  transient bright flash that reverts to whatever steady state was set
  before it (used for all the input/output/publish activity LEDs). Reusing
  one widget for both means an LED can show "connected" *and* flash on
  publish without two separate implementations.
- **`ToggleSwitch`** (`toggle_switch.py`) — an iOS-style animated on/off
  switch (`QPropertyAnimation` sliding the knob), used instead of a plain
  `QCheckBox`.
- **`IORow`** (`io_row.py`) — composes a label + `LedIndicator` +
  `ToggleSwitch` into one row. This is the unit every input, output, and
  publish-transport row in the UI is built from. `set_disabled_stub(tooltip)`
  greys out a row with no backend yet (used for the Song Generator output).

`LiveFeedWidget` (`live_feed.py`) is a small titled scrolling list — a
generalized version of the single flat event log the app originally had,
now instantiated twice (Segments, Sounds) so each category gets its own
feed in the Settings column.

`app/style.py` holds one QSS string applied once to the whole window
(`setStyleSheet`) rather than inline per-widget styling — the dark
theme, LED glow, and toggle colors all live in that one file.

---

## Settings persistence

`config/settings.py` wraps `QSettings("Vaporware", "VaporwareSoundObserver")`.
Every input/output/publish toggle is a boolean property following the same
pattern: a getter with a hardcoded default (chosen to match the
always-on-VoiceBox-STT behavior the app originally shipped with, so
existing installs don't silently change behavior) and a setter called from
the corresponding `IORow.toggled` handler in `window.py`. See the
**Persisted settings** table in the PR/commit history or grep
`config/settings.py` directly for the current key list — it's a flat list
of `@property`/`@x.setter` pairs, deliberately not abstracted further since
there are only a handful.
