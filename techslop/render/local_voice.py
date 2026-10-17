"""Offline eSpeak NG narration with engine word events, not guessed word timing."""
from __future__ import annotations

import ctypes as C
from ctypes.util import find_library
import os
from pathlib import Path
import threading
import wave

_LOCK = threading.Lock()


class EventID(C.Union):
    _fields_ = [('number', C.c_int), ('name', C.c_char_p), ('string', C.c_char * 8)]


class Event(C.Structure):
    _fields_ = [('type', C.c_int), ('unique_identifier', C.c_uint), ('text_position', C.c_int),
                ('length', C.c_int), ('audio_position', C.c_int), ('sample', C.c_int),
                ('user_data', C.c_void_p), ('id', EventID)]


def synthesize_local(text: str, output: Path, *, voice: str = 'es-419', rate: int = 155) -> list[dict]:
    if not 100 <= rate <= 220:
        raise ValueError('Local speech rate must be 100–220 words/minute')
    library = os.environ.get('ESPEAK_LIBRARY_PATH') or find_library('espeak-ng')
    data_path = os.environ.get('ESPEAK_DATA_PATH')
    if not library:
        # Optional non-root installation used by this cloud machine.
        directory = Path('/workspace/.tools/espeak/root/usr/lib/x86_64-linux-gnu')
        if not (directory / 'libespeak-ng.so.1').exists():
            raise RuntimeError('eSpeak NG is unavailable; install espeak-ng or provide ESPEAK_LIBRARY_PATH')
        for dependency in ['libsonic.so.0', 'libpcaudio.so.0']:
            C.CDLL(str(directory / dependency), mode=C.RTLD_GLOBAL)
        library = str(directory / 'libespeak-ng.so.1')
        data_path = data_path or str(directory)
    pcm, events = [], []
    callback_type = C.CFUNCTYPE(C.c_int, C.POINTER(C.c_short), C.c_int, C.POINTER(Event))

    @callback_type
    def callback(samples, count, metadata):
        if samples and count:
            pcm.append(C.string_at(samples, count * 2))
        i = 0
        while metadata and metadata[i].type != 0:
            e = metadata[i]
            if e.type == 1:  # espeakEVENT_WORD
                word = text[max(0, e.text_position - 1):e.text_position - 1 + e.length].strip()
                if word:
                    events.append({'word': word, 'start': e.audio_position / 1000})
            i += 1
        return 0

    with _LOCK:
        engine = C.CDLL(library)
        engine.espeak_Initialize.argtypes = [C.c_int, C.c_int, C.c_char_p, C.c_int]
        sample_rate = engine.espeak_Initialize(2, 0, data_path.encode() if data_path else None, 0)
        if sample_rate <= 0:
            raise RuntimeError('Unable to initialize eSpeak data')
        try:
            engine.espeak_SetVoiceByName.argtypes = [C.c_char_p]
            if engine.espeak_SetVoiceByName(voice.encode()) != 0:
                raise ValueError('Requested local voice is unavailable')
            engine.espeak_SetParameter(1, rate, 0)
            engine.espeak_SetSynthCallback.argtypes = [callback_type]
            engine.espeak_SetSynthCallback(callback)
            encoded = text.encode('utf-8') + b'\0'
            engine.espeak_Synth.argtypes = [C.c_char_p, C.c_size_t, C.c_uint, C.c_int, C.c_uint, C.c_uint, C.POINTER(C.c_uint), C.c_void_p]
            identifier = C.c_uint()
            if engine.espeak_Synth(encoded, len(encoded), 0, 1, 0, 1, C.byref(identifier), None) != 0:
                raise RuntimeError('Local synthesis failed')
            engine.espeak_Synchronize()
        finally:
            engine.espeak_Terminate()
    audio = b''.join(pcm)
    if not audio or not events:
        raise RuntimeError('Local voice returned no PCM or word events')
    with wave.open(str(output), 'wb') as target:
        target.setparams((1, 2, sample_rate, 0, 'NONE', 'not compressed'))
        target.writeframes(audio)
    duration = len(audio) / 2 / sample_rate
    # End at the following engine event; final word ends with the measured PCM.
    for i, event in enumerate(events):
        end = events[i+1]['start'] if i+1 < len(events) else duration
        event['end'] = max(event['start'] + .001, min(end, duration))
    return events
