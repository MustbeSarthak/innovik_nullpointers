import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHead from '../components/PageHead';
import UiButton from '../components/UiButton';
import { PatientAPI } from '../lib/api';
import { useToast } from '../context/ToastContext';
import { IcCare } from '../components/Icons';

export default function Caretaker() {
  const { showToast } = useToast();
  const [status, setStatus] = useState(null);
  const [form, setForm] = useState({ name: '', relation: '', phone: '', altPhone: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    PatientAPI.get()
      .then((p) => {
        if (p.caretaker) {
          setStatus(p.caretaker);
          setForm({
            name: p.caretaker.name || '',
            relation: p.caretaker.relationship || '',
            phone: p.caretaker.phone || '',
            altPhone: p.caretaker.alt_phone || '',
          });
        }
      })
      .catch(() => {});
  }, []);

  const save = async (e) => {
    e.preventDefault();
    if (!form.name || !form.phone) return showToast('Name and phone are required', 'err');
    setSaving(true);
    try {
      const ct = await PatientAPI.updateCaretaker({
        name: form.name,
        phone: form.phone,
        relationship: form.relation,
        altPhone: form.altPhone,
      });
      setStatus(ct);
      showToast('Caretaker saved');
    } catch (err) {
      showToast(err.message || 'Failed to save', 'err');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page">
      <PageHead title="Caretaker" backTo="/profile" />

      <div className="card fade-in" style={{ textAlign: 'center', padding: 28 }}>
        <div className="logo-box" style={{ width: 72, height: 72, borderRadius: '50%', margin: '0 auto' }}>
          <IcCare size={34} />
        </div>
        {status ? (
          <div style={{ marginTop: 12 }}>
            <p style={{ fontSize: 19, fontWeight: 800 }}>{status.name}</p>
            <p className="hint" style={{ marginTop: 4 }}>
              {status.relationship || ''} · {status.phone}
            </p>
          </div>
        ) : (
          <p className="sub" style={{ fontSize: 14, marginTop: 12 }}>No caretaker assigned yet</p>
        )}
      </div>

      <div className="card fade-in" style={{ marginTop: 16 }}>
        <h3 className="section-title" style={{ margin: 0 }}>Add / Update Caretaker</h3>
        <form onSubmit={save} style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 14 }}>
          <div className="form-group">
            <label className="label">Name</label>
            <input className="input" placeholder="Caretaker name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="form-group">
            <label className="label">Relationship</label>
            <input className="input" placeholder="e.g. Spouse, Parent, Child" value={form.relation} onChange={(e) => setForm({ ...form, relation: e.target.value })} />
          </div>
          <div className="form-grid">
            <div className="form-group">
              <label className="label">Phone</label>
              <input type="tel" className="input" placeholder="+91 XXXXX XXXXX" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="label">Alternate</label>
              <input type="tel" className="input" placeholder="Optional" value={form.altPhone} onChange={(e) => setForm({ ...form, altPhone: e.target.value })} />
            </div>
          </div>
          <UiButton type="submit" className="btn-primary" loading={saving}>
            {saving ? 'Saving…' : 'Save Caretaker'}
          </UiButton>
        </form>
      </div>

      <div className="btn-row" style={{ marginTop: 20 }}>
        <Link to="/profile" className="btn btn-ghost">Back to Profile</Link>
        <Link to="/dashboard" className="btn btn-outline">Dashboard</Link>
      </div>
    </div>
  );
}