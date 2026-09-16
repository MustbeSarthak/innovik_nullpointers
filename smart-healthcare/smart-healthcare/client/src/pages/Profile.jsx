import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import PageHead from '../components/PageHead';
import ThemeToggle from '../components/ThemeToggle';
import UiButton from '../components/UiButton';
import { AuthAPI, PatientAPI, UploadAPI } from '../lib/api';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { IcUser, IcCare, IcDoc, IcLogout } from '../components/Icons';

export default function Profile() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { setUser } = useAuth();
  const [patient, setPatient] = useState(null);
  const [docs, setDocs] = useState([]);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ age: '', gender: '', blood: '', height: '', weight: '', phone: '' });
  const [saving, setSaving] = useState(false);

  const load = () =>
    Promise.all([PatientAPI.get(), UploadAPI.list()]).then(([p, files]) => {
      setPatient(p);
      setDocs(files || []);
      setForm({
        age: p.age || '',
        gender: p.gender || '',
        blood: p.blood_group || '',
        height: p.height || '',
        weight: p.weight || '',
        phone: p.phone || '',
      });
    });

  useEffect(() => {
    load().catch(() => {});
  }, []);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await PatientAPI.update({
        age: form.age ? parseInt(form.age) : null,
        gender: form.gender || null,
        blood_group: form.blood || null,
        height: form.height ? parseFloat(form.height) : null,
        weight: form.weight ? parseFloat(form.weight) : null,
        phone: form.phone || null,
      });
      showToast('Profile updated');
      setEditing(false);
      load();
    } catch (err) {
      showToast(err.message || 'Update failed', 'err');
    } finally {
      setSaving(false);
    }
  };

  const logout = async () => {
    await AuthAPI.logout();
    setUser(null);
    navigate('/login');
  };

  if (!patient) {
    return (
      <div className="page">
        <PageHead title="Profile" backTo="/" />
        <div className="card empty"><span className="spinner" /></div>
      </div>
    );
  }

  const history = patient.medical_history || {};
  const conditions = Object.keys(history).filter((k) => history[k]);

  const infoItems = [
    ['Age', patient.age || '-'],
    ['Gender', patient.gender || '-'],
    ['Blood Group', patient.blood_group || '-'],
    ['Height', patient.height ? `${patient.height} cm` : '-'],
    ['Weight', patient.weight ? `${patient.weight} kg` : '-'],
    ['Phone', patient.phone || '-'],
  ];

  return (
    <div className="page">
      <PageHead
        title="Profile"
        backTo="/"
        right={
          <div className="split" style={{ gap: 8 }}>
            <ThemeToggle />
            <button className="icon-btn" onClick={logout} title="Sign out">
              <IcLogout size={17} />
            </button>
          </div>
        }
      />

      <div className="card fade-in" style={{ textAlign: 'center', padding: 26 }}>
        <div className="logo-box" style={{ width: 76, height: 76, borderRadius: '50%', margin: '0 auto' }}>
          <IcUser size={36} />
        </div>
        <h2 style={{ fontSize: 21, fontWeight: 800, marginTop: 12 }}>{patient.name}</h2>
        <p className="hint">{patient.email}</p>
      </div>

      <h3 className="section-title">Personal Information</h3>
      <div className="card" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        {infoItems.map(([k, v]) => (
          <div key={k}>
            <p className="hint" style={{ fontSize: 11, fontWeight: 700 }}>{k}</p>
            <p style={{ fontWeight: 700, marginTop: 2, fontSize: 14 }}>{v}</p>
          </div>
        ))}
      </div>

      <h3 className="section-title">Medical History</h3>
      <div className="card">
        {conditions.length === 0 ? (
          <p className="hint">No medical history recorded.</p>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {conditions.map((c) => (
              <span key={c} className="badge badge-moderate" style={{ textTransform: 'none' }}>
                {c.replace(/([A-Z])/g, ' $1').toLowerCase()}
              </span>
            ))}
          </div>
        )}
      </div>

      <h3 className="section-title">Caretaker</h3>
      <div className="card">
        {patient.caretaker ? (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div className="logo-box logo-sm" style={{ background: 'var(--success-soft)', color: 'var(--success)', boxShadow: 'none' }}>
                <IcCare size={18} />
              </div>
              <div>
                <p style={{ fontWeight: 700, fontSize: 14 }}>
                  {patient.caretaker.name}{' '}
                  <span className="hint">({patient.caretaker.relationship})</span>
                </p>
                <p className="hint">{patient.caretaker.phone}</p>
              </div>
            </div>
            <Link to="/caretaker" className="btn btn-ghost btn-sm" style={{ marginTop: 12, width: 'auto' }}>Edit</Link>
          </div>
        ) : (
          <div>
            <p className="hint">No caretaker assigned.</p>
            <Link to="/caretaker" className="btn btn-ghost btn-sm" style={{ marginTop: 12, width: 'auto' }}>Add Caretaker</Link>
          </div>
        )}
      </div>

      <h3 className="section-title">Documents</h3>
      <div className="card">
        {docs.length ? (
          docs.map((d) => (
            <div className="split" key={d.id} style={{ padding: '6px 0' }}>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', minWidth: 0 }}>
                <IcDoc size={18} style={{ color: 'var(--primary)' }} />
                <p style={{ fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{d.file_name}</p>
              </div>
              <a href={d.file_url} target="_blank" rel="noreferrer" style={{ fontSize: 12, fontWeight: 700, color: 'var(--primary)' }}>View</a>
            </div>
          ))
        ) : (
          <p className="hint">No documents uploaded.</p>
        )}
      </div>

      <div className="btn-row" style={{ marginTop: 22 }}>
        <UiButton className="btn-primary" onClick={() => setEditing(true)}>
          Edit Profile
        </UiButton>
        <Link to="/caretaker" className="btn btn-ghost">Caretaker</Link>
      </div>

      {editing && (
        <div className="modal" onClick={() => setEditing(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 18 }}>Edit Profile</h3>
            <form onSubmit={save} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="form-grid">
                <div>
                  <label className="label">Age</label>
                  <input className="input" type="number" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} />
                </div>
                <div>
                  <label className="label">Gender</label>
                  <select className="select" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
                    <option value="">Select</option>
                    <option>Male</option>
                    <option>Female</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="label">Blood Group</label>
                <select className="select" value={form.blood} onChange={(e) => setForm({ ...form, blood: e.target.value })}>
                  <option value="">Select</option>
                  {['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map((b) => <option key={b}>{b}</option>)}
                </select>
              </div>
              <div className="form-grid">
                <div>
                  <label className="label">Height (cm)</label>
                  <input className="input" type="number" value={form.height} onChange={(e) => setForm({ ...form, height: e.target.value })} />
                </div>
                <div>
                  <label className="label">Weight (kg)</label>
                  <input className="input" type="number" value={form.weight} onChange={(e) => setForm({ ...form, weight: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="label">Phone</label>
                <input className="input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </div>
              <div className="btn-row" style={{ margin: 0 }}>
                <UiButton type="button" className="btn-outline" onClick={() => setEditing(false)}>Cancel</UiButton>
                <UiButton type="submit" className="btn-primary" loading={saving}>Save</UiButton>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}