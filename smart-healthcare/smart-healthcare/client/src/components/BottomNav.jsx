import { NavLink, useLocation } from 'react-router-dom';
import { IcHome, IcAssess, IcBell, IcUser, IcSpark } from './Icons';

const items = [
  { to: '/', icon: IcHome, label: 'Home' },
  { to: '/assessment', icon: IcAssess, label: 'Assess' },
  { to: '/assistant', icon: IcSpark, label: 'AI Care', center: true },
  { to: '/alerts', icon: IcBell, label: 'Alerts' },
  { to: '/profile', icon: IcUser, label: 'Profile' },
];

export default function BottomNav() {
  const { pathname } = useLocation();
  const hideOn = ['/login', '/signup'];
  if (hideOn.includes(pathname)) return null;

  return (
    <nav className="bottom-nav">
      {items.map(({ to, icon: Icon, label, center }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `nav-item${isActive ? ' active' : ''}${center ? ' nav-ai' : ''}`
          }
        >
          <Icon size={center ? 23 : 21} />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}