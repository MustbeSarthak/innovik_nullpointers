import axios from 'axios';

let _currentUser = null;

const TOKEN_KEY = 'smart_healthcare_token';
const USER_KEY = 'smart_healthcare_user';
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL.replace(/\/$/, ''),
  withCredentials: true,
});

const getStoredToken = () => localStorage.getItem(TOKEN_KEY);

const persistToken = (token) => {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
};

const normalizePatient = (patient) => {
  if (!patient) return null;

  const normalized = {
    ...patient,
    id: patient.patient_id ?? patient.id ?? patient.user_id ?? null,
    patient_id: patient.patient_id ?? patient.id ?? patient.user_id ?? null,
    name: patient.full_name ?? patient.name ?? 'Patient',
    full_name: patient.full_name ?? patient.name ?? 'Patient',
    email: patient.email ?? '',
    phone: patient.phone_number ?? patient.phone ?? null,
    phone_number: patient.phone_number ?? patient.phone ?? null,
  };

  return normalized;
};

const persistUser = (user) => {
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(USER_KEY);
  }
};

const readStoredUser = () => {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const extractErrorMessage = (error) => {
  const payload = error?.response?.data;
  if (typeof payload === 'string') return payload;
  if (payload?.detail) {
    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item) => item.msg || item.message || 'Invalid value').join(', ');
    }
    return payload.detail;
  }
  if (payload?.message) return payload.message;
  if (payload?.error) return payload.error;
  return error?.message || 'Request failed';
};

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers = {
      ...(config.headers || {}),
      Authorization: `Bearer ${token}`,
    };
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      _currentUser = null;
      persistUser(null);
      persistToken(null);
    }
    return Promise.reject(new Error(extractErrorMessage(error)));
  }
);

const toAssessmentList = (payload) => {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload.items)) return payload.items;
  if (payload && payload.data && Array.isArray(payload.data.items)) return payload.data.items;
  if (payload && payload.data && Array.isArray(payload.data)) return payload.data;
  if (payload && payload.assessments && Array.isArray(payload.assessments)) return payload.assessments;
  if (payload) return [payload];
  return [];
};

const toDocumentList = (payload) => {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload.items)) return payload.items;
  return payload?.documents ?? payload?.data?.items ?? payload?.data ?? [];
};

const normalizeAssessmentBody = (payload = {}) => {
  const medicalHistory = payload.medical_history ?? payload.history ?? {};
  const conditions = Object.entries(medicalHistory)
    .filter(([, enabled]) => Boolean(enabled))
    .map(([condition]) => ({ condition: String(condition), details: null }));

  const symptomsMap = payload.current_symptoms ?? payload.symptoms ?? {};
  const symptoms = Object.entries(symptomsMap)
    .filter(([, enabled]) => Boolean(enabled))
    .map(([symptom]) => ({
      symptom: String(symptom),
      duration: 'not specified',
      severity: 'mild',
      notes: null,
    }));

  const meds = Array.isArray(payload.medications)
    ? payload.medications
    : Array.isArray(payload.meds)
      ? payload.meds
      : [];

  return {
    basic_information: {
      age: Number(payload.age ?? 30),
      gender: (payload.gender ?? 'prefer_not_to_say').toLowerCase().replace(/\s+/g, '_'),
      height_cm: Number(payload.height ?? 170),
      weight_kg: Number(payload.weight ?? 70),
    },
    medical_history: {
      conditions: conditions.length ? conditions : [{ condition: 'none', details: null }],
    },
    current_symptoms: { symptoms },
    medications: {
      medications: meds.map((item) => ({
        name: item.name || 'Medication',
        dosage: item.dosage || 'as directed',
        frequency: item.frequency || 'daily',
      })),
    },
    allergies: { allergies: [] },
    additional_information: payload.notes || null,
  };
};

