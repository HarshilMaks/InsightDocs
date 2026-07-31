from backend.config import settings
from backend.models.database import engine


def test_database_engine_uses_pre_ping_and_configured_recycle():
    assert engine.pool._pre_ping is True
    assert engine.pool._recycle == settings.db_pool_recycle


def test_database_pool_sizing_is_environment_driven():
    """Pool sizing must come from Settings (env-configurable), not a
    hardcoded literal, so operators can tune it per deployment plan."""
    assert engine.pool.size() == settings.db_pool_size
    assert engine.pool._max_overflow == settings.db_max_overflow
