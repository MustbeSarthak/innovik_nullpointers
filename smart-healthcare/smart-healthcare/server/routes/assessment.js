const express = require('express');
const router = express.Router();
const { createAssessment, getAssessmentHistory } = require('../controllers/assessmentController');
const authMiddleware = require('../middleware/auth');

router.post('/', authMiddleware, createAssessment);
router.get('/history', authMiddleware, getAssessmentHistory);

module.exports = router;
