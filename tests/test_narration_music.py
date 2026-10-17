from __future__ import annotations

from array import array
from ctypes.util import find_library
import hashlib
import json
import math
from pathlib import Path
from unittest.mock import AsyncMock
import wave

import pytest

from scripts.create_demo_music import create_music
from techslop.editorial.script_format import validate_script
from techslop.render.audio import prepare_audio
from techslop.render.music import mix_with_ducking, validate_license
from techslop.render.local_voice import synthesize_local


def write_signal(path, duration=3, music=False):
    rate=24000
    data=array('h', (int(32767 * (.12 if music else .30) * math.sin(2*math.pi*(200 if music else 800)*i/rate))
                     if music or .4 <= i/rate < 1.4 else 0 for i in range(int(duration*rate))))
    with wave.open(str(path), 'wb') as target:
        target.setparams((1,2,rate,0,'NONE','not compressed'))
        target.writeframes(data.tobytes())


def license_for(path):
    target=path.with_suffix('.json')
    target.write_text(json.dumps({'title':'Test sine', 'author':'Unit test', 'source':'original generated signal',
                                 'license':'CC0-1.0','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}))
    return target


def projection(path, start, end, hz):
    with wave.open(str(path),'rb') as source:
        rate=source.getframerate()
        source.setpos(int(start*rate))
        data=array('h',source.readframes(int((end-start)*rate)))
        channels=source.getnchannels()
    data=data[::channels]
    a=sum(v*math.cos(2*math.pi*hz*i/rate) for i,v in enumerate(data))
    b=sum(v*math.sin(2*math.pi*hz*i/rate) for i,v in enumerate(data))
    return math.hypot(a,b)/len(data)


def test_music_ducking_reduces_background_during_speech(tmp_path):
    voice,music,out=[tmp_path/n for n in ['voice.wav','music.wav','mix.wav']]
    write_signal(voice)
    write_signal(music,music=True)
    report=mix_with_ducking(voice,music,license_for(music),out)
    during=projection(out,.8,1.2,200)
    after=projection(out,2,2.4,200)
    assert during < after * .7, (during,after)
    assert report['ducking']=='speech_sidechain'
    with wave.open(str(out),'rb') as source:
        assert source.getnframes()/source.getframerate()==pytest.approx(3,abs=.03)


def test_unlicensed_or_changed_music_is_rejected(tmp_path):
    music=tmp_path/'music.wav';write_signal(music,music=True)
    license_file=license_for(music)
    data=json.loads(license_file.read_text());data['license']='unknown'
    license_file.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='Music requires'):
        validate_license(music,license_file)
    license_file=license_for(music)
    music.write_bytes(music.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='hash'):
        validate_license(music,license_file)


def test_original_music_has_matching_cc0_metadata(tmp_path):
    path=tmp_path/'bed.wav'
    metadata=validate_license(path,create_music(path))
    assert metadata['license']=='CC0-1.0'


def load_demo():
    root=Path('examples/hybrid-demo')
    return validate_script(json.loads((root/'script.json').read_text()),json.loads((root/'dossier.json').read_text()))


def test_auto_edge_failure_falls_back_to_local_voice(tmp_path,monkeypatch):
    monkeypatch.setattr('techslop.render.audio._edge',AsyncMock(side_effect=ConnectionError('blocked')))
    def local(text,path,**kwargs):
        write_signal(path,duration=15)
        return [{'word':text.split()[0],'start':0,'end':1}]
    monkeypatch.setattr('techslop.render.local_voice.synthesize_local',local)
    paths,durations,words,mode,reason=prepare_audio(load_demo(),tmp_path,provider='auto')
    assert mode=='espeak_es_419'
    assert reason=='ConnectionError'
    assert sum(durations)==60
    assert all(p.name.startswith('local-voice-') for p in paths)


def test_paid_provider_is_rejected_without_api_call(tmp_path):
    with pytest.raises(ValueError,match='Paid providers'):
        prepare_audio(load_demo(),tmp_path,provider='openai')


def test_provided_audio_preserves_files_and_uses_config(tmp_path,monkeypatch):
    from techslop.config import settings
    external=tmp_path/'provided';external.mkdir()
    for i in range(4):write_signal(external/f'scene-{i+1}.wav',duration=15)
    before={p.name:p.read_bytes() for p in external.iterdir()}
    monkeypatch.setattr(settings,'narration_audio_dir',str(external))
    paths,durations,words,mode,_=prepare_audio(load_demo(),tmp_path/'output',provider='provided')
    assert mode=='provided_voice'
    assert sum(durations)==60
    assert {p.name:p.read_bytes() for p in external.iterdir()}==before


@pytest.mark.skipif(not (find_library('espeak-ng') or Path('/workspace/.tools/espeak/root/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1').exists()),reason='Optional eSpeak NG not installed')
def test_actual_local_speech_returns_spanish_word_events(tmp_path):
    output=tmp_path/'voice.wav'
    events=synthesize_local('Hola México. Narración y sincronización.',output)
    assert [e['word'] for e in events]==['Hola','México','Narración','y','sincronización']
    assert all(0<=e['start']<e['end'] for e in events)
    assert all(a['start']<=b['start'] for a,b in zip(events,events[1:]))
    assert output.stat().st_size>1000
