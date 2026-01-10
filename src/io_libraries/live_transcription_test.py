import io
import queue
import requests
import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy.signal import resample_poly

SERVER_URL = "http://127.0.0.1:8080/inference"

CAPTURE_SR = 44100   # mic native
ASR_SR = 16000       # whisper requirement
CHANNELS = 1
CHUNK_SEC = 1.0

q = queue.Queue()

def cb(indata, frames, time, status):
    if status:
        print(status)
    q.put(indata.copy())

def to_16k(audio_44k):
    return resample_poly(audio_44k, ASR_SR, CAPTURE_SR).astype(np.int16)

def send_chunk(audio_16k):
    buf = io.BytesIO()
    sf.write(buf, audio_16k, ASR_SR, format="WAV", subtype="PCM_16")
    buf.seek(0)
    r = requests.post(SERVER_URL, files={"file": buf}, timeout=30)
    r.raise_for_status()
    return r.json()

print("Starting live ASR. Speak a short command, then pause.")
print("Ctrl+C to stop.\n")

frames_per_chunk = int(CAPTURE_SR * CHUNK_SEC)

with sd.InputStream(
    samplerate=CAPTURE_SR,
    channels=CHANNELS,
    dtype="int16",
    callback=cb
):
    carry = np.zeros((0, CHANNELS), dtype=np.int16)

    while True:
        block = q.get()
        audio = np.concatenate([carry, block], axis=0)

        while audio.shape[0] >= frames_per_chunk:
            chunk_44k = audio[:frames_per_chunk]
            audio = audio[frames_per_chunk:]

            chunk_16k = to_16k(chunk_44k)

            out = send_chunk(chunk_16k)
            text = (out.get("text") or "").strip()
            if text:
                print("ASR:", text)

        carry = audio