import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires live Supabase credentials in .env")


@pytest.fixture
def supabase_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_PUBLISHABLE_KEY"))
