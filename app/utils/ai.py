from typing import List, Dict

# Simple stub for AI food recognition. Replace with real service integration.
def recognize(image_file) -> List[Dict]:
    # In real implementation, send image_file.stream to external service
    # Here we just return a static guess list for development
    return [
        {"label": "ayam", "confidence": 0.82},
        {"label": "kentang", "confidence": 0.61},
    ]
