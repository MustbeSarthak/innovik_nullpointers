import { createContext, useCallback, useContext, useState } from 'react';

const ToastContext = createContext({ showToast: () => {} });

let timer;

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);

  const showToast = useCallback((message, type = 'ok') => {
    setToast({ message, type, key: Date.now() });
    clearTimeout(timer);
    timer = setTimeout(() => setToast(null), 3200);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {toast && (
        <div key={toast.key} className={`toast ${toast.type}`}>
          {toast.message}
        </div>
      )}
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);