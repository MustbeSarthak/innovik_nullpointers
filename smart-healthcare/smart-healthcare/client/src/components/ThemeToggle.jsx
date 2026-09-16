import { useTheme } from '../context/ThemeContext';
import { IcSun, IcMoon } from './Icons';

export default function ThemeToggle({ className = '' }) {
  const { theme, toggle } = useTheme();

  return (
    <button
      className={`theme-switch ${theme} ${className}`}
      onClick={toggle}
      aria-label="Toggle night mode"
    >
      <span className="knob">{theme === 'light' ? <IcMoon /> : <IcSun />}</span>
    </button>
  );
}