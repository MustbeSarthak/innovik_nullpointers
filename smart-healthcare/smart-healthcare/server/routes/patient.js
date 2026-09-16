const express = require('express');
const router = express.Router();
const { getPatient, updatePatient, updateCaretaker } = require('../controllers/patientController');
const authMiddleware = require('../middleware/auth');

router.get('/', authMiddleware, getPatient);
router.get('/:id', authMiddleware, getPatient);
router.put('/', authMiddleware, updatePatient);
router.put('/caretaker', authMiddleware, updateCaretaker);

module.exports = router;
