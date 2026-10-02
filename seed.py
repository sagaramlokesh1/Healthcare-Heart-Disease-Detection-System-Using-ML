from app import db, predictions_db
from datetime import datetime
import random

# If you have a Patient model, ensure patient IDs exist; otherwise set to 1.
sample_data = []
for i in range(30):
    sample_data.append({
        'patient_id': random.randint(1, 10),  # adjust range
        'risk_level': random.choice(['High', 'Medium', 'Low']),
        'probability': round(random.uniform(10, 95), 1),
        'smoker': random.choice([True, False]),
        'diabetic': random.choice([True, False]),
        'family_history': random.choice([True, False]),
        'hypertension': random.choice([True, False]),
        'created_at': datetime.now()
    })

# If predictions_db is a Model class:
for data in sample_data:
    pred = predictions_db(**data)
    db.session.add(pred)
db.session.commit()

print(f"Inserted {len(sample_data)} predictions.")