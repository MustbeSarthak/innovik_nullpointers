import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthAPI } from '../lib/api';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import UiButton from '../components/UiButton';
import { IcHeart } from '../components/Icons';
import ThemeToggle from '../components/ThemeToggle';

export default function Login() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { setUser } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!email || !password) return showToast('Please fill in all fields', 'err');
    setBusy(true);
    try {
      const data = await AuthAPI.login({ email, password });
      setUser(data.user);
      showToast('Login successful');
      setTimeout(() => navigate('/dashboard'), 450);
    } catch (err) {
      showToast(err.message || 'Login failed', 'err');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center' }}>
      <div style={{ width: '100%', maxWidth: 420, margin: '0 auto' }}>
        <div className="split" style={{ marginBottom: 18 }}>
          <div className="logo-box">
            <IcHeart size={28} />
          </div>
          <ThemeToggle />
        </div>

        <div className="card" style={{ padding: 30, borderRadius: 24 }}>
          <h1 style={{ fontSize: 24, fontWeight: 800 }}>Welcome Back</h1>
          <p className="sub" style={{ fontSize: 14, margin: '6px 0 24px' }}>
            Sign in to access your health dashboard
          </p>

          <form onSubmit={submit}>
            <div className="form-group">
              <label className="label">Email</label>
              <input
                type="email"
                className="input"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="label">Password</label>
              <input
                type="password"
                className="input"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <UiButton type="submit" className="btn-primary" loading={busy}>
              {busy ? 'Signing in…' : 'Sign In'}
            </UiButton>
          </form>

          <div style={{ textAlign: 'center', marginTop: 22, paddingTop: 20, borderTop: '1px solid var(--border)' }}>
            <p className="sub" style={{ fontSize: 14 }}>
              Don't have an account?{' '}
              <Link to="/signup" style={{ fontWeight: 700, color: 'var(--primary)' }}>
                Sign Up
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}