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
    "ai.use": "Submit and manage AI image jobs",
    "gang_sheets.view": "View gang sheet layouts",
    "gang_sheets.manage": "Create, edit, and export gang sheets",
    "production.view": "View production queue and history",
    "production.manage": "Manage production workflow and quality",
    "inventory.view": "View inventory and low-stock warnings",
    "inventory.manage": "Receive, issue, and adjust stock",
    "purchases.view": "View suppliers and purchases",
    "purchases.manage": "Manage suppliers, purchases, and receipts",
    "sales.view": "View quotations, invoices, and ledgers",
    "sales.manage": "Create quotations, invoices, and credit notes",
    "payments.view": "View payment history",
    "payments.manage": "Record customer payments",
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
            "ai.use",
            "gang_sheets.view",
            "gang_sheets.manage",
            "production.view",
            "production.manage",
            "inventory.view",
            "inventory.manage",
            "purchases.view",
            "purchases.manage",
            "sales.view",
            "sales.manage",
            "payments.view",
            "payments.manage",
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
            "ai.use",
            "gang_sheets.view",
            "gang_sheets.manage",
            "production.view",
            "production.manage",
        }
    ),
    "Production Operator": frozenset(
        {
            "dashboard.view",
            "orders.view",
            "gang_sheets.view",
            "production.view",
            "production.manage",
        }
    ),
    "Accountant": frozenset(
        {
            "dashboard.view",
            "reports.view",
            "customers.view",
            "purchases.view",
            "sales.view",
            "sales.manage",
            "payments.view",
            "payments.manage",
        }
    ),
    "Packing Staff": frozenset(
        {"dashboard.view", "orders.view", "production.view", "production.manage"}
    ),
    "Dispatch Staff": frozenset(
        {"dashboard.view", "orders.view", "production.view", "production.manage"}
    ),
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
