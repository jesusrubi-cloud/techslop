from __future__ import annotations
from io import BytesIO
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
import pytest
import yaml
from scripts import diagnose_rss_tech_business as diag

SPEC = next(s for s in diag.FEEDS if s.name == 'xataka')
RSS = b'<rss version="2.0"><channel><title>Example</title><item><title>One</title></item></channel></rss>'
ATOM = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>One</title></entry><entry/></feed>'


class Response(BytesIO):
    def __init__(self, body=RSS, code=200, headers=None):
        super().__init__(body)
        self.code = code
        self.headers = headers or {}


class Opener:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request.full_url, timeout))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.parametrize('body,format,count', [(RSS,'rss',1),(ATOM,'atom',2),
    (b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/"><channel/><item/></rdf:RDF>','rss1',1)])
def test_valid_rss_atom_and_rdf(body, format, count):
    result = diag.diagnose(SPEC, opener=Opener(Response(body)))
    assert result['status'] == 'accessible'
    assert result['http_status'] == 200
    assert result['feed_valid'] is True
    assert (result['feed_format'],result['entries']) == (format,count)


@pytest.mark.parametrize('body', [b'<html><body>Subscribe</body></html>', b'<rss>', b'<rss/>',
                                  b'<!DOCTYPE rss [<!ENTITY a "x">]><rss><channel/></rss>'])
def test_200_html_malformed_and_unsafe_xml_are_invalid(body):
    result = diag.diagnose(SPEC, opener=Opener(Response(body)))
    assert result['status'] == 'invalid'
    assert result['feed_valid'] is False
    assert result['entries'] is None


def test_empty_valid_feed_is_pending_not_working():
    result = diag.diagnose(SPEC, opener=Opener(Response(b'<rss><channel/></rss>')))
    assert result['status'] == 'pending_confirmation'
    assert result['feed_valid'] is True
    assert result['entries'] == 0


@pytest.mark.parametrize('status,expected', [(401,'blocked'),(402,'blocked'),(403,'blocked'),(407,'blocked'),
                                            (429,'blocked'),(451,'blocked'),(404,'invalid'),(410,'invalid'),(503,'pending_confirmation')])
def test_http_statuses_and_http_error_objects(status, expected):
    error = HTTPError(SPEC.url,status,'sensitive server message',{},BytesIO(b'private body'))
    result = diag.diagnose(SPEC, opener=Opener(error))
    assert result['status'] == expected
    assert result['http_status'] == status
    assert 'private body' not in json.dumps(result)
    assert 'sensitive server message' not in json.dumps(result)


def test_redirect_chain_and_destination_failure_are_recorded():
    opener = Opener(Response(code=301,headers={'Location':'https://feeds.example.com/feed?token=secret'}),
                    Response(code=403))
    result = diag.diagnose(SPEC, opener=opener)
    assert result['status'] == 'blocked'
    assert result['final_url'] == 'https://feeds.example.com/feed'
    assert result['redirects'] == [{'from':SPEC.url,'status':301,'to':'https://feeds.example.com/feed'}]
    assert len(opener.calls) == 2
    assert 'secret' not in json.dumps(result)


def test_relative_redirect_to_valid_atom():
    result = diag.diagnose(SPEC, opener=Opener(Response(code=302,headers={'Location':'/feed.atom'}),Response(ATOM)))
    assert result['status'] == 'accessible'
    assert result['final_url'] == 'https://www.xataka.com/feed.atom'


@pytest.mark.parametrize('destination', ['http://example.com/feed','https://example.com/login',
    'https://user:password@example.com/feed','https://example.com/paywall'])
def test_no_downgrades_credentials_or_authentication_attempts(destination):
    opener = Opener(Response(code=302,headers={'Location':destination}))
    result = diag.diagnose(SPEC, opener=opener)
    assert result['status'] == 'pending_confirmation'
    assert result['error_code'] == 'unsupported_or_auth_destination'
    assert len(opener.calls) == 1
    assert 'password' not in json.dumps(result)


def test_redirect_limit_no_retries():
    opener = Opener(*[Response(code=302,headers={'Location':'/loop'}) for _ in range(diag.MAX_REDIRECTS+1)])
    result = diag.diagnose(SPEC, opener=opener)
    assert result['error_code'] == 'redirect_limit'
    assert len(opener.calls) == diag.MAX_REDIRECTS+1


@pytest.mark.parametrize('headers,body', [({'Content-Length':str(diag.MAX_BYTES+1)},b''), ({},b'x'*(diag.MAX_BYTES+100))])
def test_bounded_downloads(headers, body):
    result = diag.diagnose(SPEC, opener=Opener(Response(body,headers=headers)))
    assert result['status'] == 'pending_confirmation'
    assert result['error_code'] == 'download_limit'
    assert result['downloaded_bytes'] <= diag.MAX_BYTES+1


@pytest.mark.parametrize('error,expected,status', [(TimeoutError(),'timeout','pending_confirmation'),
    (URLError(TimeoutError()),'timeout','pending_confirmation'),
    (URLError('Tunnel connection failed: 403 Forbidden secret proxy token'),'proxy_connect_denied','blocked'),
    (URLError('DNS failed: secret-token'),'URLError','pending_confirmation')])
def test_safe_network_errors(error, expected, status):
    result = diag.diagnose(SPEC, opener=Opener(error))
    assert result['error_code'] == expected
    assert result['status'] == status
    assert 'secret' not in json.dumps(result)


def test_feed_deadline_prevents_additional_requests():
    times = iter([0,0,31])
    opener = Opener(Response(code=302,headers={'Location':'/next'}))
    result = diag.diagnose(SPEC, opener=opener, clock=lambda:next(times))
    assert result['error_code'] == 'timeout'
    assert len(opener.calls) == 1
    assert opener.calls[0][1] <= diag.SOCKET_TIMEOUT_SECONDS


def test_main_writes_both_reports_for_exact_nine_profile_endpoints(tmp_path, monkeypatch):
    visited = []
    original = diag.diagnose
    def fake(spec):
        visited.append(spec)
        return original(spec,opener=Opener(Response()))
    monkeypatch.setattr(diag,'diagnose',fake)
    monkeypatch.setattr('sys.argv',['diagnose','--output-dir',str(tmp_path)])
    diag.main()
    report = json.loads((tmp_path/'rss-report.json').read_text())
    content = (tmp_path/'rss-report.md').read_text()
    assert len(report['sources']) == 9
    assert {s.name for s in visited} == diag.SPECIALIZED_NAMES
    assert all(s in diag.FEEDS for s in visited)
    assert all(s['source'] in content for s in report['sources'])
    assert 'real_network_diagnostic' == report['execution']


def test_workflow_is_manual_read_only_no_secret_or_paid_setup():
    path = Path('.github/workflows/rss-tech-business-diagnostic.yml')
    config = yaml.load(path.read_text(),Loader=yaml.BaseLoader)
    assert set(config['on']) == {'workflow_dispatch'}
    assert config['name'] == 'Diagnóstico RSS Tech Business'
    assert config['permissions'] == {'contents':'read'}
    steps = config['jobs']['diagnose']['steps']
    assert any('diagnose_rss_tech_business.py' in s.get('run','') for s in steps)
    artifact = next(s for s in steps if 'upload-artifact@' in s.get('uses',''))
    assert 'rss-report.json' in artifact['with']['path']
    assert 'rss-report.md' in artifact['with']['path']
    assert artifact['if'] == '${{ always() }}'
    assert 'secrets.' not in path.read_text()
    assert 'pipeline.py' not in path.read_text()
