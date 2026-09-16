const pool = require('../models/db');

function calculateRisk(symptoms) {
  let score = 0;
  if (symptoms.chestPain) score += 40;
  if (symptoms.breathingDifficulty) score += 40;
  if (symptoms.seizure) score += 50;
  if (symptoms.severeBleeding) score += 50;
  if (symptoms.confusion) score += 30;
  if (symptoms.fainting) score += 35;
  if (symptoms.fever) score += 10;
  if (symptoms.dizziness) score += 10;

  let level = 'Low';
  if (score >= 81) level = 'Critical';
  else if (score >= 51) level = 'High';
  else if (score >= 21) level = 'Moderate';

  return { score, level };
}

const createAssessment = async (req, res) => {
  try {
    const { symptoms, pain_level, medications, notes } = req.body;
    const pr = await pool.query('SELECT id FROM patients WHERE user_id = $1', [req.user.id]);
    if (pr.rows.length === 0) {
      return res.status(404).json({ error: 'Patient profile not found. Complete your profile first.' });
    }
    const pid = pr.rows[0].id;
    const { score, level } = calculateRisk(symptoms || {});

    const result = await pool.query(
      `INSERT INTO assessments (patient_id, risk_score, risk_level, symptoms, pain_level, medications, notes)
       VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING *`,
      [pid, score, level, JSON.stringify(symptoms || {}), pain_level || 0,
       JSON.stringify(medications || []), notes || '']
    );

    if (level === 'Critical') {
      const pi = await pool.query(
        'SELECT u.name FROM patients p JOIN users u ON p.user_id = u.id WHERE p.id = $1',
        [pid]
      );
      const pname = pi.rows[0]?.name || 'Unknown';
      await pool.query(
        `INSERT INTO alerts (patient_id, severity, message, risk_score, symptoms, action_taken)
         VALUES ($1,$2,$3,$4,$5,$6)`,
        [pid, 'Critical', `${pname} may require immediate attention.`,
         score, JSON.stringify(symptoms || {}), 'Emergency alert triggered']
      );
    }

    res.status(201).json({
      assessment: result.rows[0],
      risk: { score, level },
      isCritical: level === 'Critical'
    });
  } catch (err) {
    console.error('Create assessment error:', err.message);
    res.status(500).json({ error: 'Server error' });
  }
};

const getAssessmentHistory = async (req, res) => {
  try {
    const pr = await pool.query('SELECT id FROM patients WHERE user_id = $1', [req.user.id]);
    if (pr.rows.length === 0) {
      return res.json([]);
    }
    const result = await pool.query(
      'SELECT * FROM assessments WHERE patient_id = $1 ORDER BY created_at DESC',
      [pr.rows[0].id]
    );
    res.json(result.rows);
  } catch (err) {
    console.error('Get assessment history error:', err.message);
    res.status(500).json({ error: 'Server error' });
  }
};

module.exports = { createAssessment, getAssessmentHistory, calculateRisk };
