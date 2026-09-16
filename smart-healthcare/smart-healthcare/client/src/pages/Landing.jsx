import { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import ThemeToggle from '../components/ThemeToggle';
import { IcHeart, IcAssess, IcUpload, IcClock, IcSpark, IcChat, IcCamera, IcWarn, IcShield } from '../components/Icons';

const SIMULATION_STATES = ['normal', 'medium', 'critical'];
const formatMetric = (value) => Number.isFinite(Number(value)) ? Number(value).toFixed(2) : '--';
const stateMeta = {
  normal: { label: 'Normal', tone: 'good', text: 'Vitals are stable.' },
  medium: { label: 'Medium', tone: 'warn', text: 'Hospitalization should be considered.' },
  critical: { label: 'Critical', tone: 'danger', text: 'Critical signal detected — SMS sent to caretaker.' },
};

const tokenHeaders = () => {
  const token = localStorage.getItem('smart_healthcare_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export default function Landing() {
  const { user, loading } = useAuth();
  const { showToast } = useToast();
  const [running, setRunning] = useState(false);
  const [state, setState] = useState('normal');
  const [reading, setReading] = useState(null);
  const [alertBox, setAlertBox] = useState(null);

  const loadLatestReading = async () => {
    if (!user) return;
    try {
      const { data } = await axios.get('/api/v1/vitals/latest', {
        headers: tokenHeaders(),
      });
      if (data) setReading(data);
    } catch {
      setReading(null);
    }
  };

  const applyState = async (nextState) => {
    if (!user) return;

    try {
      await axios.post(
        '/api/v1/vitals/simulator/start',
        {
          profile: user?.gender === 'female' ? 'female' : 'male',
          state: nextState,
          interval_seconds: 1.5,
          scenario: 'NORMAL',
        },
        { headers: tokenHeaders() }
      );
      setState(nextState);

      if (nextState === 'critical') {
        setAlertBox({
          type: 'danger',
          message: 'Critical reading detected. SMS sent to caretaker.',
        });
        showToast('Critical reading detected — SMS sent to caretaker', 'err');
      } else if (nextState === 'medium') {
        setAlertBox({
          type: 'warn',
          message: 'Medium alert: hospitalization should be considered.',
        });
      } else {
        setAlertBox(null);
      }
    } catch (error) {
      console.error('simulator start failed', error);
    }
  };

  const randomizeReading = (base, nextState) => {
    if (!base) return null;

    const intensity = nextState === 'critical' ? 1.8 : nextState === 'medium' ? 1.2 : 0.45;
    const wave = Math.sin((Date.now() / 1000) + 1) * intensity;
    const next = { ...base };

    next.heart_rate = Number(Math.max(52, Math.min(170, Number(base.heart_rate || 72) + (Math.random() * 10 - 5) + wave * 8)).toFixed(2));
    next.systolic_bp = Number(Math.max(80, Math.min(200, Number(base.systolic_bp || 118) + (Math.random() * 12 - 6) + wave * 10)).toFixed(2));
    next.diastolic_bp = Number(Math.max(50, Math.min(120, Number(base.diastolic_bp || 78) + (Math.random() * 10 - 5) + wave * 7)).toFixed(2));
    next.spo2 = Number(Math.max(78, Math.min(100, Number(base.spo2 || 98) + (Math.random() * 4 - 2) - wave * 5)).toFixed(2));
    next.temperature = Number(Math.max(35.5, Math.min(40.5, Number(base.temperature || 37) + (Math.random() * 0.8 - 0.4) + wave * 0.7)).toFixed(2));
    next.glucose = Number(Math.max(68, Math.min(350, Number(base.glucose || 120) + (Math.random() * 30 - 15) + wave * 18)).toFixed(2));
    next.simulator_state = nextState;
    next.source = 'SIMULATED';

    return next;
  };

  const stopSimulation = async () => {
    if (!user) return;
    try {
      await axios.post('/api/v1/vitals/simulator/stop', {}, { headers: tokenHeaders() });
    } catch (error) {
      console.error('simulator stop failed', error);
    }
    setRunning(false);
    setAlertBox(null);
    setState('normal');
  };

  const startSimulation = async () => {
    if (!user) return;
    setRunning(true);
    await applyState('normal');
  };

  useEffect(() => {
    if (!user) return;
    loadLatestReading();
  }, [user]);

  useEffect(() => {
    if (!running || !user) return;

    const refresh = setInterval(async () => {
      try {
        const { data } = await axios.get('/api/v1/vitals/latest', { headers: tokenHeaders() });
        if (data) {
          setReading(randomizeReading(data, state));
        }
      } catch {
        setReading(null);
      }
    }, 1500);

    const cycle = setInterval(() => {
      setState((prev) => {
        const index = SIMULATION_STATES.indexOf(prev);
        const next = SIMULATION_STATES[(index + 1) % SIMULATION_STATES.length];
        applyState(next);
        return next;
      });
    }, 7000);

    return () => {
      clearInterval(refresh);
      clearInterval(cycle);
    };
  }, [running, user, state]);

  return (
    <div className="page" style={{ paddingTop: 22 }}>
      <div className="split">
        <div className="logo-box">
          <IcHeart size={30} />
        </div>
        <ThemeToggle />
      </div>

      <div style={{ marginTop: 22 }}>
        <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: '-0.6px' }}>
          {loading ? 'Smart Healthcare' : user ? `Welcome, ${user.name.split(' ')[0]} 👋` : 'Smart Healthcare'}
        </h1>
        <p className="sub" style={{ fontSize: 14, marginTop: 6 }}>
          Your health, always monitored — at your fingertips.
        </p>
      </div>

      <div className="card live-monitor-card" style={{ marginTop: 18 }}>
        <div className="split" style={{ alignItems: 'center' }}>
          <div>
            <p className="monitor-label">Live Health Monitor</p>
            <h3 className="monitor-title">{stateMeta[state].label}</h3>
          </div>
          <span className={`status-pill ${stateMeta[state].tone}`}>
            {stateMeta[state].label}
          </span>
        </div>

        <div className="monitor-grid">
          <div className="metric-box">
            <span>Heart rate</span>
            <strong>{formatMetric(reading?.heart_rate)} bpm</strong>
          </div>
          <div className="metric-box">
            <span>BP</span>
            <strong>{reading ? `${formatMetric(reading.systolic_bp)}/${formatMetric(reading.diastolic_bp)}` : '--/--'} mmHg</strong>
          </div>
          <div className="metric-box">
            <span>SpO2</span>
            <strong>{formatMetric(reading?.spo2)}%</strong>
          </div>
          <div className="metric-box">
            <span>Temp</span>
            <strong>{formatMetric(reading?.temperature)}°C</strong>
          </div>
          <div className="metric-box">
            <span>Glucose</span>
            <strong>{formatMetric(reading?.glucose)} mg/dL</strong>
          </div>
          <div className="metric-box">
            <span>Signal</span>
            <strong>{reading?.source ? reading.source.toLowerCase() : 'idle'}</strong>
          </div>
        </div>

        {alertBox && (
          <div className={`alert-box ${alertBox.type}`}>
            {alertBox.message}
          </div>
        )}

        {!user ? (
          <div className="simulator-cta">
            <Link to="/login" className="btn btn-primary btn-sm">Log in to enable simulation</Link>
          </div>
        ) : (
          <div className="simulator-cta">
            <button className="btn btn-primary btn-sm" onClick={running ? stopSimulation : startSimulation}>
              {running ? 'Stop simulation' : 'Start simulation'}
            </button>
          </div>
        )}
      </div>

      <div className="card ai-hero fade-in" style={{ marginTop: 20 }}>
        <div className="split">
          <div>
            <span className="badge" style={{ background: 'rgba(255,255,255,0.2)', color: '#fff' }}>
              <IcSpark size={13} /> NEW
            </span>
            <h2 style={{ fontSize: 20, marginTop: 10 }}>AI Health Assistant</h2>
            <p style={{ fontSize: 13.5, marginTop: 6, opacity: 0.92, lineHeight: 1.5 }}>
              Ask about everyday symptoms or scan a skin photo — understand rashes, fever, cold
              and more with simple, reassuring guidance.
            </p>
          </div>
        </div>
        <div className="btn-row" style={{ marginTop: 16 }}>
          <Link to="/assistant?mode=chat" className="btn btn-ghost" style={{ background: 'rgba(255,255,255,0.18)', color: '#fff', boxShadow: 'none' }}>
            <IcChat size={17} /> Chat
          </Link>
          <Link to="/assistant?mode=scan" className="btn" style={{ background: '#fff', color: 'var(--primary-strong)', boxShadow: 'none' }}>
            <IcCamera size={17} /> Scan Skin
          </Link>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 18 }}>
        <Link to="/assessment" className="card tappable" style={{ padding: 18 }}>
          <div className="logo-box logo-sm" style={{ background: 'var(--primary-soft)', color: 'var(--primary)', boxShadow: 'none' }}>
            <IcAssess />
          </div>
          <h3 style={{ fontSize: 15, marginTop: 12 }}>Start Assessment</h3>
          <p className="hint" style={{ marginTop: 4 }}>Complete your health checkup</p>
        </Link>

        <Link to="/upload" className="card tappable" style={{ padding: 18 }}>
          <div className="logo-box logo-sm" style={{ background: 'var(--success-soft)', color: 'var(--success)', boxShadow: 'none' }}>
            <IcUpload />
          </div>
          <h3 style={{ fontSize: 15, marginTop: 12 }}>Upload Reports</h3>
          <p className="hint" style={{ marginTop: 4 }}>Store medical documents</p>
        </Link>

        <Link to="/history" className="card tappable" style={{ padding: 18 }}>
          <div className="logo-box logo-sm" style={{ background: 'var(--warn-soft)', color: 'var(--warn)', boxShadow: 'none' }}>
            <IcClock />
          </div>
          <h3 style={{ fontSize: 15, marginTop: 12 }}>View History</h3>
          <p className="hint" style={{ marginTop: 4 }}>Track your health timeline</p>
        </Link>

        <Link to="/dashboard" className="card tappable" style={{ padding: 18 }}>
          <div className="logo-box logo-sm" style={{ background: 'var(--primary-soft)', color: 'var(--primary)', boxShadow: 'none' }}>
            <IcShield />
          </div>
          <h3 style={{ fontSize: 15, marginTop: 12 }}>Dashboard</h3>
          <p className="hint" style={{ marginTop: 4 }}>Your health overview</p>
        </Link>
      </div>

      {!user && !loading && (
        <div className="card" style={{ marginTop: 18, textAlign: 'center', padding: '18px 16px' }}>
          <p className="sub" style={{ fontSize: 14 }}>
            Save your assessments and reports with an account.
          </p>
          <div className="btn-row" style={{ marginTop: 14 }}>
            <Link to="/login" className="btn btn-ghost btn-sm" style={{ width: 'auto' }}>Sign in</Link>
            <Link to="/signup" className="btn btn-primary btn-sm" style={{ width: 'auto' }}>Create account</Link>
          </div>
        </div>
      )}

      <div className="card" style={{ marginTop: 18, padding: '16px 18px', display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        <div style={{ color: 'var(--danger)' }}>
          <IcWarn size={20} />
        </div>
        <div>
          <p style={{ fontSize: 13, fontWeight: 700 }}>Emergency?</p>
          <p className="hint" style={{ marginTop: 3 }}>
            Call your local emergency number right away or visit the nearest hospital. This app is
            a guide, not a replacement for medical care.
          </p>
        </div>
      </div>
    </div>
  );
}