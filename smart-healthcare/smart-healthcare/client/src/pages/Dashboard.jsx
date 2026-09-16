import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';
import PageHead from '../components/PageHead';
import ThemeToggle from '../components/ThemeToggle';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { AuthAPI, PatientAPI, AssessmentAPI, AlertAPI, UploadAPI } from '../lib/api';
import { IcClock, IcDoc, IcUpload, IcLogout, IcHeart } from '../components/Icons';

const stateMeta = {
  normal: { label: 'Normal', tone: 'badge-low', desc: 'Vitals are stable.' },
  medium: { label: 'Medium', tone: 'badge-moderate', desc: 'Hospitalization should be considered.' },
  critical: { label: 'Critical', tone: 'badge-critical', desc: 'Critical signal detected — SMS sent to caretaker.' },
};

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const randomBetween = (min, max) => Math.random() * (max - min) + min;
const formatMetric = (value) => Number.isFinite(Number(value)) ? Number(value).toFixed(2) : '--';

const mimicAcnoTrend = (previous, current) => {
  const keys = ['heart_rate', 'systolic_bp', 'diastolic_bp', 'spo2', 'temperature', 'glucose'];
  const trend = {};

  for (const key of keys) {
    const prev = previous?.[key];
    const next = current?.[key];

    if (typeof prev === 'number' && typeof next === 'number') {
      if (Math.abs(next - prev) < 0.8) trend[key] = 'stable';
      else trend[key] = next > prev ? 'rising' : 'falling';
    }
  }

  return trend;
};

const randomizeReading = (baseReading, state, tick) => {
  if (!baseReading) return null;

  const intensity = state === 'critical' ? 1.9 : state === 'medium' ? 1.2 : 0.5;
  const wave = Math.sin((tick + 1) / 2.2);
  const next = { ...baseReading };

  next.heart_rate = Number(clamp(Number((baseReading.heart_rate || 72) + randomBetween(-8, 8) + wave * 8 * intensity), 52, 170).toFixed(2));
  next.systolic_bp = Number(clamp(Number((baseReading.systolic_bp || 118) + randomBetween(-12, 12) + wave * 10 * intensity), 80, 200).toFixed(2));
  next.diastolic_bp = Number(clamp(Number((baseReading.diastolic_bp || 78) + randomBetween(-8, 8) + wave * 7 * intensity), 50, 120).toFixed(2));
  next.spo2 = Number(clamp(Number((baseReading.spo2 || 98) + randomBetween(-3, 2) - wave * 5 * intensity), 78, 100).toFixed(2));
  next.temperature = Number(clamp(Number((baseReading.temperature || 37) + randomBetween(-0.6, 0.8) + wave * 0.7 * intensity), 35.5, 40.5).toFixed(2));
  next.glucose = Number(clamp(Number((baseReading.glucose || 120) + randomBetween(-20, 24) + wave * 18 * intensity), 68, 350).toFixed(2));
  next.simulator_state = state;
  next.source = 'SIMULATED';
  next.trend = mimicAcnoTrend(baseReading, next);

  return next;
};

