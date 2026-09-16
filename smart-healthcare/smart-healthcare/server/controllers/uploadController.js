const pool = require('../models/db');

const uploadReport = async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }
    const pr = await pool.query('SELECT id FROM patients WHERE user_id = $1', [req.user.id]);
    if (pr.rows.length === 0) {
      return res.status(404).json({ error: 'Patient profile not found' });
    }
    const pid = pr.rows[0].id;
    const fileUrl = `/uploads/${req.file.filename}`;
    const result = await pool.query(
      'INSERT INTO documents (patient_id, file_url, file_name, file_type) VALUES ($1,$2,$3,$4) RETURNING *',
      [pid, fileUrl, req.file.originalname, req.file.mimetype]
    );
    res.status(201).json(result.rows[0]);
  } catch (err) {
    console.error('Upload report error:', err.message);
    res.status(500).json({ error: 'Server error' });
  }
};

const getDocuments = async (req, res) => {
  try {
    const pr = await pool.query('SELECT id FROM patients WHERE user_id = $1', [req.user.id]);
    if (pr.rows.length === 0) {
      return res.json([]);
    }
    const result = await pool.query(
      'SELECT * FROM documents WHERE patient_id = $1 ORDER BY upload_time DESC',
      [pr.rows[0].id]
    );
    res.json(result.rows);
  } catch (err) {
    console.error('Get documents error:', err.message);
    res.status(500).json({ error: 'Server error' });
  }
};

module.exports = { uploadReport, getDocuments };
