/**
 * SQLite database adapter with pg-compatible query interface.
 * ─────────────────────────────────────────────────────────
 * Wraps better-sqlite3 so that every controller can keep calling
 *   pool.query(sql, params)  →  { rows: [...] }
 * without any changes.
 *
 * PostgreSQL $1, $2 placeholders are translated to SQLite ? placeholders.
 * JSONB columns work as TEXT (JSON strings) — JSON.parse is done on read.
 * SERIAL PRIMARY KEY becomes INTEGER PRIMARY KEY AUTOINCREMENT.
 * RETURNING * is handled via a post-run SELECT.
 */

const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = path.join(__dirname, '..', 'smart_healthcare.db');
const db = new Database(DB_PATH);

/* Enable WAL mode for better concurrency */
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

/* ── Schema (runs once — IF NOT EXISTS) ─────────────────── */
db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'patient',
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    age INTEGER,
    gender TEXT,
    blood_group TEXT,
    height REAL,
    weight REAL,
    phone TEXT,
    medical_history TEXT DEFAULT '{}',
    lifestyle TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS caretakers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER REFERENCES patients(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    relationship TEXT,
    alt_phone TEXT,
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER REFERENCES patients(id) ON DELETE CASCADE,
    risk_score INTEGER DEFAULT 0,
    risk_level TEXT DEFAULT 'Low',
    symptoms TEXT DEFAULT '{}',
    pain_level INTEGER DEFAULT 0,
    medications TEXT DEFAULT '[]',
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER REFERENCES patients(id) ON DELETE CASCADE,
    file_url TEXT NOT NULL,
    file_name TEXT,
    file_type TEXT,
    upload_time TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER REFERENCES patients(id) ON DELETE CASCADE,
    severity TEXT NOT NULL,
    message TEXT,
    risk_score INTEGER,
    symptoms TEXT DEFAULT '{}',
    action_taken TEXT,
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS medication_reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER REFERENCES patients(id) ON DELETE CASCADE,
    medicine_name TEXT NOT NULL,
    dosage TEXT,
    time TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
  );
`);

/* ── JSON column list — these get auto-parsed on read ───── */
const JSON_COLUMNS = new Set([
  'medical_history', 'lifestyle', 'symptoms', 'medications',
]);

function parseRow(row) {
  if (!row) return row;
  const out = { ...row };
  for (const col of JSON_COLUMNS) {
    if (col in out && typeof out[col] === 'string') {
      try { out[col] = JSON.parse(out[col]); } catch { /* leave as-is */ }
    }
  }
  return out;
}

/**
 * Convert PostgreSQL-style query to SQLite-compatible query.
 * – $1, $2, $3 → ?
 * – RETURNING * → separate SELECT after INSERT/UPDATE
 * – COALESCE with null params is handled natively
 * – SERIAL → already handled by schema (AUTOINCREMENT)
 */
function translateSQL(sql) {
  return sql.replace(/\$\d+/g, '?');
}

/* ── pg-compatible pool.query(sql, params) wrapper ──────── */
const pool = {
  query(sql, params = []) {
    const translated = translateSQL(sql);
    const trimmed = translated.trim().toUpperCase();

    /* Detect RETURNING * */
    const hasReturning = /RETURNING\s+\*/i.test(translated);
    const cleanSQL = translated.replace(/\s+RETURNING\s+\*/i, '');

    if (trimmed.startsWith('SELECT')) {
      const rows = db.prepare(cleanSQL).all(...params).map(parseRow);
      return Promise.resolve({ rows });
    }

    if (trimmed.startsWith('INSERT')) {
      const info = db.prepare(cleanSQL).run(...params);
      if (hasReturning) {
        /* Extract table name from INSERT INTO <table> */
        const match = cleanSQL.match(/INSERT\s+INTO\s+(\w+)/i);
        const table = match ? match[1] : null;
        if (table) {
          const row = db.prepare(`SELECT * FROM ${table} WHERE id = ?`).get(info.lastInsertRowid);
          return Promise.resolve({ rows: [parseRow(row)] });
        }
      }
      return Promise.resolve({ rows: [], lastInsertRowid: info.lastInsertRowid });
    }

    if (trimmed.startsWith('UPDATE')) {
      if (hasReturning) {
        /* For UPDATE ... WHERE id = ? RETURNING *, we need the id.
           Extract the WHERE clause id value from params (last param). */
        const match = cleanSQL.match(/UPDATE\s+(\w+)/i);
        const table = match ? match[1] : null;

        /* Find the WHERE condition to get the row back */
        const whereMatch = cleanSQL.match(/WHERE\s+(.+)/i);

        db.prepare(cleanSQL).run(...params);

        if (table && whereMatch) {
          const whereClause = whereMatch[1].trim();
          /* Count how many ? are before the WHERE clause */
          const beforeWhere = cleanSQL.substring(0, cleanSQL.toUpperCase().indexOf('WHERE')).split('?').length - 1;
          const whereParams = params.slice(beforeWhere);
          const row = db.prepare(`SELECT * FROM ${table} WHERE ${whereClause}`).get(...whereParams);
          return Promise.resolve({ rows: [parseRow(row)] });
        }
      }
      const info = db.prepare(cleanSQL).run(...params);
      return Promise.resolve({ rows: [], changes: info.changes });
    }

    if (trimmed.startsWith('DELETE')) {
      const info = db.prepare(cleanSQL).run(...params);
      return Promise.resolve({ rows: [], changes: info.changes });
    }

    /* Fallback: just run it */
    db.prepare(cleanSQL).run(...params);
    return Promise.resolve({ rows: [] });
  },
};

module.exports = pool;
