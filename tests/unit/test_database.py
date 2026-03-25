from backend.models.database import engine


def test_database_engine_uses_pre_ping_and_recycle():
    assert engine.pool._pre_ping is True
    assert engine.pool._recycle == 300
