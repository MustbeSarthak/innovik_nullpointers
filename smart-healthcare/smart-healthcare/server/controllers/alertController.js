const pool = require('../models/db');

const getAlerts = async (req, res) => {
  try {
    const pr = await pool.query('SELECT id FROM patients WHERE user_id = $1', [req.user.id]);
    if (pr.rows.length === 0) {
      return res.json([]);
    }
    const result = await pool.query(
      'SELECT * FROM alerts WHERE patient_id = $1 ORDER BY created_at DESC',
      [pr.rows[0].id]
    );
    res.json(result.rows);
  } catch (err) {
    console.error('Get alerts error:', err.message);
    res.status(500).json({ error: 'Server error' });
  }
};

const createAlert = async (req, res) => {
  try {
    const { severity, message, risk_score, symptoms, action_taken } = req.body;
    const pr = await pool.query('SELECT id FROM patients WHERE user_id = $1', [req.user.id]);
    if (pr.rows.length === 0) {
      return res.status(404).json({ error: 'Patient profile not found' });
    }
    const pid = pr.rows[0].id;
    const result = await pool.query(
      `INSERT INTO alerts (patient_id, severity, message, risk_score, symptoms, action_taken)
       VALUES ($1,$2,$3,$4,$5,$6) RETURNING *`,
      [pid, severity, message, risk_score || 0,
       JSON.stringify(symptoms || {}), action_taken || 'None']
    );
    res.status(201).json(result.rows[0]);
  } catch (err) {
    console.error('Create alert error:', err.message);
    res.status(500).json({ error: 'Server error' });
  }
};

module.exports = { getAlerts, createAlert };
