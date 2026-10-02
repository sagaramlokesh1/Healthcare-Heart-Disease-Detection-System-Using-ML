# Add this to settings.py
import sys
sys.path.append(os.path.join(BASE_DIR, 'ml_model'))

# Ensure TEMPLATES looks into your frontend folder
TEMPLATES = [
    {
        'DIRS': [BASE_DIR / 'frontend/templates'],
    
    },
]

# Ensure STATICFILES looks into your frontend static
STATICFILES_DIRS = [BASE_DIR / 'frontend/static']