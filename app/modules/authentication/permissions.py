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
    "orders.view": "View customer orders",
    "orders.manage": "Create and manage customer orders",
    "artwork.view": "View artwork and previews",
    "artwork.manage": "Upload and version artwork",
    "artwork.approve": "Record artwork approval decisions",
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
            "orders.view",
            "orders.manage",
            "artwork.view",
            "artwork.manage",
            "artwork.approve",
        }
    ),
    "Designer": frozenset(
        {
            "dashboard.view",
            "customers.view",
            "products.view",
            "orders.view",
            "artwork.view",
            "artwork.manage",
        }
    ),
    "Production Operator": frozenset({"dashboard.view", "orders.view"}),
    "Accountant": frozenset({"dashboard.view", "reports.view", "customers.view"}),
    "Packing Staff": frozenset({"dashboard.view", "orders.view"}),
    "Dispatch Staff": frozenset({"dashboard.view", "orders.view"}),
    "Viewer": frozenset(
        {
            "dashboard.view",
            "customers.view",
            "products.view",
            "orders.view",
            "artwork.view",
        }
    ),
}
