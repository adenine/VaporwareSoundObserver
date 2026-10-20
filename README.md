# Vaporware SoundObserver

The Vaporware SoundObserver helps you to observe speech and other audio events coming from people, objects, or your environment. Sibling project to [LifeObserver](../LifeObserver); same architecture, audio instead of vision.

Vaporware SoundObserver listens on a microphone, transcribes/classifies what it hears through several independently-switchable engines, and publishes structured events over MQTT and/or Spacebrew 2.0. It is designed for both prototyping and permanent installations.

---

## Interface

The app window is a control surface split into three columns:

| Column | Purpose |
|--------|---------|
| **Audio Observers** | One row per recognition engine — VoiceBox STT, Apple Native STT, YAMNet (sound). Each has its own on/off switch and an LED that pulses the instant a mic chunk is dispatched to it. |
| **Settings** | The Start/Stop Session button, Privacy Mode, MQTT/Spacebrew publish toggles (each with a steady connection-status LED plus a publish pulse), a live Words ticker, and Segments/Sounds feeds showing what's being recognized in real time. |
| **Audio Outputs** | One row per speech/audio output — Apple Native TTS, VoiceBox TTS, and a Song Generator placeholder. Each LED pulses when a message is dispatched to that engine. |

Inputs and outputs are independent — enabling more than one input at once (e.g. VoiceBox STT + Apple STT) runs them side by side on the same mic audio, each producing its own tagged events. All toggle states persist across restarts.

---

## Inputs

