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


ERROR_BODY_LIMIT = 16_384
# Only these exact provider codes influence diagnostics; never echo upstream text.
PROVIDER_CATEGORIES = {
    'insufficient_credits': 'insufficient_credits',
    'insufficient_balance': 'insufficient_credits',
    'credit_balance_too_low': 'insufficient_credits',
    'paid_plan_required': 'plan_restriction',
    'subscription_required': 'plan_restriction',
    'subscription_tier_too_low': 'plan_restriction',
    'feature_not_available_for_subscription': 'plan_restriction',
    'model_not_available_for_subscription': 'plan_restriction',
    'voice_not_found': 'voice_unavailable',
    'voice_not_available': 'voice_unavailable',
    'voice_not_available_for_api': 'voice_unavailable',
    'voice_access_denied': 'voice_unavailable',
    'api_key_quota_exceeded': 'account_quota',
    'character_limit_exceeded': 'account_quota',
    'monthly_quota_exceeded': 'account_quota',
}


class HTTPDiagnosticError(TestError):
    def __init__(self, http_code: int, category: str):
        super().__init__(f'HTTP {http_code} category={category}')


def safe_http_category(http_code: int, body: bytes) -> str:
    """Classify bounded response content; return only locally defined constants.

    A generic 402 or quota_exceeded is ambiguous without specific evidence.
    Messages are inspected only for fixed phrases, never returned or persisted.
    """
    fallback = ('payment_rejection_unknown' if http_code == 402 else
                'authentication_error' if http_code == 401 else
                'access_denied' if http_code == 403 else
                'rate_limit_or_quota' if http_code == 429 else
                'provider_error' if http_code >= 500 else 'http_error')
    if len(body) > ERROR_BODY_LIMIT:
        return fallback
    try:
        parsed = json.loads(body)
        detail = parsed.get('detail', parsed) if isinstance(parsed, dict) else None
        if not isinstance(detail, dict):
            return fallback
        status = detail.get('status', detail.get('code'))
        if not isinstance(status, str):
            return fallback
        if status in PROVIDER_CATEGORIES:
            return PROVIDER_CATEGORIES[status]
        if status in {'quota_exceeded', 'payment_required'}:
            message = detail.get('message')
            message = message.casefold() if isinstance(message, str) else ''
            signals = {
                'insufficient_credits': ('insufficient credits', 'not enough credits', 'credits remaining'),
                'account_quota': ('monthly quota', 'api key quota', 'api key limit', 'character quota'),
                'plan_restriction': ('paid plan required', 'requires a paid subscription', 'free users cannot use', 'subscription tier does not support'),
                'voice_unavailable': ('voice is not available via the api', 'voice is not available through the api', 'voice not available for api'),
            }
            categories = {category for category, phrases in signals.items()
                          if any(phrase in message for phrase in phrases)}
            if len(categories) == 1:
                return categories.pop()
            if status == 'quota_exceeded':
                return 'quota_or_credits_ambiguous'
            if categories:
                return 'payment_rejection_ambiguous'
    except (ValueError, UnicodeError, RecursionError):
        pass
    return fallback


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
        try:
            body = exc.read(ERROR_BODY_LIMIT + 1)
            category = safe_http_category(exc.code, body)
        except Exception:
            category = safe_http_category(exc.code, b'')
        finally:
            exc.close()
        raise HTTPDiagnosticError(exc.code, category) from None
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
