"""Read-only public-feed diagnostics, independent of ingestion and paid SDKs.

Uses Python's standard library; respects the runner's proxy and TLS settings.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from techslop.profiles.tech_business import FEEDS

SPECIALIZED_NAMES = frozenset({'xataka', 'genbeta', 'eleconomista', 'ars_technica',
                              'the_verge', 'google_blog', 'microsoft_blog', 'ecb', 'ft'})
MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
FEED_BUDGET_SECONDS = 30
SOCKET_TIMEOUT_SECONDS = 8


class ManualRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def public_url(url: str) -> str:
    """Reports omit userinfo, queries and fragments, including redirected tokens."""
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.hostname or '', parsed.path, '', ''))


def permitted_destination(url: str) -> bool:
    parsed = urlsplit(url)
    return (parsed.scheme == 'https' and bool(parsed.hostname)
            and not parsed.username and not parsed.password
            and not re.search(r'/(?:login|signin|sign-in|subscribe|paywall|oauth)(?:/|$)', parsed.path, re.I))


def inspect_xml(body: bytes) -> tuple[str, int]:
    if b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():
        raise ValueError('xml_declarations_not_supported')
    root = ET.fromstring(body)
    if root.tag == 'rss':
        channel = root.find('channel')
        if channel is None:
            raise ValueError('rss_channel_missing')
        return 'rss', len(channel.findall('item'))
    if root.tag == '{http://www.w3.org/2005/Atom}feed':
        return 'atom', len(root.findall('{http://www.w3.org/2005/Atom}entry'))
    if root.tag == '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF':
        if root.find('{http://purl.org/rss/1.0/}channel') is None:
            raise ValueError('rdf_channel_missing')
        return 'rss1', len(root.findall('{http://purl.org/rss/1.0/}item'))
    raise ValueError('not_rss_or_atom')


def diagnose(spec, *, opener=None, clock=time.monotonic) -> dict:
    result = {'source': spec.name, 'requested_url': public_url(spec.url),
              'status': 'pending_confirmation', 'http_status': None, 'error_code': None,
              'redirects': [], 'requests': [], 'final_url': None, 'feed_format': None,
              'feed_valid': None, 'entries': None, 'downloaded_bytes': 0}
    opener = opener or build_opener(ManualRedirects())
    deadline = clock() + FEED_BUDGET_SECONDS
    current = spec.url
    try:
        for hop in range(MAX_REDIRECTS + 1):
            if not permitted_destination(current):
                result['error_code'] = 'unsupported_or_auth_destination'
                return result
            remaining = deadline - clock()
            if remaining <= 0:
                raise TimeoutError
            result['final_url'] = public_url(current)
            result['requests'].append(public_url(current))
            request = Request(current, headers={'User-Agent': 'techslop-rss-diagnostic/1.0',
                                                'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml',
                                                'Accept-Encoding': 'identity'})
            try:
                response = opener.open(request, timeout=min(SOCKET_TIMEOUT_SECONDS, remaining))
            except HTTPError as exc:
                response = exc
            with response:
                status = result['http_status'] = response.code
                if status in {301, 302, 303, 307, 308}:
                    location = response.headers.get('Location')
                    if not location:
                        result['error_code'] = 'redirect_without_location'
                        return result
                    destination = urljoin(current, location)
                    result['redirects'].append({'from': public_url(current), 'status': status,
                                                'to': public_url(destination)})
                    if hop == MAX_REDIRECTS:
                        result['error_code'] = 'redirect_limit'
                        return result
                    current = destination
                    continue
                if status in {401, 402, 403, 407, 429, 451}:
                    result.update(status='blocked', error_code=f'http_{status}')
                    return result
                if status != 200:
                    result.update(status='invalid' if status in {404, 410} else 'pending_confirmation',
                                  error_code=f'http_{status}')
                    return result
                size = response.headers.get('Content-Length', '')
                if size.isdecimal() and int(size) > MAX_BYTES:
                    result['error_code'] = 'download_limit'
                    return result
                if response.headers.get('Content-Encoding', 'identity').lower() not in {'identity', ''}:
                    result['error_code'] = 'unsupported_content_encoding'
                    return result
                chunks = []
                while True:
                    if clock() >= deadline:
                        raise TimeoutError
                    chunk = response.read(min(65536, MAX_BYTES + 1 - result['downloaded_bytes']))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    result['downloaded_bytes'] += len(chunk)
                    if result['downloaded_bytes'] > MAX_BYTES:
                        result['error_code'] = 'download_limit'
                        return result
                try:
                    format, count = inspect_xml(b''.join(chunks))
                except (ET.ParseError, ValueError):
                    result.update(status='invalid', feed_valid=False, error_code='invalid_rss_atom')
                    return result
                result.update(feed_valid=True, feed_format=format, entries=count,
                              status='accessible' if count else 'pending_confirmation',
                              error_code=None if count else 'valid_feed_without_entries')
                return result
    except (TimeoutError, URLError, OSError, ValueError) as exc:
        # Exception payloads may contain proxy credentials or redirected tokens.
        # Inspect only for classification; never emit their arbitrary text.
        proxy_blocked = isinstance(exc, URLError) and bool(re.search(r'Tunnel connection failed: (?:403|407)', str(exc.reason)))
        result.update(status='blocked' if proxy_blocked else 'pending_confirmation',
                      error_code='proxy_connect_denied' if proxy_blocked else
                      'timeout' if isinstance(exc, TimeoutError) or isinstance(getattr(exc, 'reason', None), TimeoutError)
                      else type(exc).__name__)
        return result
    return result


def markdown(report: dict) -> str:
    labels = {'accessible': 'Accesible', 'blocked': 'Bloqueada', 'invalid': 'Inválida',
              'pending_confirmation': 'Pendiente de confirmar'}
    lines = ['# Diagnóstico RSS Tech Business', '', f"UTC: {report['generated_at']}", '',
             'Una respuesta HTTP 200 no basta: se exige XML RSS/Atom válido con registros. '
             'La validez es estructural; no verifica noticias, licencias de reutilización o independencia editorial.', '',
             '| Fuente | Estado | HTTP | RSS/Atom | Registros | Error |',
             '|---|---|---|---|---:|---|']
    for row in report['sources']:
        lines.append(f"| {row['source']} | {labels[row['status']]} | {row['http_status'] or '—'} | "
                     f"{row['feed_format'] or 'sin confirmar'} | {row['entries'] if row['entries'] is not None else '—'} | {row['error_code'] or '—'} |")
    for row in report['sources']:
        lines += ['', f"## {row['source']}", f"Solicitada: {row['requested_url']}",
                  f"Último destino solicitado: {row['final_url'] or 'ninguno'}"]
        lines += [f"- HTTP {hop['status']}: {hop['from']} → {hop['to']}" for hop in row['redirects']]
        if not row['redirects']:
            lines.append('Sin redirecciones observadas; un bloqueo previo a HTTP impide conocerlas.')
    return '\n'.join(lines) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('output/rss-diagnostic'))
    args = parser.parse_args()
    specs = [spec for spec in FEEDS if spec.name in SPECIALIZED_NAMES]
    if len(specs) != 9 or {spec.name for spec in specs} != SPECIALIZED_NAMES:
        raise RuntimeError('Expected exactly nine registered specialized feeds')
    report = {'schema_version': '1.0', 'generated_at': datetime.now(timezone.utc).isoformat(),
              'execution': 'real_network_diagnostic', 'limits': {'max_bytes_per_source': MAX_BYTES,
              'max_redirects': MAX_REDIRECTS, 'feed_budget_seconds': FEED_BUDGET_SECONDS,
              'socket_timeout_seconds': SOCKET_TIMEOUT_SECONDS},
              'sources': [diagnose(spec) for spec in specs]}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'rss-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    content = markdown(report)
    (args.output_dir / 'rss-report.md').write_text(content)
    print(content)


if __name__ == '__main__':
    main()
