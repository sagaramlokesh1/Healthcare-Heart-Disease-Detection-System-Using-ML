# ❤️ Healthcare Heart Disease Detection System Using Machine Learning

## 📌 Project Overview

The Healthcare Heart Disease Detection System is a full-stack machine
learning web application designed to predict heart disease risk from
patient health information.

The system integrates a Machine Learning prediction layer with a Django
backend and an interactive frontend. In addition to disease prediction,
the application is structured to support patient history, analytics,
reports, recommendations, appointments, notifications, record searching,
and healthcare data management.

---

## 🚀 Key Features

- Heart disease risk prediction
- Machine Learning model integration
- Patient registration and authentication
- Patient profile management
- Patient history tracking
- Prediction history management
- Healthcare analytics dashboard
- Patient record search
- Patient comparison
- Health recommendations
- Appointment management
- Notification management
- Feedback management
- PDF report generation
- CSV and Excel data export
- Data visualization and analytics
- ECG analysis module
- Responsive web interface

---

## 🛠️ Technology Stack

### Machine Learning
- Python
- Pandas
- NumPy
- Scikit-learn
- Matplotlib
- Jupyter Notebook
- Pickle

### Backend
- Python
- Django
- SQLite
- Django ORM

### Frontend
- HTML
- CSS
- JavaScript
- Bootstrap
- Chart.js
- Font Awesome
- DataTables

### Deployment
- Docker
- Docker Compose
- Gunicorn
- Nginx

---

## 🧠 Machine Learning Workflow

1. Data Collection
2. Data Cleaning
3. Exploratory Data Analysis
4. Data Preprocessing
5. Feature Engineering
6. Model Training
7. Model Evaluation
8. Model Serialization
9. Django Integration
10. Patient Risk Prediction

---

## 📊 Machine Learning Layer

The `ml_model/` module contains the machine learning pipeline.

Key components include:

- `train_model.py` – Model training
- `predict.py` – Prediction logic
- `preprocessing.py` – Data preprocessing
- `feature_engineering.py` – Feature preparation
- `evaluation.py` – Model evaluation
- `recommendation_system.py` – Recommendation logic
- `history_manager.py` – Prediction history
- `analytics_engine.py` – Analytics processing
- `ecg_analysis.py` – ECG analysis

Trained artifacts are stored inside:

    ml_model/saved_models/

including:

    heart_model.pkl
    scaler.pkl
    feature_columns.pkl
    encoder.pkl

---

## 📈 Analytics & Visualization

The system includes analytical functionality for understanding patient
and prediction data.

Visualizations include:

- Heart disease risk distribution
- Correlation analysis
- Prediction trends
- Patient statistics
- Feature relationships
- Analytics dashboards

Generated visualizations and reports are maintained in the
`visualizations/`, `reports/`, and frontend chart directories.

---

## 🖥️ Django Backend

The backend is developed using Django.

The `predictor` application manages:

- Heart disease predictions
- Patient records
- Prediction history
- Analytics
- Reports
- Recommendations
- Appointments
- Notifications
- Record searching
- Patient comparisons
- CSV/Excel exports
- Feedback

The `accounts` application handles:

- User authentication
- Registration
- Profile management
- Password recovery
- Account settings

---

## 📄 Reporting

The application is structured to generate and manage:

- Patient summary reports
- Prediction reports
- Analytics reports
- PDF reports
- CSV exports
- Excel exports
- Charts and visual reports

---

## 📂 Project Structure

HeartDiseaseProject/
│
├── ml_model/
│   ├── dataset/
│   ├── notebooks/
│   ├── saved_models/
│   ├── reports/
│   └── visualizations/
│
├── backend/
│   ├── core/
│   ├── predictor/
│   └── accounts/
│
├── frontend/
│   ├── templates/
│   ├── static/
│   └── media/
│
├── logs/
├── tests/
├── deployment/
├── requirements.txt
├── manage.py
├── db.sqlite3
└── README.md

---

## 🔐 Environment Configuration

Sensitive configuration should be stored in a `.env` file.

Example:

    SECRET_KEY=your_secret_key
    DEBUG=True

Do not upload the real `.env` file to GitHub.

Add it to `.gitignore`:

    .env
    venv/
    __pycache__/
    *.pyc
    db.sqlite3

---

## ⚙️ Installation

### 1. Clone the Repository

    git clone <your-repository-url>
    cd HeartDiseaseProject

### 2. Create Virtual Environment

    python -m venv venv

### 3. Activate Virtual Environment

Windows:

    venv\Scripts\activate

Linux/macOS:

    source venv/bin/activate

### 4. Install Dependencies

    pip install -r requirements.txt

### 5. Apply Database Migrations

    python manage.py makemigrations
    python manage.py migrate

### 6. Run the Application

    python manage.py runserver

Open:

    http://127.0.0.1:8000/

---

## 📌 Future Improvements

- Improve model performance with additional datasets
- Add model explainability
- Add REST API support
- Improve recommendation personalization
- Add cloud deployment
- Add advanced healthcare analytics
- Add automated model monitoring

---

## ⚠️ Disclaimer

This project is developed for educational and analytical purposes.
Predictions produced by the machine learning model should not be used
as a substitute for professional medical diagnosis or treatment.

---

## 👤 Author

**Sagaram Lokesh**

Data Analytics | Python | SQL | Power BI | Tableau | Machine Learning

LinkedIn: linkedin.com/in/sagaramlokesh  
GitHub: github.com/SagaramLokesh