const authHeaders = () => {
  const token = localStorage.getItem('smart_healthcare_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

function Badge({ level }) {
  const cls =
    level === 'Critical' ? 'badge-critical'
      : level === 'High' ? 'badge-high'
      : level === 'Moderate' ? 'badge-moderate' : 'badge-low';
  return <span className={`badge ${cls}`}>{level}</span>;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { user, setUser } = useAuth();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState({ patient: {}, assessments: [], alerts: [], docs: [] });
  const [latestVital, setLatestVital] = useState(null);
  const [simulator, setSimulator] = useState({ running: false, state: 'normal' });
  const previousStateRef = useRef('normal');
  const tickRef = useRef(0);

  const syncVitals = async () => {
    if (!user) return;
    try {
      const [latestRes, statusRes] = await Promise.all([
        axios.get('/api/v1/vitals/latest', { headers: authHeaders() }),
        axios.get('/api/v1/vitals/simulator/status', { headers: authHeaders() }),
      ]);

      const nextStatus = statusRes?.data ?? { running: false, state: 'normal' };
      const currentState = nextStatus.state || nextStatus?.simulator_state || 'normal';
      const seededReading = latestRes?.data ? randomizeReading(latestRes.data, currentState, tickRef.current) : null;
      tickRef.current += 1;

      setLatestVital(seededReading || latestRes?.data || null);
      setSimulator({
        running: !!nextStatus.running,
        state: currentState,
      });
    } catch {
      setLatestVital(null);
      setSimulator({ running: false, state: 'normal' });
    }
  };

  const startSimulator = async (nextState = 'normal') => {
    if (!user) return;
    setSimulator((prev) => ({ ...prev, running: true, state: nextState }));
    try {
      await axios.post(
        '/api/v1/vitals/simulator/start',
        {
          profile: user?.gender === 'female' ? 'female' : 'male',
          state: nextState,
          interval_seconds: 1.5,
          scenario: 'NORMAL',
        },
        { headers: authHeaders() }
      );
      await syncVitals();
    } catch (error) {
      console.error('Failed to start simulator', error);
    }
  };

  useEffect(() => {
    Promise.all([PatientAPI.get(), AssessmentAPI.history(), AlertAPI.list(), UploadAPI.list()])
      .then(([patient, assessments, alerts, docs]) =>
        setData({ patient, assessments, alerts, docs })
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    syncVitals();
    const interval = setInterval(syncVitals, 1500);
    return () => clearInterval(interval);
  }, [user]);

  useEffect(() => {
    if (!user) return;

    const ensureRunning = async () => {
      try {
        const { data } = await axios.get('/api/v1/vitals/simulator/status', {
          headers: authHeaders(),
        });

        if (!data?.running) {
          await startSimulator('normal');
        } else {
          setSimulator({ running: true, state: data.state || 'normal' });
        }
      } catch {
        await startSimulator('normal');
      }
    };

    ensureRunning();
  }, [user]);

  useEffect(() => {
    if (!user || !simulator.running) return;

    const cycle = setInterval(() => {
      const states = ['normal', 'medium', 'critical'];
      const currentIndex = states.indexOf(simulator.state || 'normal');
      const nextState = states[(currentIndex + 1) % states.length];
      setSimulator((prev) => ({ ...prev, state: nextState }));
      startSimulator(nextState);
    }, 7000);

    return () => clearInterval(cycle);
  }, [user, simulator.running, simulator.state]);

  useEffect(() => {
    const state = latestVital?.simulator_state || simulator.state || 'normal';
    if (state !== previousStateRef.current) {
      if (state === 'critical') {
        showToast('Critical reading detected — SMS sent to caretaker', 'err');
      } else if (state === 'medium') {
        showToast('Medium alert: hospitalization should be considered', 'warn');
      }
      previousStateRef.current = state;
    }
  }, [latestVital, simulator.state, showToast]);

  const { patient, assessments, alerts, docs } = data;
  const latest = assessments[0];
  const liveState = latestVital?.simulator_state || simulator.state || 'normal';
  const status = stateMeta[liveState] || stateMeta.normal;

  const logout = async () => {
    await AuthAPI.logout();
    setUser(null);
    navigate('/login');
  };

  return (
    <div className="page">
      <PageHead
        title={loading ? 'Dashboard' : `Hi, ${(user?.name || 'Patient').split(' ')[0]}`}
        right={
          <div className="split" style={{ gap: 8 }}>
            <ThemeToggle />
            <button className="icon-btn" onClick={logout} title="Sign out">
              <IcLogout size={17} />
            </button>
          </div>
        }
      />

      {loading ? (
        <div className="card empty"><span className="spinner" /></div>
      ) : (
        <div className="fade-in">
          <div className="card" style={{ background: 'var(--primary-soft)', borderColor: 'transparent' }}>
            <div className="split">
              <div>
                <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase', color: 'var(--primary-strong)' }}>
                  Live Monitoring
                </p>
                <h2 style={{ fontSize: 24, marginTop: 4 }}>{status.label}</h2>
                <p className="sub" style={{ fontSize: 13, marginTop: 4 }}>{status.desc}</p>
              </div>
              <span className={`badge ${status.tone}`}>{status.label}</span>
            </div>
            <div className="btn-row" style={{ marginTop: 14 }}>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => startSimulator(liveState === 'critical' ? 'normal' : liveState)}
              >
                {simulator.running ? 'Refresh monitor' : 'Start monitor'}
              </button>
            </div>
          </div>

          <div className="card live-monitor-card" style={{ marginTop: 18 }}>
            <div className="split" style={{ alignItems: 'center' }}>
              <div>
                <p className="monitor-label">Current vitals</p>
                <h3 className="monitor-title">{status.label}</h3>
              </div>
              <span className={`status-pill ${liveState === 'critical' ? 'danger' : liveState === 'medium' ? 'warn' : 'good'}`}>
                {status.label}
              </span>
            </div>

            <div className="monitor-grid">
              <div className="metric-box">
                <span>Heart rate</span>
                <strong>{formatMetric(latestVital?.heart_rate)} bpm</strong>
              </div>
              <div className="metric-box">
                <span>Blood pressure</span>
                <strong>{latestVital ? `${formatMetric(latestVital.systolic_bp)}/${formatMetric(latestVital.diastolic_bp)}` : '--/--'} mmHg</strong>
              </div>
              <div className="metric-box">
                <span>SpO2</span>
                <strong>{formatMetric(latestVital?.spo2)}%</strong>
              </div>
              <div className="metric-box">
                <span>Temperature</span>
                <strong>{formatMetric(latestVital?.temperature)}°C</strong>
              </div>
              <div className="metric-box">
                <span>Glucose</span>
                <strong>{formatMetric(latestVital?.glucose)} mg/dL</strong>
              </div>
              <div className="metric-box">
                <span>Source</span>
                <strong>{latestVital?.source ? latestVital.source.toLowerCase() : 'idle'}</strong>
              </div>
            </div>

            {liveState === 'critical' && (
              <div className="alert-box danger">Critical reading detected — SMS sent to caretaker.</div>
            )}
            {liveState === 'medium' && (
              <div className="alert-box warn">Medium alert: hospitalization should be considered.</div>
            )}
          </div>

          <div className="stat-grid">
            <div className="stat">
              <p className="stat-label">Assessments</p>
              <p className="stat-value">{assessments.length}</p>
            </div>
            <div className="stat">
              <p className="stat-label">Alerts</p>
              <p className="stat-value" style={{ color: alerts.length ? 'var(--danger)' : undefined }}>
                {alerts.length}
              </p>
            </div>
          </div>

          <h3 className="section-title">Recent Assessments</h3>
          {assessments.length === 0 ? (
            <div className="card empty">
              <div className="empty-icon"><IcClock /></div>
              <h3>No assessments yet</h3>
              <p>Complete an assessment to track your health.</p>
              <Link to="/assessment" className="btn btn-primary btn-sm">Start Assessment</Link>
            </div>
          ) : (
            assessments.slice(0, 3).map((a) => (
              <div className="card card-pad-s" key={a.id}>
                <div className="split">
                  <div>
                    <p style={{ fontSize: 14, fontWeight: 700 }}>
                      Score: <span style={{ color: 'var(--primary)' }}>{a.risk_score}</span>
                    </p>
                    <p className="hint" style={{ marginTop: 2 }}>{new Date(a.created_at).toLocaleDateString()}</p>
                  </div>
                  <Badge level={a.risk_level} />
                </div>
              </div>
            ))
          )}

          <h3 className="section-title">Uploaded Reports</h3>
          {docs.length === 0 ? (
            <div className="card empty">
              <div className="empty-icon"><IcDoc /></div>
              <h3>No reports yet</h3>
              <p>Upload prescriptions or reports.</p>
              <Link to="/upload" className="btn btn-ghost btn-sm" style={{ width: 'auto' }}>
                <IcUpload size={15} /> Upload Report
              </Link>
            </div>
          ) : (
            docs.slice(0, 3).map((d) => (
              <div className="card card-pad-s" key={d.id}>
                <div className="split">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, flex: 1 }}>
                    <div className="logo-box logo-sm" style={{ background: 'var(--primary-soft)', color: 'var(--primary)', boxShadow: 'none' }}>
                      <IcDoc size={18} />
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <p style={{ fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{d.file_name}</p>
                      <p className="hint">{new Date(d.upload_time).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <a href={d.file_url} target="_blank" rel="noreferrer" style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--primary)' }}>View</a>
                </div>
              </div>
            ))
          )}

          <h3 className="section-title">Medication Reminders</h3>
          {(!patient.medications || patient.medications?.length === 0) ? (
            <div className="card empty">
              <div className="empty-icon"><IcHeart /></div>
              <h3>No medication reminders</h3>
              <p>Add medications during your next assessment.</p>
            </div>
          ) : (
            patient.medications.map((m, i) => (
              <div className="card card-pad-s" key={i}>
                <div className="split">
                  <div>
                    <p style={{ fontSize: 14, fontWeight: 700 }}>{m.name}</p>
                    <p className="hint" style={{ marginTop: 2 }}>
                      {m.dosage || ''} {m.time ? `· ${m.time}` : ''}
                    </p>
                  </div>
                  <span style={{ fontSize: 20 }}>⏰</span>
                </div>
              </div>
            ))
          )}

          <div className="btn-row" style={{ marginTop: 22 }}>
            <Link to="/assessment" className="btn btn-primary">New Assessment</Link>
            <Link to="/upload" className="btn btn-ghost">Upload Report</Link>
          </div>
        </div>
      )}
    </div>
  );
}