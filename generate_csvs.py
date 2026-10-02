# generate_csvs.py
import os
import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta

# Create directory if not exists
os.makedirs('ml_model/dataset', exist_ok=True)

# ------------------------------
# 1. Generate heart.csv (simulated UCI-style dataset)
# ------------------------------
print("Generating heart.csv ...")
np.random.seed(42)
n = 303  # standard size of Cleveland dataset

heart_data = {
    'age': np.random.randint(29, 77, n),
    'sex': np.random.choice([0, 1], n, p=[0.32, 0.68]),   # 1 = male
    'cp': np.random.choice([0, 1, 2, 3], n),              # chest pain type
    'trestbps': np.random.randint(94, 200, n),            # resting blood pressure
    'chol': np.random.randint(126, 564, n),               # cholesterol
    'fbs': np.random.choice([0, 1], n, p=[0.85, 0.15]),   # fasting blood sugar >120
    'restecg': np.random.choice([0, 1, 2], n),            # resting ECG
    'thalach': np.random.randint(71, 202, n),             # max heart rate
    'exang': np.random.choice([0, 1], n),                 # exercise induced angina
    'oldpeak': np.random.uniform(0, 6.2, n).round(1),     # ST depression
    'slope': np.random.choice([0, 1, 2], n),
    'ca': np.random.choice([0, 1, 2, 3], n, p=[0.6, 0.2, 0.15, 0.05]),
    'thal': np.random.choice([0, 1, 2, 3], n, p=[0.05, 0.5, 0.3, 0.15]),
    'target': np.random.choice([0, 1], n, p=[0.45, 0.55])  # 1 = disease
}
df_heart = pd.DataFrame(heart_data)
df_heart.to_csv('ml_model/dataset/heart.csv', index=False)
print("✓ heart.csv saved")

# ------------------------------
# 2. Generate patient_records.csv (synthetic patients)
# ------------------------------
print("Generating patient_records.csv ...")
fake = Faker()
Faker.seed(42)
np.random.seed(42)

n_patients = 200
patient_records = []

for i in range(1, n_patients + 1):
    dob = fake.date_of_birth(minimum_age=30, maximum_age=85)
    gender = np.random.choice(['M', 'F'])
    first_name = fake.first_name_male() if gender == 'M' else fake.first_name_female()
    last_name = fake.last_name()
    
    patient_records.append({
        'patient_id': i,
        'first_name': first_name,
        'last_name': last_name,
        'date_of_birth': dob.strftime('%Y-%m-%d'),
        'gender': gender,
        'phone': fake.phone_number(),
        'email': fake.email(),
        'address': fake.address().replace('\n', ', '),
        'medical_history': np.random.choice(
            ['None', 'Hypertension', 'Diabetes', 'Hypertension, Diabetes', 'High Cholesterol'],
            p=[0.3, 0.3, 0.2, 0.1, 0.1]
        ),
        'created_at': fake.date_time_between(start_date='-2y', end_date='now').strftime('%Y-%m-%d %H:%M:%S')
    })

df_patients = pd.DataFrame(patient_records)
df_patients.to_csv('ml_model/dataset/patient_records.csv', index=False)
print("✓ patient_records.csv saved")

# ------------------------------
# 3. Generate prediction_history.csv (synthetic predictions)
# ------------------------------
print("Generating prediction_history.csv ...")
np.random.seed(42)

# Load patient IDs from the file we just created
patient_ids = df_patients['patient_id'].tolist()

n_predictions = 500
pred_data = []

for i in range(1, n_predictions + 1):
    patient_id = np.random.choice(patient_ids)
    pred_date = datetime.now() - timedelta(days=np.random.randint(0, 365))
    risk = np.random.uniform(0, 1)
    risk_class = 1 if risk > 0.5 else 0
    
    pred_data.append({
        'prediction_id': i,
        'patient_id': patient_id,
        'prediction_date': pred_date.strftime('%Y-%m-%d %H:%M:%S'),
        'ml_risk_score': round(risk, 3),
        'ml_risk_class': risk_class,
        'framingham_score': round(np.random.uniform(0, 100), 1),
        'ascvd_score': round(np.random.uniform(0, 100), 1),
        'qrisk3_score': round(np.random.uniform(0, 100), 1),
        'systolic_bp': np.random.randint(90, 180),
        'cholesterol': np.random.randint(150, 350),
        'smoker': np.random.choice([True, False], p=[0.2, 0.8]),
        'diabetic': np.random.choice([True, False], p=[0.25, 0.75]),
        'recommendation': np.random.choice(
            ['Consult cardiologist immediately', 'Lifestyle changes and follow-up', 'Maintain healthy habits'],
            p=[0.3, 0.4, 0.3]
        )
    })

df_preds = pd.DataFrame(pred_data)
df_preds.to_csv('ml_model/dataset/prediction_history.csv', index=False)
print("✓ prediction_history.csv saved")

print("\n✅ All three CSV files have been generated in 'ml_model/dataset/'")