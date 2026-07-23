"""Initial role and permission definitions."""

PERMISSIONS = {
    "dashboard.view": "View the operational dashboard",
    "users.manage": "Create and manage users",
    "roles.manage": "Manage roles and permissions",
    "settings.manage": "Manage application settings",
    "reports.view": "View business reports",
}

ROLE_PERMISSIONS = {
    "Administrator": frozenset(PERMISSIONS),
    "Manager": frozenset({"dashboard.view", "reports.view"}),
    "Designer": frozenset({"dashboard.view"}),
    "Production Operator": frozenset({"dashboard.view"}),
    "Accountant": frozenset({"dashboard.view", "reports.view"}),
    "Packing Staff": frozenset({"dashboard.view"}),
    "Dispatch Staff": frozenset({"dashboard.view"}),
    "Viewer": frozenset({"dashboard.view"}),
}
