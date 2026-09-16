import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PageHead from '../components/PageHead';
import UiButton from '../components/UiButton';
import UploadZone from '../components/UploadZone';
import { useToast } from '../context/ToastContext';
import { PatientAPI, AssessmentAPI, UploadAPI } from '../lib/api';
import { calculateRisk, SYMPTOM_OPTIONS, HISTORY_OPTIONS } from '../lib/risk';
import { IcCheck, IcWarn, IcPlus, IcUpload } from '../components/Icons';

const TOTAL = 8;

export default function Assessment() {
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [step, setStep] = useState(0);
  const [anim, setAnim] = useState(false);
  const [form, setForm] = useState({
    name: '', age: '', gender: '', blood: '', height: '', weight: '', phone: '',
    ctName: '', ctRelation: '', ctPhone: '', ctAltPhone: '',
    history: {}, symptoms: {}, pain: 0, smoking: '', alcohol: '', sleep: '', exercise: '',
    meds: [], notes: '', files: [],
  });
  const [skipped, setSkipped] = useState({});
  const [critical, setCritical] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [step]);

  const set = (key, val) => {
    setForm((f) => ({ ...f, [key]: val }));
    setAnim(true);
    clearTimeout(animT.current);
    animT.current = setTimeout(() => setAnim(false), 450);
  };
  const animT = useRef(null);

  const personalFilled = !!(form.name || form.age || form.gender || form.blood || form.height || form.weight || form.phone);
  const emergencyFilled = !!(form.ctName || form.ctPhone || form.ctRelation);
  const historyFilled = Object.values(form.history).some(Boolean);
  const symptomsFilled = Object.values(form.symptoms).some(Boolean) || Number(form.pain) > 0;
  const lifestyleFilled = !!(form.smoking || form.alcohol || form.sleep || form.exercise);
  const medsFilled = form.meds.length > 0;
  const filesFilled = form.files.length > 0;
  const notesFilled = !!form.notes;

  const buttonState = (() => {
    if (step === 0) return personalFilled ? 'next' : 'skip';
    if (step === 1) return emergencyFilled ? 'next' : 'skip';
    if (step === 2) return historyFilled ? 'next' : 'skip';
    if (step === 3) return symptomsFilled ? 'next' : 'skip';
    if (step === 4) return lifestyleFilled ? 'next' : 'skip';
    if (step === 5) return medsFilled ? 'next' : 'skip';
    if (step === 6) return filesFilled ? 'next' : 'skip';
    if (step === 7) return notesFilled ? 'submit' : 'skip-submit';
    return 'next';
  })();

  const toggleChip = (group, key) => {
    setForm((f) => ({ ...f, [group]: { ...f[group], [key]: !f[group][key] } }));
    setAnim(true);
    clearTimeout(animT.current);
    animT.current = setTimeout(() => setAnim(false), 500);
  };

  const addMed = () => set('meds', [...form.meds, { name: '', dosage: '', time: '' }]);
  const updateMed = (i, key, value) => {
    const meds = form.meds.slice();
    meds[i] = { ...meds[i], [key]: value };
    set('meds', meds);
  };
  const removeMed = (i) => set('meds', form.meds.filter((_, idx) => idx !== i));

  const progress = ((step + 1) / TOTAL) * 100;

  const goNext = () => {
    if (step < TOTAL - 1) setStep(step + 1);
  };

  const submit = async () => {
    setBusy(true);
    const risk = calculateRisk(form.symptoms || {});
    try {
      /* Step 0 – Personal details (only send if not fully skipped) */
      const hasPersonal = form.name || form.age || form.gender || form.blood || form.height || form.weight || form.phone;
      if (!skipped[0] || hasPersonal) {
        const patientData = {};
        if (form.name) patientData.name = form.name;
        if (form.age) patientData.age = parseInt(form.age);
        if (form.gender) patientData.gender = form.gender;
        if (form.blood) patientData.blood_group = form.blood;
        if (form.height) patientData.height = parseFloat(form.height);
        if (form.weight) patientData.weight = parseFloat(form.weight);
        if (form.phone) patientData.phone = form.phone;

        /* Step 2 – Medical History */
        const activeHistory = Object.keys(form.history).filter((k) => form.history[k]);
        patientData.medical_history = activeHistory.length > 0
          ? activeHistory.reduce((a, k) => ({ ...a, [k]: true }), {})
          : {};

        /* Step 4 – Lifestyle */
        patientData.lifestyle = {
          smoking: form.smoking || '',
          alcohol: form.alcohol || '',
          sleep: form.sleep || '',
          exercise: form.exercise || '',
        };

        await PatientAPI.update(patientData);
      }

      /* Step 1 – Emergency contact (only if filled) */
      if (form.ctName && !skipped[1]) {
        await PatientAPI.updateCaretaker({
          name: form.ctName,
          relationship: form.ctRelation || '',
          phone: form.ctPhone || '',
          altPhone: form.ctAltPhone || '',
        });
      }

      /* Step 6 – Files (only if present) */
      if (form.files.length > 0) {
        for (const f of form.files) {
          const fd = new FormData();
          fd.append('report', f);
          await UploadAPI.upload(fd);
        }
      }

      /* Always create assessment record */
      await AssessmentAPI.create({
        symptoms: form.symptoms || {},
        pain_level: form.pain ? parseInt(form.pain) : 0,
        medications: form.meds.filter((m) => m.name),
        notes: form.notes || '',
        risk_level: risk.level,
        risk_score: risk.score,
      });

      if (risk.level === 'Critical') {
        setCritical(true);
        try {
          new Audio('/alarm.mp3').play().catch(() => {});
        } catch {}
        if ('vibrate' in navigator) navigator.vibrate([500, 200, 500]);
        /* Alert is auto-created by the backend when risk is Critical */
      } else {
        showToast(`Assessment complete · Risk: ${risk.level} (${risk.score})`);
        setTimeout(() => navigate('/dashboard'), 600);
      }
    } catch (err) {
      showToast(err.message || 'Failed to submit assessment', 'err');
    } finally {
      setBusy(false);
    }
  };

  const primaryAction = () => {
    if (buttonState === 'submit' || buttonState === 'skip-submit') {
      if (buttonState === 'skip-submit') setSkipped((s) => ({ ...s, [step]: true }));
      return submit();
    }
    if (buttonState === 'skip') {
      setSkipped((s) => ({ ...s, [step]: true }));
    }
    goNext();
  };

  const primaryLabel = (() => {
    if (buttonState === 'skip') return 'Skip →';
    if (buttonState === 'next') return 'Next →';
    if (buttonState === 'skip-submit') return 'Skip & Submit';
    return 'Submit Assessment';
  })();

  return (
    <div className="page">
      <PageHead title="Health Assessment" backTo="/" />

      <div className="progress-track">
        <div className="progress-fill" style={{ width: progress + '%' }} />
      </div>
      <div className="section-dots">
        {Array.from({ length: TOTAL }).map((_, i) => (
          <span key={i} className={`dot ${i === step ? 'active' : i < step ? 'done' : ''}`} />
        ))}
      </div>

      {/* 0 · Personal */}
      {step === 0 && (
        <div className="card fade-in">
          <h2 className="section-title" style={{ margin: 0 }}>Personal Details</h2>
          <div style={{ marginTop: 14 }}>
            <div className="form-group">
              <label className="label">Full Name</label>
              <input className="input" placeholder="Enter your full name" value={form.name} onChange={(e) => set('name', e.target.value)} />
            </div>
            <div className="form-grid">
              <div className="form-group">
                <label className="label">Age</label>
                <input type="number" className="input" placeholder="Age" value={form.age} onChange={(e) => set('age', e.target.value)} />
              </div>
              <div className="form-group">
                <label className="label">Gender</label>
                <select className="select" value={form.gender} onChange={(e) => set('gender', e.target.value)}>
                  <option value="">Select</option>
                  <option>Male</option>
                  <option>Female</option>
                  <option>Other</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label className="label">Blood Group</label>
              <select className="select" value={form.blood} onChange={(e) => set('blood', e.target.value)}>
                <option value="">Select</option>
                {['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map((b) => (
                  <option key={b}>{b}</option>
                ))}
              </select>
            </div>
            <div className="form-grid">
              <div className="form-group">
                <label className="label">Height (cm)</label>
                <input type="number" className="input" placeholder="170" value={form.height} onChange={(e) => set('height', e.target.value)} />
              </div>
              <div className="form-group">
                <label className="label">Weight (kg)</label>
                <input type="number" className="input" placeholder="70" value={form.weight} onChange={(e) => set('weight', e.target.value)} />
              </div>
            </div>
            <div className="form-group">
              <label className="label">Phone</label>
              <input type="tel" className="input" placeholder="+91 XXXXX XXXXX" value={form.phone} onChange={(e) => set('phone', e.target.value)} />
            </div>
          </div>
          <div className="btn-row">
            <UiButton className={`btn-primary${anim ? ' grow' : ''}`} onClick={primaryAction}>
              {primaryLabel}
            </UiButton>
          </div>
        </div>
      )}

      {/* 1 · Emergency Contact */}
      {step === 1 && (
        <div className="card fade-in">
          <h2 className="section-title" style={{ margin: 0 }}>Emergency Contact</h2>
          <p className="hint" style={{ margin: '6px 0 14px' }}>
            Optional — add someone who should be notified in an emergency.
          </p>
          <div className="form-group">
            <label className="label">Caretaker Name</label>
            <input className="input" placeholder="Full name" value={form.ctName} onChange={(e) => set('ctName', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="label">Relationship</label>
            <input className="input" placeholder="e.g. Spouse, Parent" value={form.ctRelation} onChange={(e) => set('ctRelation', e.target.value)} />
          </div>
          <div className="form-grid">
            <div className="form-group">
              <label className="label">Phone</label>
              <input type="tel" className="input" placeholder="+91 XXXXX XXXXX" value={form.ctPhone} onChange={(e) => set('ctPhone', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="label">Alternate</label>
              <input type="tel" className="input" placeholder="Optional" value={form.ctAltPhone} onChange={(e) => set('ctAltPhone', e.target.value)} />
            </div>
          </div>
          <div className="btn-row">
            <UiButton className="btn-outline" onClick={() => setStep(0)}>← Back</UiButton>
            <UiButton className={`btn-primary${anim ? ' shake' : ''}`} onClick={primaryAction}>
              {primaryLabel}
            </UiButton>
          </div>
        </div>
      )}

      {/* 2 · Medical History */}
      {step === 2 && (
        <div className="card fade-in">
          <h2 className="section-title" style={{ margin: 0 }}>Medical History</h2>
          <p className="hint" style={{ margin: '6px 0 14px' }}>Select all that apply — or skip if you have no past diseases.</p>
          <div className="chip-grid">
            {HISTORY_OPTIONS.map((opt) => {
              const on = !!form.history[opt.value];
              return (
                <div key={opt.value} className={`chip ${on ? 'on' : ''}`} onClick={() => toggleChip('history', opt.value)}>
                  <span className="check">{on && <IcCheck />}</span>
                  {opt.label}
                </div>
              );
            })}
          </div>
          <div className="btn-row">
            <UiButton className="btn-outline" onClick={() => setStep(1)}>← Back</UiButton>
            <UiButton
              className={`btn-primary${anim ? ' grow' : ''}`}
              onClick={primaryAction}
            >
              {primaryLabel}
            </UiButton>
          </div>
        </div>
      )}

      {/* 3 · Symptoms */}
      {step === 3 && (
        <div className="card fade-in">
          <h2 className="section-title" style={{ margin: 0 }}>Current Symptoms</h2>
          <div style={{ padding: '8px 0 6px' }}>
            <label className="label">Pain Level</label>
            <input
              type="range"
              min="0"
              max="10"
              value={form.pain}
              onChange={(e) => set('pain', e.target.value)}
              style={{ width: '100%', accentColor: 'var(--primary)' }}
            />
            <div className="split" style={{ marginTop: 4 }}>
              <span className="hint">No pain</span>
              <span style={{ fontSize: 24, fontWeight: 800, color: 'var(--primary)' }}>{form.pain}</span>
              <span className="hint">Worst pain</span>
            </div>
          </div>

          <div className="chip-grid" style={{ marginTop: 8 }}>
            {SYMPTOM_OPTIONS.map((opt) => {
              const on = !!form.symptoms[opt.value];
              return (
                <div
                  key={opt.value}
                  className={`chip ${on ? 'on' : ''}`}
                  style={opt.critical && !on ? { borderColor: 'var(--danger-soft)' } : undefined}
                  onClick={() => toggleChip('symptoms', opt.value)}
                >
                  <span className="check">{on && <IcCheck />}</span>
                  {opt.label}
                  {opt.critical && on && <IcWarn size={14} style={{ color: 'var(--danger)', marginLeft: 'auto' }} />}
                </div>
              );
            })}
          </div>

          <div className="disclaimer" style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginTop: 14 }}>
            <IcWarn size={16} style={{ color: 'var(--danger)', flexShrink: 0 }} />
            <span>Red-highlighted symptoms (critical) trigger an immediate critical alert.</span>
          </div>

          <div className="btn-row">
            <UiButton className="btn-outline" onClick={() => setStep(2)}>← Back</UiButton>
            <UiButton className={`btn-primary${anim ? ' grow' : ''}`} onClick={primaryAction}>{primaryLabel}</UiButton>
          </div>
        </div>
      )}

      {/* 4 · Lifestyle */}
      {step === 4 && (
        <div className="card fade-in">
          <h2 className="section-title" style={{ margin: 0 }}>Lifestyle</h2>
          <div style={{ marginTop: 14 }}>
            <div className="form-group">
              <label className="label">Smoking</label>
              <select className="select" value={form.smoking} onChange={(e) => set('smoking', e.target.value)}>
                <option value="">Select</option>
                <option>Never</option>
                <option>Former Smoker</option>
                <option>Occasional</option>
                <option>Regular</option>
              </select>
            </div>
            <div className="form-group">
              <label className="label">Alcohol</label>
              <select className="select" value={form.alcohol} onChange={(e) => set('alcohol', e.target.value)}>
                <option value="">Select</option>
                <option>Never</option>
                <option>Occasional</option>
                <option>Moderate</option>
                <option>Heavy</option>
              </select>
            </div>
            <div className="form-grid">
              <div className="form-group">
                <label className="label">Sleep</label>
                <select className="select" value={form.sleep} onChange={(e) => set('sleep', e.target.value)}>
                  <option value="">Select</option>
                  <option>Less than 4</option>
                  <option>4 - 6</option>
                  <option>6 - 8</option>
                  <option>More than 8</option>
                </select>
              </div>
              <div className="form-group">
                <label className="label">Exercise</label>
                <select className="select" value={form.exercise} onChange={(e) => set('exercise', e.target.value)}>
                  <option value="">Select</option>
                  <option>None</option>
                  <option>Light (1-2/week)</option>
                  <option>Moderate (3-4/week)</option>
                  <option>Intense (5+/week)</option>
                </select>
              </div>
            </div>
          </div>
          <div className="btn-row">
            <UiButton className="btn-outline" onClick={() => setStep(3)}>← Back</UiButton>
            <UiButton className={`btn-primary${anim ? ' grow' : ''}`} onClick={primaryAction}>{primaryLabel}</UiButton>
          </div>
        </div>
      )}

      {/* 5 · Medication */}
      {step === 5 && (
        <div className="card fade-in">
          <h2 className="section-title" style={{ margin: 0 }}>Current Medication</h2>
          <p className="hint" style={{ margin: '6px 0 14px' }}>
            Add any medicines you take regularly — or skip if you're taking none.
          </p>

          {form.meds.map((m, i) => (
            <div className="card card-pad-s" style={{ marginBottom: 12 }} key={i}>
              <div className="split" style={{ marginBottom: 10 }}>
                <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--primary-strong)' }}>Medication {i + 1}</span>
                <button className="icon-btn" style={{ width: 32, height: 32 }} onClick={() => removeMed(i)} title="Remove">
                  ✕
                </button>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <input className="input" placeholder="Medicine name" value={m.name} onChange={(e) => updateMed(i, 'name', e.target.value)} />
                <div className="form-grid">
                  <input className="input" placeholder="Dosage (e.g. 500mg)" value={m.dosage} onChange={(e) => updateMed(i, 'dosage', e.target.value)} />
                  <input className="input" placeholder="Time (e.g. Night)" value={m.time} onChange={(e) => updateMed(i, 'time', e.target.value)} />
                </div>
              </div>
            </div>
          ))}

          <UiButton className="btn-ghost" onClick={addMed}>
            <IcPlus size={18} /> Add Medication
          </UiButton>

          <div className="btn-row">
            <UiButton className="btn-outline" onClick={() => setStep(4)}>← Back</UiButton>
            <UiButton className={`btn-primary${anim ? ' grow' : ''}`} onClick={primaryAction}>
              {primaryLabel}
            </UiButton>
          </div>
        </div>
      )}

      {/* 6 · Upload */}
      {step === 6 && (
        <div className="card fade-in">
          <h2 className="section-title" style={{ margin: 0 }}>Upload Reports</h2>
          <p className="hint" style={{ margin: '6px 0 14px' }}>Optional — attach any existing medical reports.</p>
          <UploadZone onFile={(file) => set('files', [...form.files, file])} />
          {form.files.map((f, i) => (
            <div className="file-preview" key={i}>
              <IcUpload size={22} style={{ color: 'var(--primary)' }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontWeight: 700, fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.name}</p>
                <p className="hint">{(f.size / 1024).toFixed(1)} KB</p>
              </div>
              <button className="icon-btn" style={{ width: 30, height: 30 }} onClick={() => set('files', form.files.filter((_, idx) => idx !== i))}>
                ✕
              </button>
            </div>
          ))}
          <div className="btn-row">
            <UiButton className="btn-outline" onClick={() => setStep(5)}>← Back</UiButton>
            <UiButton className={`btn-primary${anim ? ' grow' : ''}`} onClick={primaryAction}>
              {primaryLabel}
            </UiButton>
          </div>
        </div>
      )}

      {/* 7 · Notes */}
      {step === 7 && (
        <div className="card fade-in">
          <h2 className="section-title" style={{ margin: 0 }}>Additional Notes</h2>
          <div className="form-group" style={{ marginTop: 14 }}>
            <textarea
              className="textarea"
              rows={6}
              placeholder="Any additional information about your condition..."
              value={form.notes}
              onChange={(e) => set('notes', e.target.value)}
            />
          </div>
          <div className="btn-row">
            <UiButton className="btn-outline" onClick={() => setStep(6)}>← Back</UiButton>
            <UiButton className="btn-primary" loading={busy} onClick={primaryAction}>
              {busy ? 'Submitting…' : primaryLabel}
            </UiButton>
          </div>
        </div>
      )}

      {critical && (
        <div className="critical-overlay">
          <div className="logo-box" style={{ width: 84, height: 84, borderRadius: 28, background: 'rgba(255,255,255,0.15)', boxShadow: 'none' }}>
            <IcWarn size={44} />
          </div>
          <h1 style={{ fontSize: 28, letterSpacing: 1 }}>CRITICAL CONDITION DETECTED</h1>
          <p style={{ fontSize: 15, opacity: 0.92 }}>A critical alert has been raised.</p>
          <p style={{ fontSize: 13, opacity: 0.8 }}>Stay calm and seek emergency help immediately.</p>
          <UiButton
            className="btn"
            style={{ background: '#fff', color: '#b91c1c', width: 'auto', marginTop: 18, borderRadius: 30, padding: '13px 40px' }}
            onClick={() => {
              setCritical(false);
              showToast('Alert acknowledged');
              setTimeout(() => navigate('/dashboard'), 300);
            }}
          >
            Acknowledge
          </UiButton>
        </div>
      )}
    </div>
  );
}