const toUploadFormData = (formData) => {
  const fd = new FormData();
  const fileSource = formData instanceof FormData ? formData : null;
  const file = fileSource?.get('file') || fileSource?.get('report') || fileSource?.get('document');

  if (file instanceof File) {
    fd.append('file', file);
  } else if (file && typeof file === 'object' && 'name' in file) {
    fd.append('file', file);
  }

  if (!fd.has('file')) {
    return fd;
  }

  const name = file?.name || 'uploaded-document';
  fd.append('title', name.replace(/\.[^/.]+$/, '') || 'Uploaded document');
  fd.append('document_type', 'other');
  fd.append('description', 'Uploaded from Smart Healthcare');
  return fd;
};

/* ══════════════════════════════════════════════════════════
   Auth
   ══════════════════════════════════════════════════════════ */

export const AuthAPI = {
  async register({ name, email, password }) {
    const { data } = await api.post('/auth/register', {
      full_name: name,
      email,
      password,
    });

    const token = data.access_token;
    const user = normalizePatient(data.patient);
    _currentUser = user;
    persistToken(token);
    persistUser(user);

    return { user, token, ...data };
  },

  async login({ email, password }) {
    const { data } = await api.post('/auth/login', { email, password });
    const token = data.access_token;
    const user = normalizePatient(data.patient);
    _currentUser = user;
    persistToken(token);
    persistUser(user);

    return { user, token, ...data };
  },

  async logout() {
    _currentUser = null;
    persistToken(null);
    persistUser(null);
    return null;
  },

  async me() {
    try {
      const token = getStoredToken();
      if (!token) {
        _currentUser = null;
        persistUser(null);
        return null;
      }

      const { data } = await api.get('/auth/me');
      const user = normalizePatient(data);
      _currentUser = user;
      persistUser(user);
      return user;
    } catch {
      _currentUser = null;
      persistUser(null);
      persistToken(null);
      return null;
    }
  },
};

/* ══════════════════════════════════════════════════════════
   Patient
   ══════════════════════════════════════════════════════════ */

export const PatientAPI = {
  async get() {
    const existing = readStoredUser();
    if (existing) {
      _currentUser = normalizePatient(existing);
      return _currentUser;
    }

    const user = await AuthAPI.me();
    return user ?? null;
  },

  async update(data) {
    const current = _currentUser || readStoredUser() || {};
    const next = normalizePatient({ ...current, ...data });
    _currentUser = next;
    persistUser(next);
    return next;
  },

  async updateCaretaker(data) {
    const current = _currentUser || readStoredUser() || {};
    const next = normalizePatient({ ...current, caretaker: data });
    _currentUser = next;
    persistUser(next);
    return next;
  },
};

/* ══════════════════════════════════════════════════════════
   Assessment
   ══════════════════════════════════════════════════════════ */

export const AssessmentAPI = {
  async create(data) {
    const body = normalizeAssessmentBody(data);
    const { data: response } = await api.post('/assessments', body);
    return response;
  },

  async history() {
    const { data } = await api.get('/assessments/me');
    return toAssessmentList(data);
  },
};

/* ══════════════════════════════════════════════════════════
   Upload / Documents
   ══════════════════════════════════════════════════════════ */

export const UploadAPI = {
  async upload(formData) {
    const fd = toUploadFormData(formData);
    const { data } = await api.post('/documents', fd, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  async list() {
    const { data } = await api.get('/documents');
    return toDocumentList(data);
  },
};

/* ══════════════════════════════════════════════════════════
   AI Care
   ══════════════════════════════════════════════════════════ */

export const AiCareAPI = {
  async chat(message) {
    const { data } = await api.post('/ai-care/chat', { message });
    return data;
  },
};

/* ══════════════════════════════════════════════════════════
   Alerts
   ══════════════════════════════════════════════════════════ */

export const AlertAPI = {
  async list() {
    return [];
  },

  async create(data) {
    return data;
  },
};

export const NotificationAPI = {
  async list() {
    return [];
  },
};

export function getCurrentUser() {
  return _currentUser || normalizePatient(readStoredUser());
}

export function isSignedIn() {
  return !!getCurrentUser();
}

export function clearSession() {
  _currentUser = null;
  persistToken(null);
  persistUser(null);
}

export function seedDemoData() {
  return null;
}