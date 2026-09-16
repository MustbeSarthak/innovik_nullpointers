const pool = require('../models/db');

const getPatient = async (req, res) => {
  try {
    const userId = req.params.id || req.user.id;
    const result = await pool.query(
      `SELECT p.*, u.name, u.email FROM patients p
       JOIN users u ON p.user_id = u.id
       WHERE p.user_id = $1`,
      [userId]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Patient not found' });
    }
    const patient = result.rows[0];
    const caretaker = await pool.query(
      'SELECT * FROM caretakers WHERE patient_id = $1',
      [patient.id]
    );
    patient.caretaker = caretaker.rows[0] || null;
    const docs = await pool.query(
      'SELECT * FROM documents WHERE patient_id = $1 ORDER BY upload_time DESC',
      [patient.id]
    );
    patient.documents = docs.rows;

    const medsResult = await pool.query(
      'SELECT medications FROM assessments WHERE patient_id = $1 ORDER BY created_at DESC LIMIT 1',
      [patient.id]
    );
    patient.medications = medsResult.rows[0]?.medications || [];

    res.json(patient);
  } catch (err) {
    console.error('Get patient error:', err.message);
    res.status(500).json({ error: 'Server error' });
  }
};

const updatePatient = async (req, res) => {
  try {
    const { age, gender, blood_group, height, weight, phone, medical_history, lifestyle } = req.body;
    const pr = await pool.query('SELECT id FROM patients WHERE user_id = $1', [req.user.id]);
    if (pr.rows.length === 0) {
      return res.status(404).json({ error: 'Patient not found' });
    }
    const pid = pr.rows[0].id;
    const result = await pool.query(
      `UPDATE patients SET
        age = COALESCE($1, age),
        gender = COALESCE($2, gender),
        blood_group = COALESCE($3, blood_group),
        height = COALESCE($4, height),
        weight = COALESCE($5, weight),
        phone = COALESCE($6, phone),
        medical_history = COALESCE($7, medical_history),
        lifestyle = COALESCE($8, lifestyle)
      WHERE id = $9 RETURNING *`,
      [age, gender, blood_group, height, weight, phone,
       medical_history ? JSON.stringify(medical_history) : null,
       lifestyle ? JSON.stringify(lifestyle) : null, pid]
    );
    res.json(result.rows[0]);
  } catch (err) {
    console.error('Update patient error:', err.message);
    res.status(500).json({ error: 'Server error' });
  }
};

const updateCaretaker = async (req, res) => {
  try {
    const { name, phone, relationship, altPhone } = req.body;
    const pr = await pool.query('SELECT id FROM patients WHERE user_id = $1', [req.user.id]);
    if (pr.rows.length === 0) {
      return res.status(404).json({ error: 'Patient not found' });
    }
    const pid = pr.rows[0].id;
    const existing = await pool.query('SELECT id FROM caretakers WHERE patient_id = $1', [pid]);
    let result;
    if (existing.rows.length > 0) {
      result = await pool.query(
        'UPDATE caretakers SET name=$1, phone=$2, relationship=$3, alt_phone=$4 WHERE patient_id=$5 RETURNING *',
        [name, phone, relationship, altPhone || null, pid]
      );
    } else {
      result = await pool.query(
        'INSERT INTO caretakers (patient_id, name, phone, relationship, alt_phone) VALUES ($1,$2,$3,$4,$5) RETURNING *',
        [pid, name, phone, relationship, altPhone || null]
      );
    }
    res.json(result.rows[0]);
  } catch (err) {
    console.error('Update caretaker error:', err.message);
    res.status(500).json({ error: 'Server error' });
  }
};

module.exports = { getPatient, updatePatient, updateCaretaker };
