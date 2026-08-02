from app.modules.whatsapp_workspace.navigation_guard import (
    host_is_allowed,
    redact_url,
    top_level_url_is_allowed,
)


def test_allows_whatsapp_and_required_subdomains() -> None:
    assert top_level_url_is_allowed("https://web.whatsapp.com/")
    assert top_level_url_is_allowed("https://static.whatsapp.net/assets/app.js")
    assert top_level_url_is_allowed("https://lookaside.facebook.com/path")
    assert top_level_url_is_allowed("https://example.fbcdn.net/image")


def test_rejects_lookalikes_non_https_and_credentials() -> None:
    assert not host_is_allowed("whatsapp.com.evil.example")
    assert not top_level_url_is_allowed("http://web.whatsapp.com/")
    assert not top_level_url_is_allowed("https://user@example.com@evil.example/")
    assert not top_level_url_is_allowed("javascript:alert(1)")


def test_redaction_removes_sensitive_url_parts() -> None:
    assert redact_url("https://user:secret@example.com:8443/a/b?token=secret#chat") == (
        "https://example.com/a/b"
    )
