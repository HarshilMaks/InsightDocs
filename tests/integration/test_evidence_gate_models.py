from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models import Base, EvidenceGateClaim, EvidenceGateRun, Query, User


def _engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    return engine


def _user() -> User:
    return User(
        id="user-evidence-1",
        email="evidence@example.com",
        name="Evidence User",
        hashed_password="not-used-in-this-test",
    )


def _query(user_id: str) -> Query:
    return Query(
        id="query-evidence-1",
        user_id=user_id,
        query_text="What stores metadata?",
        response_text="PostgreSQL stores metadata.",
        sources=[{"source_number": 1, "content": "PostgreSQL stores metadata."}],
    )


def _run(query_id: str, user_id: str, attempt: int = 1) -> EvidenceGateRun:
    return EvidenceGateRun(
        query_id=query_id,
        user_id=user_id,
        attempt=attempt,
        policy_version="evidence-gate/v1",
        mode="shadow",
        status="passed",
        action="allow",
        candidate_answer_sha256="a" * 64,
        delivered_answer_sha256="a" * 64,
        source_snapshot_sha256="b" * 64,
        claim_count=1,
        supported_count=1,
    )


def test_run_and_claim_persist_with_query_bound_relationships():
    engine = _engine()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        user = _user()
        query = _query(user.id)
        run = _run(query.id, user.id)
        claim = EvidenceGateClaim(
            gate_run=run,
            ordinal=1,
            claim_text="PostgreSQL stores metadata.",
            claim_sha256="c" * 64,
            verdict="supported",
            supporting_source_numbers=[1],
        )
        session.add_all([user, query, run, claim])
        session.commit()

        stored_query = session.get(Query, query.id)
        stored_run = session.get(EvidenceGateRun, run.id)
        assert stored_query is not None
        assert stored_run is not None
        assert [item.id for item in stored_query.evidence_gate_runs] == [run.id]
        assert stored_run.claims[0].supporting_source_numbers == [1]
        assert stored_run.query_id == stored_query.id
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_unique_attempt_constraint_and_check_constraints_are_enforced():
    engine = _engine()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        user = _user()
        query = _query(user.id)
        session.add_all([user, query])
        session.commit()

        session.add(_run(query.id, user.id))
        session.commit()

        session.add(_run(query.id, user.id))
        try:
            session.commit()
            raise AssertionError("duplicate policy attempt unexpectedly persisted")
        except IntegrityError:
            session.rollback()

        invalid = _run(query.id, user.id, attempt=2)
        invalid.status = "not-a-status"
        session.add(invalid)
        try:
            session.commit()
            raise AssertionError("invalid status unexpectedly persisted")
        except IntegrityError:
            session.rollback()
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_deleting_a_query_cascades_its_audit_run_and_claim():
    engine = _engine()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        user = _user()
        query = _query(user.id)
        run = _run(query.id, user.id)
        claim = EvidenceGateClaim(
            gate_run=run,
            ordinal=1,
            claim_text="PostgreSQL stores metadata.",
            claim_sha256="c" * 64,
            verdict="supported",
            supporting_source_numbers=[1],
        )
        session.add_all([user, query, run, claim])
        session.commit()

        session.delete(query)
        session.commit()

        assert session.get(EvidenceGateRun, run.id) is None
        assert session.get(EvidenceGateClaim, claim.id) is None
    finally:
        session.close()
        Base.metadata.drop_all(engine)
