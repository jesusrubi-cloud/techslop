from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import urllib.error

import pytest

from scripts import elevenlabs_manual_test as trial


class Response(io.BytesIO):
    def __init__(self, data, mime):
        super().__init__(data)
        self.headers = {'Content-Type': mime}


class FakeOpener:
    def __init__(self, audio=b'', accent='Mexican', fail=False):
        self.calls=[]
        self.audio=audio
        self.accent=accent
        self.fail=fail

    def open(self, request, timeout):
        self.calls.append(request)
        if request.get_method()=='GET':
            return Response(json.dumps({'labels':{'accent':self.accent,'language':'Spanish'}}).encode(),'application/json')
        if self.fail:
            raise urllib.error.URLError('simulated confidential upstream payload')
        return Response(self.audio,'audio/mpeg')


@pytest.fixture
def fake_key(monkeypatch):
    monkeypatch.setenv('ELEVENLABS_API_KEY','unit-test-placeholder-never-real')


def test_no_authorization_means_no_requests(tmp_path,fake_key):
    opener=FakeOpener()
    with pytest.raises(trial.TestError,match='authorization'):
        trial.execute(tmp_path/'out','test_voice_mexican',opener=opener)
    assert opener.calls==[]


def test_wrong_accent_means_no_generation(tmp_path,fake_key):
    opener=FakeOpener(accent='American')
    with pytest.raises(trial.TestError,match='not labelled Mexican'):
        trial.execute(tmp_path/'out','test_voice_mexican',approved=True,opener=opener)
    assert [r.get_method() for r in opener.calls]==['GET']


def test_character_budget_is_enforced_before_network(tmp_path,fake_key,monkeypatch):
    monkeypatch.setattr(trial,'TEXT','a'*81)
    opener=FakeOpener()
    with pytest.raises(trial.TestError,match='character budget'):
        trial.execute(tmp_path/'out','test_voice_mexican',approved=True,opener=opener)
    assert opener.calls==[]


def test_failed_generation_is_never_retried_or_logged(tmp_path,fake_key):
    opener=FakeOpener(fail=True)
    with pytest.raises(trial.TestError) as failure:
        trial.execute(tmp_path/'out','test_voice_mexican',approved=True,opener=opener)
    assert len([r for r in opener.calls if r.get_method()=='POST'])==1
    assert 'confidential' not in str(failure.value)
    with pytest.raises(trial.TestError,match='previous attempt'):
        trial.execute(tmp_path/'out','test_voice_mexican',approved=True,opener=opener)
    assert len(opener.calls)==2


def test_missing_secret_fails_without_network(tmp_path,monkeypatch):
    monkeypatch.delenv('ELEVENLABS_API_KEY',raising=False)
    opener=FakeOpener()
    with pytest.raises(trial.TestError,match='missing'):
        trial.execute(tmp_path/'out','test_voice_mexican',approved=True,opener=opener)
    assert opener.calls==[]


def test_simulated_long_response_is_capped_and_decoded_locally(tmp_path,fake_key):
    # Local sine wave only: no narration or paid-service request is generated.
    source=tmp_path/'synthetic.mp3'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=400:duration=16',str(source)],check=True)
    opener=FakeOpener(source.read_bytes())
    report=trial.execute(tmp_path/'out','test_voice_mexican',approved=True,opener=opener)
    assert [r.get_method() for r in opener.calls]==['GET','POST']
    request=json.loads(opener.calls[1].data)
    assert request['text']==trial.TEXT
    assert len(request['text'])<=80
    assert request['model_id']=='eleven_flash_v2_5'
    assert 0<report['output_duration_seconds']<=15
    assert report['generation_requests']==1
    assert report['publication_approved'] is False
    assert 'unit-test-placeholder' not in (tmp_path/'out/report.json').read_text()
    assert not (tmp_path/'out/source.mp3').exists()


def test_redirects_are_rejected():
    with pytest.raises(trial.TestError,match='redirects'):
        trial.NoRedirect().redirect_request(None,None,302,'found',{},'https://other.example')


@pytest.mark.asyncio
async def test_legacy_provider_cannot_bypass_manual_authorization(tmp_path):
    from techslop.voice.elevenlabs import ElevenLabsTTS
    with pytest.raises(PermissionError,match='manual Actions'):
        await ElevenLabsTTS(object()).synthesize_chunk('No generar',tmp_path/'not-created.mp3')
    assert not (tmp_path/'not-created.mp3').exists()