| Engine | What it does | Status |
|--------|---------------|--------|
| **VoiceBox STT** | Sends each ~8s mic chunk to a local [VoiceBox](https://voicebox.sh) instance's `/transcribe` endpoint. | Working |
| **Apple Native STT** | On-device transcription via macOS's `Speech.framework` (`SFSpeechRecognizer`, `requiresOnDeviceRecognition`). Same ~8s chunk cadence as VoiceBox. Triggers a one-time macOS "Speech Recognition" permission prompt on first use. | Working |
| **YAMNet (sound)** | Local ambient-sound classification via the MediaPipe-hosted YAMNet `.tflite` model, run through `ai-edge-litert`. Runs on a much shorter ~1s cadence (independent of the STT chunk timer) for responsive sound-event detection. The model (~4MB) and class map are downloaded once to `~/.cache/vaporwaresoundobserver/yamnet/` on first enable. | Working |

Transcripts and sound events are tagged with their source engine (e.g. `[apple]`, `[voicebox]`) in the Segments/Sounds feeds and in the `source` field of published MQTT payloads.

## Outputs

| Engine | What it does | Status |
|--------|---------------|--------|
| **Apple Native TTS** | Speaks text aloud via macOS's built-in `say` command. | Working |
| **VoiceBox TTS** | `POST /speak` to a local VoiceBox instance, polls `GET /generate/{id}/status` until generation completes, fetches the rendered audio from `GET /audio/{id}`, and plays it via `afplay`. Runs on a background thread so a slow round trip never blocks the UI. | Working |
| **Song Generator** | Placeholder row (disabled, "TBD — no backend yet"). No engine has been chosen yet. | Not started |

Outputs are triggered by an incoming `tts` message on the Spacebrew `VaporwareSoundObserver/tts` topic — every *enabled* output engine speaks it.

---

## Privacy Modes

Privacy is a first-class concern. The active mode is switchable live in the app — no restart required.

The three tiers are about **identity attribution**, not whether content is captured — transcription itself runs in Mode 1, with no speaker identity attached. Modes 2 and 3 layer on speaker recognition; they don't gate transcription.

| Mode | Name | Stores data | Identity |
|------|------|-------------|----------|
| 1 | Anonymized Realtime | No | None — transcript/sound-event content, no speaker identity |
| 2 | Anonymized Recognition | Voice-print embeddings only (no audio) | Anonymous speaker IDs persisted across sessions |
| 3 | Identified Recognition | Speaker name | Full named-speaker identity |

### Mode 1 — Anonymized Realtime
- `SpeechTranscribed` — full transcript text + duration, no speaker identity attached — **working**, via VoiceBox and/or Apple Native STT
- `SoundDetected` — label + confidence — **working**, via YAMNet

### Mode 2 — Anonymized Recognition
- All Mode 1 events, plus:
- `SpeakerEntered` / `SpeakerExited` — anonymous speaker ID (voice-print matched, no name) — **stub**

### Mode 3 — Identified Recognition
- All Mode 2 events, with a known name attached to the speaker ID instead of an anonymous one — **stub**

Modes 2 and 3 are not currently being built out; Mode 1 is the only tier with working recognition today. Default mode is Mode 1, so events publish as soon as a session is started — no mode switch required. All input recognizers (STT and YAMNet) are gated by this same Mode 1 check.

---

## MQTT

Vaporware SoundObserver is a **publisher only** — it connects to an external MQTT broker. The Settings column's "MQTT publish" switch gates whether events actually go out (independent of connection state, which is shown by the LED next to it). Topics follow the pattern:

```
<topic_base>/speech/transcribed
<topic_base>/sound/detected
<topic_base>/speaker/entered
<topic_base>/speaker/exited
```

Default topic base: `vaporwaresoundobserver`. Configurable via Settings.

Example payload (`vaporwaresoundobserver/speech/transcribed`):
```json
{
  "text": "Hello from Vaporware.",
  "duration": 4.16,
  "mode": 1
}
```

## Spacebrew 2.0

Vaporware SoundObserver also registers as a node on a [Spacebrew 2.0](https://github.com) router (itself just an MQTT client speaking a small registration protocol on top of the same broker). The Settings column's "Spacebrew 2.0 publish" switch gates outbound publishing the same way the MQTT switch does.

Publishes (`VaporwareSoundObserver/<name>`):
- `word` — one message per word, as transcripts come in
- `segments` — the full transcript per chunk
- `sound_detected` — YAMNet label + confidence

Subscribes:
- `tts` — text received here is spoken aloud via every *enabled* output engine (Apple Native TTS / VoiceBox TTS)

---

## Deployment Tiers

| Tier | Hardware | Modes |
|------|----------|-------|
| High performance | Laptop or NVIDIA Jetson Orin Nano | 1, 2, 3 |
| Edge | Raspberry Pi 4 or 5 | 1, 2 |
| MQTT client | ESP32 or Arduino (simple sound-level trigger) | Subscriber/actuator only |

---

## Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.9+ |
| UI | PyQt6 desktop window, custom-painted LED/toggle widgets, QSS dark theme |
| Capture | sounddevice (PortAudio) |
| Transcription | [VoiceBox](https://voicebox.sh) local REST API (`/transcribe`), and/or macOS `Speech.framework` on-device (`pyobjc-framework-Speech`) |
| Sound classification | YAMNet (`.tflite`, via `ai-edge-litert`) |
| Text-to-speech | macOS `say`, and/or VoiceBox's `/speak` REST flow |
| Speaker diarization — Mode 2 | TBD |
| Transport | paho-mqtt (publisher + Spacebrew 2.0 registration) |
| Config | QSettings (mic device, service URLs, privacy mode, all input/output toggle states) |

---

## Project Structure

```
vaporwaresoundobserver/
├── main.py                            # Entry point
├── app/
│   ├── window.py                      # MainWindow — 3-column layout, wiring
│   ├── style.py                       # QSS dark theme
│   ├── dialogs/
│   │   └── settings_dialog.py         # VoiceBox/MQTT/Spacebrew connection settings
│   └── widgets/
│       ├── led_indicator.py           # Custom-painted LED (steady state + pulse)
│       ├── toggle_switch.py           # iOS-style animated on/off switch
│       ├── io_row.py                  # label + LED + switch, one row per channel
│       └── live_feed.py               # Titled scrolling list (Segments/Sounds)
├── pipeline/
│   ├── pipeline.py                    # QThread orchestrator: dual-cadence mic → recognize → publish
│   ├── microphone.py                  # sounddevice capture, independently-flushable named buffers
│   ├── transcribers/
│   │   ├── base.py                    # Abstract transcriber interface
│   │   ├── voicebox.py                # VoiceBox /transcribe REST client
│   │   └── apple_native.py            # On-device SFSpeechRecognizer client
│   └── classifiers/
│       ├── base.py                    # Abstract classifier interface
│       └── yamnet.py                  # YAMNet tflite classifier (lazy model download)
├── outputs/
│   ├── apple_tts.py                   # `say`-based TTS
│   └── voicebox_tts.py                # VoiceBox /speak → poll → /audio → afplay
├── mqtt/
│   ├── client.py                      # paho-mqtt v2 client wrapper
│   └── events.py                      # JSON payload builders per event type
├── spacebrew/
│   ├── client.py                      # Spacebrew 2.0 registration + pub/sub wrapper
│   └── events.py                      # Spacebrew message name/value builders
├── privacy/
│   └── mode.py                        # PrivacyMode enum
└── config/
    └── settings.py                    # QSettings wrapper (all persisted app state)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the pipeline's concurrency model, the transcriber/classifier plugin interfaces, and how to add a new input or output engine.

---

## Running

Requires [VoiceBox](https://voicebox.sh) running locally (for VoiceBox STT/TTS) and an MQTT broker (e.g. `mosquitto`) reachable at the configured host/port. Apple Native STT/TTS and YAMNet have no external service dependency.

**Create the virtualenv outside iCloud Drive.** This project's source lives in an iCloud-synced folder, but if `.venv` is created here too, PyQt6 fails to start with `qt.qpa.plugin: Could not find the Qt platform plugin "cocoa"` — the plugin `.dylib` loads fine via a plain `dlopen`, but Qt's own plugin loader chokes on it under iCloud sync for reasons not fully diagnosed. Confirmed fix: put the venv anywhere outside `~/Library/Mobile Documents/`, e.g.:

```bash
python3 -m venv ~/.venvs/vaporwaresoundobserver
~/.venvs/vaporwaresoundobserver/bin/pip install -r requirements.txt
cd vaporwaresoundobserver
~/.venvs/vaporwaresoundobserver/bin/python main.py
```

On first run on macOS, the system will prompt for microphone access. Enabling Apple Native STT triggers a separate, one-time Speech Recognition permission prompt.

## Settings

Open **Vaporware SoundObserver → Settings…** to configure the VoiceBox URL, MQTT broker host/port, topic base, and Spacebrew broker host/port. These, along with every input/output toggle and the privacy mode, are saved automatically between sessions.

---

## Status

| Component | Status |
|-----------|--------|
| Mic capture, dual-cadence chunked buffering (8s STT / 1s YAMNet) | Working |
| VoiceBox STT, MQTT + Spacebrew publish | Working — verified live: real audio → VoiceBox transcript → published and received by an independent MQTT subscriber |
| Apple Native STT | Working — verified live: permission-prompt flow, then real on-device transcription of spoken audio |
| YAMNet ambient sound classification | Working — verified live: real-time classification of real sounds (speech, percussion, telephone ring, typing) at ~1s latency |
| Apple Native TTS | Working |
| VoiceBox TTS | Implemented against VoiceBox's live `/speak` → `/generate/{id}/status` → `/audio/{id}` contract; dispatches without error |
| Song Generator output | Not started — disabled stub row, no backend chosen yet |
| MQTT/Spacebrew publish toggles | Working — verified live with an independent MQTT subscriber that publishing stops/resumes exactly on toggle |
| Settings persistence (all toggles, privacy mode, connection settings) | Working — verified across a full app restart |
| Mode 2 — anonymous speaker diarization | Stub |
| Mode 3 — named speaker identification | Stub |

## History

This started as an embedded "Listen" panel inside [Vaporware](../Vaporware)'s admin prototype (browser-based mic capture via Web Audio, calling VoiceBox directly over HTTP). It was extracted into its own project to match the satellite-node Observer pattern used by [LifeObserver](../LifeObserver): Vaporware SoundObserver runs independently, on its own machine if needed, and publishes structured events over MQTT rather than being called directly by whatever consumes them. It later grew from a single VoiceBox-only transcriber into a multi-engine sensing panel — independently switchable STT/sound-classification inputs and TTS outputs, each publishable over MQTT and/or Spacebrew 2.0.
