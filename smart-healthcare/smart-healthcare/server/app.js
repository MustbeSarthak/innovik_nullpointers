const express = require('express');
const cors = require('cors');
const cookieParser = require('cookie-parser');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors({ origin: true, credentials: true }));
app.use(express.json());
app.use(cookieParser());
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));
app.use(express.static(path.join(__dirname, '..', 'client', 'dist')));

app.use('/auth', require('./routes/auth'));
app.use('/patient', require('./routes/patient'));
app.use('/assessment', require('./routes/assessment'));
app.use('/upload', require('./routes/upload'));
app.use('/alert', require('./routes/alerts'));

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'client', 'dist', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Smart Healthcare server running on http://localhost:${PORT}`);
});
