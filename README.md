# 🏥 Automated Pharmacy & Prescription Management System

An AI-powered web application developed during a hackathon to modernize pharmacy operations, improve prescription safety, and enhance patient understanding using intelligent automation.

---

## 🚀 Project Overview

The **Automated Pharmacy & Prescription Management System** is a full-stack web application that digitizes the workflow between **Doctors, Pharmacists, and Administrators**. It allows secure prescription creation, validation, billing, inventory management, and integrates **AI (ChatGPT / Google Gemini)** to analyze and explain prescriptions in a human-friendly manner.

The project focuses on **patient safety**, **efficiency**, and **clarity**, making it ideal for real-world healthcare environments.

---

## ✨ Key Features

### 👨‍⚕️ Doctor Module
- Add and manage patients
- Create digital prescriptions
- View patient prescription history

### 💊 Pharmacist Module
- Validate prescriptions using AI-based safety checks
- Detect:
  - Dosage limit violations
  - Drug–drug interactions
  - Allergy conflicts
- Generate bills and invoices
- Manage medicine inventory
- View low-stock alerts

### 🧑‍💼 Admin Module
- Manage users (Doctor / Pharmacist / Admin)
- View system statistics and reports
- Monitor sales and prescription data

### 🧠 AI-Powered Features
- AI-assisted prescription explanation
- Converts medical jargon into simple language
- Supports **OpenAI (ChatGPT)** and **Google Gemini**
- Prescription analysis via:
  - Database records
  - Uploaded prescription images (OCR + AI)
- Safe fallback mechanism if AI service is unavailable

⚠️ *AI outputs are for informational purposes only and not for medical diagnosis.*

---

## 🛠️ Tech Stack

| Layer        | Technology |
|-------------|------------|
| Frontend    | HTML, CSS |
| Backend     | Python (Flask) |
| Database    | MySQL |
| AI Models   | OpenAI (ChatGPT) |
| Authentication | Role-based (Admin, Doctor, Pharmacist) |

---

## 📁 Project Structure

automated-pharmacy-system/
│
├── app.py
├── .env
├── .gitignore
├── requirements.txt
├── README.md
│
├── templates/
│ ├── login.html
│ ├── doctor_dashboard.html
│ ├── pharmacist_dashboard.html
│ ├── admin_dashboard.html
│ ├── ai_analysis.html
│ ├── invoice.html
│ └── reports.html
│
├── static/
│ ├── css/
│ ├── uploads/
│
└── database/
└── pharmacy_db.sql

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/automated-pharmacy-system.git
cd automated-pharmacy-system

2️⃣ Create Virtual Environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Configure Environment Variables
SECRET_KEY=hackathon_secret_key
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=pharmacy_db
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key

5️⃣ Setup Database
Import pharmacy_db.sql into MySQL using phpMyAdmin or MySQL CLI

6️⃣ Run the Application
python app.py

Open in browser:
http://127.0.0.1:5000

| Role       | Username | Password |
| ---------- | -------- | -------- |
| Admin      | admin    | pass123  |
| Doctor     | doc1     | pass123  |
| Pharmacist | pharm1   | pass123  |

🧠 AI Architecture (High-Level)

Prescription Data / Image
        ↓
Text Extraction (OCR / DB)
        ↓
AI Engine (OpenAI / Gemini)
        ↓
Human-Readable Explanation


