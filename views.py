from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
from pathlib import Path
from .ml_service import HeartDiseasePredictorService
import os

logger = logging.getLogger(__name__)

def home(request):
    """Home page with prediction form."""
    context = {
        'model_ready': HeartDiseasePredictorService.is_model_ready()
    }
    return render(request, 'heartdisease/home.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def predict(request):
    """API endpoint for heart disease prediction."""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = [
            'age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 'restecg',
            'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal'
        ]
        
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'error': f'Missing required field: {field}'
                }, status=400)
        
        predictor = HeartDiseasePredictorService()
        result = predictor.predict(data)
        
        return JsonResponse({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Prediction API error: {e}")
        return JsonResponse({
            'error': str(e)
        }, status=500)

def model_status(request):
    """Check model status and metadata."""
    try:
        predictor = HeartDiseasePredictorService()
        status = predictor.get_model_info()
        
        return JsonResponse({
            'model_ready': True,
            'model_info': status
        })
    except Exception as e:
        return JsonResponse({
            'model_ready': False,
            'error': str(e)
        })