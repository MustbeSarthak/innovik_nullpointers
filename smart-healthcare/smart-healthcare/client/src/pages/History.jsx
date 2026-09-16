import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHead from '../components/PageHead';
import { AssessmentAPI, AlertAPI, UploadAPI } from '../lib/api';
import { IcClock, IcShield, IcWarn, IcDoc } from '../components/Icons';

function colorFor(type, level) {
  if (type === 'alert') return level === 'Critical' ? '#ef4444' : '#f59e0b';
  if (type === 'document') return '#0d9488';
  return level === 'Critical' ? '#ef4444' : level === 'High' ? '#f59e0b' : level === 'Moderate' ? '#10b981' : '#22c55e';
}

function Icon({ type, size = 17 }) {
  if (type === 'assessment') return <IcShield size={size} />;
  if (type === 'alert') return <IcWarn size={size} />;
  return <IcDoc size={size} />;
}

export default function History() {
  const [events, setEvents] = useState(null);

  useEffect(() => {
    Promise.all([AssessmentAPI.history(), AlertAPI.list(), UploadAPI.list()])
      .then(([assessments, alerts, documents]) => {
        const all = [];

        assessments.forEach((a) => all.push({
          id: a.id,
          date: new Date(a.created_at),
          type: 'assessment',
          title: 'Assessment Completed',
          detail: `Risk: ${a.risk_level} (Score: ${a.risk_score})`,
          level: a.risk_level,
        }));

        alerts.forEach((a) => all.push({
          id: a.id,
          date: new Date(a.created_at),
          type: 'alert',
          title: `${a.severity} Alert`,
          detail: a.message || 'Alert triggered',
          level: a.severity,
        }));

        documents.forEach((d) => all.push({
          id: d.id,
          date: new Date(d.upload_time),
          type: 'document',
          title: 'Report Uploaded',
          detail: d.file_name,
        }));

        all.sort((a, b) => b.date - a.date);
        setEvents(all);
      })
      .catch(() => setEvents([]));
  }, []);

  let lastDate = '';

  return (
    <div className="page">
      <PageHead title="History" backTo="/" />

      {events === null ? (
        <div className="card empty"><span className="spinner" /></div>
      ) : events.length === 0 ? (
        <div className="card empty">
          <div className="empty-icon"><IcClock /></div>
          <h3>No history yet</h3>
          <p>Complete an assessment to build your health timeline.</p>
          <Link to="/assessment" className="btn btn-primary btn-sm">Start Assessment</Link>
        </div>
      ) : (
        events.map((ev) => {
          const dateStr = ev.date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
          const showDate = dateStr !== lastDate;
          lastDate = dateStr;
          return (
            <div key={ev.id}>
              {showDate && (
                <h3 style={{ fontSize: 12, fontWeight: 800, textTransform: 'uppercase', letterSpacing: 0.6, color: 'var(--text-3)', margin: '20px 0 8px' }}>
                  {dateStr}
                </h3>
              )}
              <div className="card card-pad-s fade-in" style={{ marginTop: 10 }}>
                <div className="tl-item" style={{ padding: 0, gap: 12 }}>
                  <div className="tl-dot" style={{ background: colorFor(ev.type, ev.level) }}>
                    <Icon type={ev.type} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 14, fontWeight: 700 }}>{ev.title}</p>
                    <p className="sub" style={{ fontSize: 13, marginTop: 2 }}>{ev.detail}</p>
                    <p className="hint" style={{ fontSize: 11, marginTop: 3 }}>{ev.date.toLocaleTimeString()}</p>
                  </div>
                </div>
              </div>
            </div>
          );
        })
      )}

      <div className="btn-row" style={{ marginTop: 24 }}>
        <Link to="/dashboard" className="btn btn-primary">Go to Dashboard</Link>
        <Link to="/alerts" className="btn btn-ghost">View Alerts</Link>
      </div>
    </div>
  );
}