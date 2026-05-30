PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    protected INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS security_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    pin_salt TEXT,
    pin_hash TEXT,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    lockout_until TEXT,
    last_unlocked_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS actions (
    key TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    kind TEXT NOT NULL,
    target TEXT NOT NULL,
    args_json TEXT NOT NULL DEFAULT '[]',
    platform TEXT NOT NULL DEFAULT 'any',
    requires_pin INTEGER NOT NULL DEFAULT 0,
    destructive INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_key TEXT NOT NULL,
    allowed INTEGER NOT NULL DEFAULT 0,
    success INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_action_log_created_at ON action_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_log_key ON action_log(action_key);

CREATE TABLE IF NOT EXISTS mount_status (
    mount_key TEXT PRIMARY KEY,
    mount_path TEXT NOT NULL,
    present INTEGER NOT NULL DEFAULT 0,
    is_mount INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL,
    checked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_number TEXT,
    release_code TEXT,
    pallet_code TEXT,
    mark_number TEXT,
    display_name TEXT NOT NULL,
    search_text TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_path TEXT,
    source_url TEXT,
    last_seen_at TEXT NOT NULL,
    indexed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_search_text ON jobs(search_text);
CREATE INDEX IF NOT EXISTS idx_jobs_display_name ON jobs(display_name);
CREATE INDEX IF NOT EXISTS idx_jobs_indexed_at ON jobs(indexed_at DESC);

CREATE TABLE IF NOT EXISTS job_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    doc_type TEXT NOT NULL,
    label TEXT NOT NULL,
    path_or_url TEXT NOT NULL,
    source_path TEXT,
    search_text TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_job_documents_unique ON job_documents(job_id, path_or_url);
CREATE INDEX IF NOT EXISTS idx_job_documents_job_id ON job_documents(job_id);
CREATE INDEX IF NOT EXISTS idx_job_documents_search_text ON job_documents(search_text);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_type TEXT NOT NULL,
    job_ref TEXT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    protected INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_type ON notes(note_type);

CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    results_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_history_query ON search_history(query);

CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_backups_created_at ON backups(created_at DESC);
