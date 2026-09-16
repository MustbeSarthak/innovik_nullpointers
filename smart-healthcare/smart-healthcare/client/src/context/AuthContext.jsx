import { createContext, useContext, useEffect, useState } from 'react';
import { AuthAPI, getCurrentUser } from '../lib/api';

const AuthContext = createContext({ user: null, loading: true, setUser: () => {} });

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    AuthAPI.me()
      .then((u) => {
        if (active) {
          setUser(u);
          setLoading(false);
        }
      })
      .catch(() => {
        if (active) {
          setUser(null);
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, setUser }}>{children}</AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

export { getCurrentUser };