from app.modules.whatsapp_workspace.profile import WhatsAppProfilePaths


def test_profile_paths_are_separated() -> None:
    paths = WhatsAppProfilePaths.default()
    assert paths.root.name == "whatsapp"
    assert paths.root.parent.name == "browser_profiles"
    assert paths.storage == paths.root / "storage"
    assert paths.cache == paths.root / "cache"
