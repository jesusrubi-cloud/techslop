"""Exercise workflow setup only, with fake tools/APT; never execute synthesis."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest
import yaml

WORKFLOW = Path('.github/workflows/elevenlabs-manual-test.yml')


def workflow():
    return yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)


def setup_script():
    return next(step['run'] for step in workflow()['jobs']['test']['steps']
                if step.get('name') == 'Preparar y comprobar herramientas de audio')


def executable(path, text):
    path.write_text('#!/bin/bash\n' + text)
    path.chmod(0o755)


@pytest.mark.parametrize('missing', [(), ('ffmpeg',), ('ffprobe',), ('ffmpeg', 'ffprobe')])
def test_setup_installs_only_when_either_audio_tool_is_missing(tmp_path, missing):
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    executable(bin_dir / 'python3', 'echo "Python mock"\n')
    for tool in ['ffmpeg', 'ffprobe']:
        if tool not in missing:
            executable(bin_dir / tool, f'echo "{tool} mock version"\n')
    executable(bin_dir / 'sudo', '''
printf '%s\n' "$*" >> "$APT_LOG"
if [[ "$1" == apt-get && "$2" == install ]]; then
  for tool in ffmpeg ffprobe; do
    printf '%s\n' '#!/bin/bash' 'echo "installed mock version"' > "$FAKE_BIN/$tool"
    /bin/chmod +x "$FAKE_BIN/$tool"
  done
fi
''')
    log = tmp_path / 'apt.log'
    env = {**os.environ, 'PATH': str(bin_dir), 'FAKE_BIN': str(bin_dir), 'APT_LOG': str(log)}
    result = subprocess.run(['/bin/bash', '-c', setup_script()], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'ffmpeg:' in result.stdout and 'ffprobe:' in result.stdout
    assert 'version' in result.stdout
    for tool in ['ffmpeg', 'ffprobe']:
        if tool in missing:
            assert f'Herramienta ausente: {tool}' in result.stdout
        else:
            assert f'Herramienta disponible: {tool}' in result.stdout
    if missing:
        assert log.read_text().splitlines() == ['apt-get update', 'apt-get install --yes --no-install-recommends ffmpeg']
    else:
        assert not log.exists()


def test_package_failure_stops_setup(tmp_path):
    executable(tmp_path / 'python3', 'echo "Python mock"\n')
    executable(tmp_path / 'sudo', 'echo "mock APT failure" >&2\nexit 42\n')
    result = subprocess.run(['/bin/bash', '-c', setup_script()], env={**os.environ, 'PATH': str(tmp_path)}, capture_output=True, text=True)
    assert result.returncode == 42
    assert 'mock APT failure' in result.stderr


def test_manual_authorization_and_secret_scope_preserved():
    parsed = workflow()
    assert set(parsed['on']) == {'workflow_dispatch'}
    assert parsed['on']['workflow_dispatch']['inputs']['authorize_one_request']['default'] == 'false'
    job = parsed['jobs']['test']
    assert job['if'] == '${{ inputs.authorize_one_request == true }}'
    secret_steps = [s for s in job['steps'] if 'ELEVENLABS_API_KEY' in s.get('env', {})]
    assert len(secret_steps) == 1
    assert secret_steps[0]['env']['ELEVENLABS_API_KEY'] == '${{ secrets.ELEVENLABS_API_KEY }}'
    assert 'elevenlabs_manual_test.py' in secret_steps[0]['run']
    assert 'ELEVENLABS' not in setup_script()


def test_voice_id_is_still_a_fresh_manual_input():
    parsed = workflow()
    voice = parsed['on']['workflow_dispatch']['inputs']['voice_id']
    assert voice['required'] == 'true'
    assert voice['type'] == 'string'
    generation = next(step for step in parsed['jobs']['test']['steps']
                      if 'ELEVENLABS_API_KEY' in step.get('env', {}))
    assert generation['env']['VOICE_ID'] == '${{ inputs.voice_id }}'
    assert '--voice-id "$VOICE_ID"' in generation['run']
