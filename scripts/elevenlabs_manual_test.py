"""Explicit manual ElevenLabs test: fixed text, one generation, no retries or publication."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request

TEXT = 'Hola, México. Esta es una prueba breve de narración en español.'
MAX_CHARACTERS = 80
MAX_SECONDS = 15
MAX_BYTES = 2_000_000
MODEL = 'eleven_flash_v2_5'
BASE = 'https://api.elevenlabs.io'


class TestError(RuntimeError):
    """Safe diagnostic: never includes API response bodies, headers or credentials."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise TestError('API redirects are not allowed')


def normalize(value: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))


def request_bytes(opener, request, maximum: int) -> tuple[bytes, object]:
    try:
        with opener.open(request, timeout=45) as response:
            payload = response.read(maximum + 1)
            if len(payload) > maximum:
                raise TestError('API response exceeds the permitted size')
            return payload, response.headers
    except urllib.error.HTTPError as exc:
        raise TestError(f'ElevenLabs HTTP {exc.code}; no retry performed') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise TestError('Network failure; no retry performed. A generation may still have been charged.') from None


def execute(output: Path, voice_id: str, *, approved: bool = False, opener=None) -> dict:
    if not approved:
        raise TestError('Manual authorization for one generation is required')
    if not TEXT or len(TEXT) > MAX_CHARACTERS:
        raise TestError('Fixed text exceeds the character budget')
    if not re.fullmatch(r'[A-Za-z0-9_-]{10,64}', voice_id):
        raise TestError('A valid Mexican Spanish voice ID is required')
    key = os.environ.get('ELEVENLABS_API_KEY', '')
    if not key.strip():
        raise TestError('ELEVENLABS_API_KEY is missing or unavailable to this job')
    if output.exists() and any(output.iterdir()):
        raise TestError('Output must be empty; a previous attempt must not be retried automatically')
    output.mkdir(parents=True, exist_ok=True)
    # An exclusive marker prevents a second request in the same workspace.
    marker = output / 'attempt.json'
    with marker.open('x') as target:
        json.dump({'maximum_generation_requests': 1, 'maximum_characters': MAX_CHARACTERS,
                   'text_characters': len(TEXT), 'model': MODEL}, target)
    opener = opener or urllib.request.build_opener(NoRedirect())
    headers = {'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': 'application/json'}
    # Metadata lookup is not speech generation. Require a provider-labelled Mexican voice.
    payload, _ = request_bytes(opener, urllib.request.Request(f'{BASE}/v1/voices/{voice_id}', headers=headers), 200_000)
    try:
        voice = json.loads(payload)
        labels = voice.get('labels', {})
        accent = normalize(str(labels.get('accent', ''))).strip()
        language = normalize(str(labels.get('language', ''))).strip()
    except (ValueError, AttributeError, TypeError):
        raise TestError('Invalid voice metadata') from None
    if accent not in {'mexican', 'mexicano', 'mexicana', 'mexico', 'mexican spanish', 'es-mx'}:
        raise TestError('Voice is not labelled Mexican by ElevenLabs; no generation requested')
    if language and language not in {'es', 'es-mx', 'spanish', 'espanol', 'espanol mexicano'}:
        raise TestError('Voice language is not Spanish; no generation requested')
    body = json.dumps({'text': TEXT, 'model_id': MODEL, 'language_code': 'es',
                       'voice_settings': {'stability': .5, 'similarity_boost': .75, 'speed': 1.0}}).encode()
    audio, response_headers = request_bytes(opener, urllib.request.Request(
        f'{BASE}/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128',
        data=body, headers={**headers, 'Accept': 'audio/mpeg'}, method='POST'), MAX_BYTES)
    content_type = response_headers.get('Content-Type', '').split(';')[0].strip()
    if not audio or content_type not in {'audio/mpeg', 'audio/mp3'}:
        raise TestError('No MP3 returned; no retry performed')
    raw = output / 'source.mp3'
    raw.write_bytes(audio)
    final = output / 'elevenlabs-es-mx-test.mp3'
    # The provider has no hard duration parameter. Enforce the downloadable duration locally.
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(raw), '-t', '14.8',
                    '-vn', '-af', 'afade=t=out:st=14.5:d=0.3', '-ar', '44100', '-c:a', 'libmp3lame', '-b:a', '128k', str(final)], check=True, capture_output=True)
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(final)], check=True, capture_output=True, text=True)
    metadata = json.loads(probe.stdout)
    duration = float(metadata['format']['duration'])
    if not 0 < duration <= MAX_SECONDS or not any(s['codec_name'] == 'mp3' for s in metadata['streams']):
        raise TestError('Output failed MP3 or duration validation')
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(final), '-f', 'null', '-'], check=True, capture_output=True)
    raw.unlink()
    # Do not persist voice metadata, account details, headers or secret values.
    report = {'model': MODEL, 'text': TEXT, 'text_characters': len(TEXT), 'maximum_characters': MAX_CHARACTERS,
              'generation_requests': 1, 'maximum_generation_requests': 1, 'max_duration_seconds': MAX_SECONDS,
              'output_duration_seconds': duration, 'output_bytes': final.stat().st_size,
              'voice_accent_label': accent, 'voice_id': voice_id, 'full_decode': 'passed',
              'publication_approved': False,
              'billing_note': 'Character/request cap per run, not an account-wide or monetary cap. Consult provider billing.'}
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-one-request', action='store_true')
    parser.add_argument('--voice-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = execute(args.output, args.voice_id, approved=args.execute_one_request)
    except TestError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print('Test failed; no retry performed. Inspect workflow status; secret and API payloads are suppressed.', file=sys.stderr)
        return 1
    print(f"MP3 ready: {report['output_duration_seconds']:.2f}s; {report['text_characters']} characters; one generation.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
