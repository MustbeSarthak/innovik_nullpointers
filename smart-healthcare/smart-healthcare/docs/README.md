# Smart Healthcare System

## Tech Stack
- **Frontend:** HTML, CSS, Vanilla JavaScript
- **Backend:** Node.js + Express
- **Database:** PostgreSQL
- **Authentication:** JWT + HttpOnly Cookies
- **File Upload:** Multer
- **Notifications:** Browser Push / FCM (configurable)
- **Theme:** Emerald health theme (teal + green)

## Quick Start

### 1. Database Setup
```bash
# Create the PostgreSQL database
createdb smart_healthcare

# Initialize tables
cd server
npm run db:init
```

### 2. Backend Server
```bash
cd server
npm install
npm run dev   # runs on http://localhost:5000
```

### 3. Frontend (Live Server or Netlify)
The frontend is a pure static site in `client/`.

**Live Server (testing):**
```bash
cd client
npx live-server
# OR open client/index.html in your browser
# Pages: http://localhost:8080/pages/landing.html
```

**Netlify (deploy):**
- Publish directory: `client/`
- No build command needed for static frontend
- If deploying backend API, configure separately or use Netlify Functions

## API Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| POST | /auth/register | Create account |
| POST | /auth/login | Sign in |
| POST | /auth/logout | Sign out |
| GET  | /auth/me | Current user |
| GET  | /patient | Patient profile |
| PUT  | /patient | Update profile |
| PUT  | /patient/caretaker | Save caretaker |
| POST | /assessment | Submit assessment |
| GET  | /assessment/history | Assessment history |
| POST | /upload | Upload report |
| GET  | /upload | List documents |
| GET  | /alert | List alerts |
| POST | /alert | Create alert |

## Risk Detection
Scores: Chest Pain 40, Breathing 40, Seizure 50, Bleeding 50, Confusion 30, Fainting 35, Fever 10, Dizziness 10

- 0-20 Low &bull; 21-50 Moderate &bull; 51-80 High &bull; 81+ Critical

## Page Navigation Map
```
index.html → pages/landing.html → all pages
login.html ↔ signup.html
landing.html → assessment.html / upload.html / history.html / dashboard.html
assessment.html → dashboard.html (on complete)
dashboard.html → assessment.html / upload.html / alert / profile
alerts.html → dashboard.html / history.html
patient-profile.html → caretaker.html / upload.html
```