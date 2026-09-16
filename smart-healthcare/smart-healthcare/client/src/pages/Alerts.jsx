import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHead from '../components/PageHead';
import { AlertAPI } from '../lib/api';
import { IcBell, IcWarn, IcShield } from '../components/Icons';

function Badge({ level }) {
  const cls =
    level === 'Critical' ? 'badge-critical'
      : level === 'High' ? 'badge-high'
      : level === 'Moderate' ? 'badge-moderate' : 'badge-low';
  return <span className={`badge ${cls}`}>{level}</span>;
}

export default function Alerts() {
  const [alerts, setAlerts] = useState(null);

  useEffect(() => {
    AlertAPI.list().then(setAlerts).catch(() => setAlerts([]));
  }, []);

  return (
    <div className="page">
      <PageHead title="Alerts" backTo="/" />

      {alerts === null ? (
        <div className="card empty"><span className="spinner" /></div>
      ) : alerts.length === 0 ? (
        <div className="card empty">
          <div className="empty-icon" style={{ color: 'var(--success)' }}>
            <IcShield size={26} />
          </div>
          <h3>All clear</h3>
          <p>No alerts detected. We're monitoring your health.</p>
          <Link to="/assessment" className="btn btn-ghost btn-sm" style={{ width: 'auto' }}>Run Health Check</Link>
        </div>
      ) : (
        alerts.map((a) => (
          <div className="card card-pad-s fade-in" style={{ marginTop: 10, borderLeft: `4px solid ${a.severity === 'Critical' ? 'var(--danger)' : 'var(--warn)'}` }} key={a.id}>
            <div className="split" style={{ marginBottom: 8 }}>
              <Badge level={a.severity} />
              <span className="hint" style={{ fontSize: 11 }}>
                {new Date(a.created_at).toLocaleString()}
              </span>
            </div>
            <p style={{ fontSize: 15, fontWeight: 700 }}>{a.message || 'Health alert'}</p>
            {a.risk_score != null && (
              <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                <span className="badge badge-moderate">Risk Score: {a.risk_score}</span>
                {a.action_taken && <span className="badge badge-low">Action: {a.action_taken}</span>}
              </div>
            )}
          </div>
        ))
      )}

      <div className="btn-row" style={{ marginTop: 24 }}>
        <Link to="/dashboard" className="btn btn-primary">Go to Dashboard</Link>
        <Link to="/history" className="btn btn-ghost">View History</Link>
      </div>
    </div>
  );
}