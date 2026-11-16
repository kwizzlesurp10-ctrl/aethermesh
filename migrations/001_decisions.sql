CREATE TABLE IF NOT EXISTS gate_decisions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT, -- use BIGSERIAL in Postgres
    created_at    TEXT    NOT NULL,                  -- TIMESTAMPTZ DEFAULT NOW() in Postgres
    module        TEXT    NOT NULL,
    env           TEXT    NOT NULL,
    risk_score    INTEGER NOT NULL,
    veto          BOOLEAN NOT NULL,
    status        TEXT    NOT NULL,
    reason        TEXT,
    otel_trace_id TEXT,
    contract_json TEXT    NOT NULL                   -- JSONB in Postgres
);

CREATE INDEX IF NOT EXISTS idx_gate_decisions_module_veto
    ON gate_decisions (module, veto, created_at DESC);
