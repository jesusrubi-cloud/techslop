"""Provider refusals are simulated; never access ElevenLabs or real credentials."""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest
from scripts import elevenlabs_manual_test as trial


@pytest.mark.parametrize('status,category', [
    ('insufficient_credits','insufficient_credits'),
    ('paid_plan_required','plan_restriction'),
    ('subscription_required','plan_restriction'),
    ('voice_not_available_for_api','voice_unavailable'),
    ('voice_not_found','voice_unavailable'),
    ('api_key_quota_exceeded','account_quota'),
    ('monthly_quota_exceeded','account_quota'),
    ('unknown_sensitive_code_secret123','payment_rejection_unknown'),
])
def test_status_allowlist_returns_only_safe_constants(status,category):
    body=json.dumps({'detail':{'status':status,'message':'api_key=secret123; account=private@example.invalid'}}).encode()
    assert trial.safe_http_category(402,body)==category


@pytest.mark.parametrize('message,category', [
    ('You have insufficient credits. key=private','insufficient_credits'),
    ('This request exceeds your quota. You have 2 credits remaining.','insufficient_credits'),
    ('API key quota exhausted for private@example.invalid','account_quota'),
    ('Monthly quota exceeded','account_quota'),
    ('Quota exhausted','quota_or_credits_ambiguous'),
    ('API key quota exhausted; insufficient credits','quota_or_credits_ambiguous'),
])
def test_ambiguous_quota_does_not_claim_a_cause_without_evidence(message,category):
    body=json.dumps({'detail':{'status':'quota_exceeded','message':message}}).encode()
    assert trial.safe_http_category(402,body)==category


@pytest.mark.parametrize('body', [b'',b'not JSON secret123',b'[]',b'{"detail":null}',b'{"detail":{"status":[]}}',b'{"detail":"private"}',b'\xff',b'x'*16385])
def test_malformed_or_oversized_body_is_safe_unknown(body):
    assert trial.safe_http_category(402,body)=='payment_rejection_unknown'


class RejectingOpener:
    def __init__(self,code=402,status='insufficient_credits'):
        self.calls=0
        self.code,self.status=code,status
        self.body=None
    def open(self,request,timeout):
        self.calls+=1
        self.body=io.BytesIO(json.dumps({'detail':{'status':self.status,'message':'secret123 private@example.invalid'}}).encode())
        raise urllib.error.HTTPError(request.full_url,self.code,'sensitive reason secret123',{'X-private':'secret123'},self.body)


def test_http_exception_is_sanitized_closed_and_not_retried():
    opener=RejectingOpener()
    request=urllib.request.Request('https://api.elevenlabs.io/v1/text-to-speech/private_voice',data=b'{}',headers={'xi-api-key':'fake-unit-test-key'})
    with pytest.raises(trial.HTTPDiagnosticError) as failure:
        trial.request_bytes(opener,request,100)
    assert str(failure.value)=='HTTP 402 category=insufficient_credits'
    assert opener.calls==1
    assert opener.body.closed


@pytest.mark.parametrize('status,category', [
    ('insufficient_credits','insufficient_credits'),
    ('paid_plan_required','plan_restriction'),
    ('voice_not_available_for_api','voice_unavailable'),
    ('api_key_quota_exceeded','account_quota'),
])
def test_cli_logs_only_http_code_and_safe_category(tmp_path,monkeypatch,capsys,status,category):
    def fail(*args,**kwargs):
        trial.request_bytes(RejectingOpener(status=status),urllib.request.Request('https://api.elevenlabs.io/'),10)
    monkeypatch.setattr(trial,'execute',fail)
    monkeypatch.setattr('sys.argv',['test','--execute-one-request','--voice-id','unit_test_voice','--output',str(tmp_path)])
    assert trial.main()==1
    captured=capsys.readouterr()
    assert captured.out==''
    assert captured.err==f'HTTP 402 category={category}\n'
    assert list(tmp_path.iterdir())==[]


@pytest.mark.parametrize('message,category', [
    ('Paid plan required. Private account details follow.','plan_restriction'),
    ('This voice is not available via the API. secret123','voice_unavailable'),
    ('Not enough credits. balance=private','insufficient_credits'),
    ('Monthly quota exceeded for private account','account_quota'),
    ('Paid plan required; this voice is not available via the API.','payment_rejection_ambiguous'),
    ('Payment required. Private billing details.','payment_rejection_unknown'),
])
def test_payment_required_uses_only_specific_safe_signals(message,category):
    body=json.dumps({'detail':{'status':'payment_required','message':message}}).encode()
    assert trial.safe_http_category(402,body)==category


def test_error_body_read_is_bounded():
    class BoundedBody(io.BytesIO):
        def read(self,n=-1):
            assert n==trial.ERROR_BODY_LIMIT+1
            return super().read(n)
    class Opener:
        def open(self,request,timeout):
            raise urllib.error.HTTPError(request.full_url,402,'private',{},BoundedBody(b'x'*50000))
    with pytest.raises(trial.HTTPDiagnosticError,match='^HTTP 402 category=payment_rejection_unknown$'):
        trial.request_bytes(Opener(),urllib.request.Request('https://api.elevenlabs.io/'),20)
