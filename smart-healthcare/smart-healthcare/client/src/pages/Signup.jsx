import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthAPI } from '../lib/api';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import UiButton from '../components/UiButton';
import { IcUser } from '../components/Icons';
import ThemeToggle from '../components/ThemeToggle';

export default function Signup() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { setUser } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!name || !email || !password) return showToast('Please fill in all fields', 'err');
    if (password !== confirm) return showToast('Passwords do not match', 'err');
    if (password.length < 6) return showToast('Password must be at least 6 characters', 'err');
    setBusy(true);
    try {
      const data = await AuthAPI.register({ name, email, password });
      setUser(data.user);
      showToast('Account created');
      setTimeout(() => navigate('/assessment'), 600);
    } catch (err) {
      showToast(err.message || 'Registration failed', 'err');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center' }}>
      <div style={{ width: '100%', maxWidth: 420, margin: '0 auto' }}>
        <div className="split" style={{ marginBottom: 18 }}>
          <div className="logo-box">
            <IcUser size={28} />
          </div>
          <ThemeToggle />
        </div>

        <div className="card" style={{ padding: 30, borderRadius: 24 }}>
          <h1 style={{ fontSize: 24, fontWeight: 800 }}>Create Account</h1>
          <p className="sub" style={{ fontSize: 14, margin: '6px 0 24px' }}>
            Your health, one step away
          </p>

          <form onSubmit={submit}>
            <div className="form-group">
              <label className="label">Full Name</label>
              <input className="input" placeholder="John Doe" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="label">Email</label>
              <input type="email" className="input" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="label">Password</label>
              <input type="password" className="input" placeholder="Min 6 characters" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="label">Confirm Password</label>
              <input type="password" className="input" placeholder="Repeat password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            </div>
            <UiButton type="submit" className="btn-primary" loading={busy}>
              {busy ? 'Creating…' : 'Create Account'}
            </UiButton>
          </form>

          <div style={{ textAlign: 'center', marginTop: 22, paddingTop: 20, borderTop: '1px solid var(--border)' }}>
            <p className="sub" style={{ fontSize: 14 }}>
              Already have an account?{' '}
              <Link to="/login" style={{ fontWeight: 700, color: 'var(--primary)' }}>
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}