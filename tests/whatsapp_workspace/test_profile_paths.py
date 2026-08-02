import pytest

from app.modules.whatsapp_workspace.profile import WhatsAppProfilePaths, chromium_user_agent


def test_profile_paths_are_separated() -> None:
    paths = WhatsAppProfilePaths.default()
    assert paths.root.name == "whatsapp"
    assert paths.root.parent.name == "browser_profiles"
    assert paths.storage == paths.root / "storage"
    assert paths.cache == paths.root / "cache"


def test_chromium_user_agent_uses_real_chrome_identity() -> None:
    user_agent = chromium_user_agent("140.0.7339.225")
    assert "Chrome/140.0.7339.225" in user_agent
    assert "QtWebEngine" not in user_agent
    assert user_agent.endswith("Safari/537.36")


@pytest.mark.parametrize("version", ["", "latest", "140 beta"])
def test_chromium_user_agent_rejects_invalid_versions(version: str) -> None:
    with pytest.raises(ValueError):
        chromium_user_agent(version)
