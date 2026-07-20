# AI-Match-Analyst
# ⚽ AI Match Analyst

AI Match Analyst is a full-stack football analytics web application that generates intelligent post-match reports using real football squad data and user-entered match statistics.

The application allows users to select teams, load real player squads via the football-data.org API, record individual player performances, and generate detailed AI-style match analysis. Reports include player ratings, tactical verdicts, possession analysis, attacking insights, match intelligence, confidence scores, and an overall match rating.

All generated reports are stored in a SQLite database, allowing users to keep a history of previous matches.

---

## 🚀 Features

- Generate AI-style football match reports
- Load real team squads using the football-data.org API
- Display official club logos using TheSportsDB API
- Select players from both teams
- Enter player statistics
- Automatically calculate player ratings
- Choose the Man of the Match
- Generate tactical analysis and match intelligence
- Calculate overall match ratings and confidence scores
- Store match history in a SQLite database
- Clean and responsive user interface

---

## 🛠️ Tech Stack

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- FastAPI

### Database
- SQLite

### APIs
- football-data.org
- TheSportsDB

---

## 📷 Screenshots

*(Add screenshots of your application here.)*

Examples:
- Home page
- Squad selection
- Match report
- Match history

---

## ⚙️ Installation

### Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-match-analyst.git
```

### Navigate into the project

```bash
cd ai-match-analyst
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Create a `.env` file inside the `backend` folder

```env
FOOTBALL_DATA_API_KEY=YOUR_API_KEY
```

### Start the backend

```bash
cd backend
python -m uvicorn main:app --reload
```

### Open the frontend

Open `frontend/index.html` in your browser (or use Live Server in VS Code).

---

## 📁 Project Structure

```
ai-match-analyst/
│
├── backend/
│   ├── main.py
│   ├── match_history.db
│   └── .env
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── README.md
├── LICENSE
└── .gitignore
```

---

## 🎯 Future Improvements

- Position-specific player rating algorithms
- Interactive charts and visualisations
- PDF export for match reports
- Advanced performance analytics
- User authentication
- Cloud deployment
- More detailed AI-generated tactical analysis

---

## 📚 What I Learned

This project helped me gain practical experience with:

- Building REST APIs using FastAPI
- Working with external APIs
- Managing environment variables securely
- Database integration with SQLite
- Asynchronous JavaScript (Fetch API)
- Dynamic DOM manipulation
- Full-stack application development
- Organising larger software projects

---

## 📄 License

This project is licensed under the MIT License.
