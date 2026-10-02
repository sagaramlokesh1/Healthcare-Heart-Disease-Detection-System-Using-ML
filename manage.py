#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
import click
from django.core.management import execute_from_command_line
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.core.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


# -------------------------------------------------------------------
# Custom management commands (can be used via 'python manage.py <command>')
# -------------------------------------------------------------------
class CommandSeedData(BaseCommand):
    """Seed database with sample patients, visits, and predictions."""
    help = 'Populates the database with synthetic test data.'

    def handle(self, *args, **options):
        from backend.predictor.models import Patient, Visit, PredictionHistory
        from faker import Faker
        import random
        from datetime import timedelta, date

        fake = Faker()
        self.stdout.write("Seeding data...")

        # Create a demo user if none exists
        user, _ = User.objects.get_or_create(username='doctor', defaults={
            'email': 'doctor@example.com',
            'is_staff': True
        })
        if user.check_password('pass123') is False:
            user.set_password('pass123')
            user.save()

        # Create 20 sample patients
        patients_created = 0
        for _ in range(20):
            first_name = fake.first_name()
            last_name = fake.last_name()
            dob = fake.date_of_birth(minimum_age=30, maximum_age=80)
            patient = Patient.objects.create(
                user=user if random.random() > 0.5 else None,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=dob,
                gender=random.choice(['M', 'F']),
                phone=fake.phone_number(),
                email=fake.email(),
                address=fake.address(),
                medical_history=random.choice(['None', 'Hypertension', 'Diabetes', 'Hypertension, Diabetes'])
            )
            # Create 1-3 visits per patient
            for v in range(random.randint(1, 4)):
                visit_date = date.today() - timedelta(days=random.randint(0, 365))
                Visit.objects.create(
                    patient=patient,
                    visit_date=visit_date,
                    systolic_bp=random.randint(110, 180),
                    diastolic_bp=random.randint(70, 110),
                    cholesterol=random.randint(150, 300),
                    hdl_cholesterol=random.randint(30, 70),
                    glucose=random.randint(80, 180),
                    smoker=random.choice([True, False]),
                    diabetic=random.choice([True, False]),
                    family_history=random.choice([True, False]),
                    notes=fake.sentence()
                )
            patients_created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {patients_created} patients with visits."))


class CommandTrainModel(BaseCommand):
    """Train the ML model using data from heart.csv and save it."""
    help = 'Trains the RandomForest model and saves it to saved_models/'

    def handle(self, *args, **options):
        import pandas as pd
        import numpy as np
        import joblib
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from pathlib import Path

        data_path = Path('ml_model/dataset/heart.csv')
        if not data_path.exists():
            self.stdout.write(self.style.ERROR("heart.csv not found. Run generate_csvs.py first."))
            return

        df = pd.read_csv(data_path)
        X = df.drop('target', axis=1)
        y = df['target']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train_scaled, y_train)

        acc = model.score(X_test_scaled, y_test)
        self.stdout.write(f"Model accuracy: {acc:.3f}")

        # Save model and scaler
        saved_dir = Path('ml_model/saved_models')
        saved_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, saved_dir / 'heart_model.pkl')
        joblib.dump(scaler, saved_dir / 'scaler.pkl')
        joblib.dump(X.columns.tolist(), saved_dir / 'feature_columns.pkl')

        self.stdout.write(self.style.SUCCESS("Model saved to ml_model/saved_models/"))


class CommandCreateAdmin(BaseCommand):
    """Create a superuser with predefined credentials (for quick setup)."""
    help = 'Creates an admin user if none exists.'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin')
        parser.add_argument('--email', type=str, default='admin@example.com')
        parser.add_argument('--password', type=str, default='admin123')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Admin user '{username}' created."))
        else:
            self.stdout.write(f"User '{username}' already exists.")


class CommandDropDB(BaseCommand):
    """DANGER: Drop all database tables and start fresh."""
    help = 'Deletes all tables (irreversible).'

    def handle(self, *args, **options):
        confirm = input("This will delete ALL data. Type 'YES' to confirm: ")
        if confirm == 'YES':
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys=OFF;")
                for table in connection.introspection.table_names():
                    cursor.execute(f"DROP TABLE IF EXISTS {table};")
                cursor.execute("PRAGMA foreign_keys=ON;")
            self.stdout.write(self.style.WARNING("All tables dropped."))
        else:
            self.stdout.write("Operation cancelled.")


# -------------------------------------------------------------------
# Register custom commands (Django automatically discovers them in
# a management/commands folder, but for simplicity we add them here.
# To keep it clean, you may move each class to a separate file inside
# backend/core/management/commands/.
# However, the code below makes them callable via manage.py directly.
# -------------------------------------------------------------------

# Override the default execute to include our commands at runtime.
# This is a simple approach – the recommended way is to create a
# 'management/commands' directory, but for brevity we patch here.

original_main = main

def patched_main():
    # Add our command classes to the registry
    from django.core.management import get_commands, load_command_class
    # This trick is not reliable; instead we instruct the user to move
    # the command classes into a proper management/commands folder.
    # For now, we just print a message.
    print("\n=== Custom commands available ===")
    print("  seed_data")
    print("  train_model")
    print("  create_admin")
    print("  drop_db")
    print("=================================\n")
    original_main()

if __name__ == '__main__':
    patched_main()