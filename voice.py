"""
ARIA - Voice Module
Handles: Speech-to-Text (mic input) + Text-to-Speech (ARIA speaks back)
"""

import subprocess
import sys

def _pip(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ── TTS ───────────────────────────────────────────────────────────────────────
try:
    import pyttsx3
    _tts_available = True
except ImportError:
    try:
        _pip("pyttsx3==2.90")
        import pyttsx3
        _tts_available = True
    except Exception:
        _tts_available = False

# ── STT ───────────────────────────────────────────────────────────────────────
try:
    import speech_recognition as sr
    _stt_available = True
except ImportError:
    try:
        _pip("SpeechRecognition==3.10.0")
        import speech_recognition as sr
        _stt_available = True
    except Exception:
        _stt_available = False


# ── TTS ENGINE ────────────────────────────────────────────────────────────────
_engine = None

def _get_engine():
    global _engine
    if _tts_available and _engine is None:
        try:
            _engine = pyttsx3.init()
            _engine.setProperty("rate", 175)
            _engine.setProperty("volume", 0.9)
            # Try to set a female-sounding voice if available
            voices = _engine.getProperty("voices")
            for v in voices:
                if "zira" in v.name.lower() or "female" in v.name.lower() or "hazel" in v.name.lower():
                    _engine.setProperty("voice", v.id)
                    break
        except Exception:
            _engine = None
    return _engine


def speak(text):
    """ARIA speaks the response aloud."""
    engine = _get_engine()
    if engine:
        try:
            # Strip emoji for cleaner speech
            clean = ""
            for ch in text:
                if ord(ch) < 0x2500:
                    clean += ch
            engine.say(clean[:300])  # limit length
            engine.runAndWait()
        except Exception:
            pass  # Silent fail — TTS is optional


def listen():
    """
    Listen from microphone and return recognized text.
    Returns: (text: str, error: str|None)
    """
    if not _stt_available:
        return None, "SpeechRecognition not installed. Run install.bat"

    try:
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=6, phrase_time_limit=8)
        text = recognizer.recognize_google(audio)
        return text, None
    except sr.WaitTimeoutError:
        return None, "No speech detected (timeout)"
    except sr.UnknownValueError:
        return None, "Could not understand audio"
    except sr.RequestError as e:
        return None, f"Google STT error: {e}"
    except OSError:
        return None, "Microphone not found or PyAudio not installed"
    except Exception as e:
        return None, str(e)


def is_voice_available():
    return _stt_available and _tts_available
