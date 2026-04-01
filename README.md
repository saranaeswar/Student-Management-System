# StudentByte — Student Management System

A full-stack Student Management System built with **Flask** + **MongoDB**, deployable to **Vercel**.

---

## 📁 Folder Structure

```
.
├── app.py                  ← Flask backend (API routes)
├── requirements.txt        ← Python dependencies
├── vercel.json             ← Vercel deployment config
├── templates/
│   └── index.html          ← Main HTML page
└── static/
    ├── css/
    │   └── style.css       ← Stylesheet
    └── js/
        └── main.js         ← Frontend JavaScript
```

---

## 🚀 Local Setup

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Start MongoDB locally
Make sure MongoDB is running on your machine:
```bash
mongod
```
Or use [MongoDB Compass](https://www.mongodb.com/products/compass) for a GUI.

### 3. Run Flask
```bash
python app.py
```

Open your browser at: **http://127.0.0.1:5000**

---

## ☁️ Deploy to Vercel

### 1. Push to GitHub
```bash
git add .
git commit -m "Your commit message"
git push origin main
```

### 2. Connect to Vercel
- Go to [Vercel](https://vercel.com) and sign in.
- Click "New Project" and import your GitHub repo.
- Vercel will auto-detect the Python app.

### 3. Set Environment Variables
In Vercel dashboard > Project Settings > Environment Variables:
- Add `MONGO_URI` with your MongoDB connection string (e.g., `mongodb+srv://...`)

### 4. Deploy
Click "Deploy" — your app will be live!

---

## 📋 Features

- ✅ Add new students
- ✅ View all students (filter by active/inactive)
- ✅ Update student details
- ✅ Delete students
- ✅ Responsive UI with Bootstrap

---

## 🔌 API Endpoints

| Method | Endpoint          | Description              |
|--------|-------------------|--------------------------|
| GET    | `/api/students`   | Get all students         |
| POST   | `/api/students`   | Add a new student        |
| PUT    | `/api/students/<id>` | Update a student         |
| DELETE | `/api/students/<id>` | Delete a student         |

**Query Params for GET:**
- `filter=active` → Show only active students
- `filter=all` → Show all students

---

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **Database:** MongoDB Atlas
- **Frontend:** HTML, CSS, JavaScript
- **Deployment:** Vercel
- **Styling:** Bootstrap

---

## 📝 Notes

- Uses environment variables for secure DB connection.
- Data is stored in MongoDB with fields: name, email, phone, course, status, created_at.
- For local dev, set `MONGO_URI` in your terminal: `$env:MONGO_URI = "your-connection-string"`

---

Enjoy your Student Management System! 🎓