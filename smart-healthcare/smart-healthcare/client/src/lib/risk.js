const WEIGHTS = {
  chestPain: 40,
  breathingDifficulty: 40,
  seizure: 50,
  severeBleeding: 50,
  fainting: 35,
  confusion: 30,
  fever: 10,
  dizziness: 10,
};

export function calculateRisk(symptoms = {}) {
  let score = 0;
  Object.keys(WEIGHTS).forEach((k) => {
    if (symptoms[k]) score += WEIGHTS[k];
  });
  if (score >= 81) return { score, level: 'Critical' };
  if (score >= 51) return { score, level: 'High' };
  if (score >= 21) return { score, level: 'Moderate' };
  return { score, level: 'Low' };
}

export const SYMPTOM_OPTIONS = [
  { value: 'chestPain', label: 'Chest Pain', critical: true },
  { value: 'breathingDifficulty', label: 'Breathing Difficulty', critical: true },
  { value: 'severeBleeding', label: 'Severe Bleeding', critical: true },
  { value: 'seizure', label: 'Seizure', critical: true },
  { value: 'fever', label: 'Fever' },
  { value: 'vomiting', label: 'Vomiting' },
  { value: 'dizziness', label: 'Dizziness' },
  { value: 'fainting', label: 'Fainting' },
  { value: 'confusion', label: 'Confusion' },
  { value: 'headache', label: 'Headache' },
  { value: 'rash', label: 'Skin Rash' },
  { value: 'soreThroat', label: 'Sore Throat' },
];

export const HISTORY_OPTIONS = [
  { value: 'diabetes', label: 'Diabetes' },
  { value: 'hypertension', label: 'Hypertension' },
  { value: 'heartDisease', label: 'Heart Disease' },
  { value: 'asthma', label: 'Asthma' },
  { value: 'kidneyDisease', label: 'Kidney Disease' },
  { value: 'stroke', label: 'Stroke' },
  { value: 'allergy', label: 'Allergy' },
  { value: 'surgery', label: 'Surgery History' },
];