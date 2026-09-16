import { useRef } from 'react';

export default function UiButton({ className = '', children, loading, onClick, disabled, ...rest }) {
  const ref = useRef(null);

  const handleClick = (e) => {
    if (loading || disabled) return;
    const btn = ref.current;
    if (btn) {
      const rect = btn.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const ripple = document.createElement('span');
      ripple.className = 'ripple';
      const size = Math.max(rect.width, rect.height) * 2;
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = x - size / 2 + 'px';
      ripple.style.top = y - size / 2 + 'px';
      btn.appendChild(ripple);
      setTimeout(() => ripple.remove(), 560);
    }
    if (onClick) onClick(e);
  };

  return (
    <button
      ref={ref}
      className={`btn ${className}`}
      onClick={handleClick}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? <span className="spinner" /> : null}
      {children}
    </button>
  );
}