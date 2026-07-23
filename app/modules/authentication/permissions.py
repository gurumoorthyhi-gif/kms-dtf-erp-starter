"""Initial role and permission definitions."""

PERMISSIONS = {
    "dashboard.view": "View the operational dashboard",
    "users.manage": "Create and manage users",
    "roles.manage": "Manage roles and permissions",
    "settings.manage": "Manage application settings",
    "reports.view": "View business reports",
    "customers.view": "View customer records",
    "customers.manage": "Create and manage customer records",
    "products.view": "View products and pricing",
    "products.manage": "Manage products and pricing rules",
}

ROLE_PERMISSIONS = {
    "Administrator": frozenset(PERMISSIONS),
    "Manager": frozenset(
        {
            "dashboard.view",
            "reports.view",
            "customers.view",
            "customers.manage",
            "products.view",
            "products.manage",
        }
    ),
    "Designer": frozenset({"dashboard.view", "customers.view", "products.view"}),
    "Production Operator": frozenset({"dashboard.view"}),
    "Accountant": frozenset({"dashboard.view", "reports.view", "customers.view"}),
    "Packing Staff": frozenset({"dashboard.view"}),
    "Dispatch Staff": frozenset({"dashboard.view"}),
    "Viewer": frozenset({"dashboard.view", "customers.view", "products.view"}),
}
