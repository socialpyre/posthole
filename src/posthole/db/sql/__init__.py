"""SQL statements grouped by table.

Each submodule holds the raw SQL strings for one table. Stores in
``posthole/db/<table>.py`` import the constants by name. Keep the SQL here
when a query is reused or non-trivial; one-off ad-hoc queries can stay
inline.
"""
