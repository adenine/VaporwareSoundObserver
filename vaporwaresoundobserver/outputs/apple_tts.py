import subprocess


def speak(text: str):
    """Speak text aloud via macOS's built-in `say` command.

    Fire-and-forget: each call spawns its own process, so overlapping
    requests will overlap audio rather than queue.
    """
    text = text.strip()
    if not text:
        return
    subprocess.Popen(["say", text])
