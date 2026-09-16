const express = require('express');
const router = express.Router();
const { getAlerts, createAlert } = require('../controllers/alertController');
const authMiddleware = require('../middleware/auth');

router.get('/', authMiddleware, getAlerts);
router.post('/', authMiddleware, createAlert);

module.exports = router;
