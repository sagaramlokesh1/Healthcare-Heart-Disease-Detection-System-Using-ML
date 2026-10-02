"""
Django ML service wrapper for production deployment.
Handles model loading, caching, and prediction serving.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any
import joblib
from ml_model.predict import HeartDiseasePredictor

logger = logging.getLogger(__name__)

class HeartDiseasePredictorService:
    """Singleton service for ML predictions."""
    
    _instance = None
    _predictor = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._predictor is None:
            model_path = Path(__file__).parent.parent / 'ml_model/saved_models'
            self._predictor = HeartDiseasePredictor(str(model_path))
    
    def predict(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make prediction using cached predictor."""
        return self._predictor.predict(patient_data)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata."""
        return {
            'model_type': type(self._predictor.model).__name__,
            'n_features': len(self._predictor.feature_columns),
            'feature_columns': self._predictor.feature_columns[:10] + ['...'],  # First 10
            'version': '1.0.0'
        }
    
    @classmethod
    def is_model_ready(cls) -> bool:
        """Check if model is ready for predictions."""
        model_dir = Path(__file__).parent.parent / 'ml_model/saved_models'
        required_files = ['model.pkl', 'scaler.pkl', 'feature_columns.pkl']
        return all((model_dir / f).exists() for f in required_files)