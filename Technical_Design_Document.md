# Technical design

The FastAPI application uses SQLAlchemy relational entities for users, shipments, documents, extracted fields, line items, validation results, corrections, approvals, audits, and exports. UUID string keys keep the SQLite demo and PostgreSQL deployment compatible. `services/extraction.py` is the provider seam: an adapter must return Pydantic-validated structured values with source pages and confidence, otherwise it must fail closed.

Validation is deterministic and rerunnable. It persists rule, severity, source values, status and a human resolution field. High unresolved results prevent approval; approval and unresolved required low-confidence values prevent export in the API itself.

Production should set PostgreSQL `DATABASE_URL`, a long JWT secret, add a configured Gemini adapter, store documents outside the application container, and generate Alembic migrations from the models.
