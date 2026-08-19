import uuid
import pytest
from app.services.hospital_service import haversine_distance


def test_haversine_distance_known_coordinates():
    # London (51.5074, -0.1278) to Paris (48.8566, 2.3522)
    # Expected distance is ~343.5 km
    dist = haversine_distance(51.5074, -0.1278, 48.8566, 2.3522)
    assert 340.0 <= dist <= 347.0


def test_haversine_distance_same_point():
    dist = haversine_distance(12.9716, 77.5946, 12.9716, 77.5946)
    assert dist == 0.0


def test_nearest_hospital_selection_logic():
    # Point at MG Road, Bangalore: (12.9716, 77.5946)
    ref_lat, ref_lng = 12.9716, 77.5946

    # Hospital A: ~1.5 km away (Indiranagar)
    hosp_a = {"name": "Indiranagar Hospital", "lat": 12.9784, "lng": 78.0000}
    # Hospital B: ~0.5 km away (Brigade Road)
    hosp_b = {"name": "Brigade Road City Clinic", "lat": 12.9720, "lng": 77.5960}
    # Hospital C: ~15 km away (Electronic City)
    hosp_c = {"name": "Electronic City Trauma Center", "lat": 12.8452, "lng": 77.6602}

    hospitals = [hosp_a, hosp_b, hosp_c]
    sorted_hospitals = sorted(
        hospitals,
        key=lambda h: haversine_distance(ref_lat, ref_lng, h["lat"], h["lng"])
    )

    assert sorted_hospitals[0]["name"] == "Brigade Road City Clinic"
    assert sorted_hospitals[-1]["name"] == "Indiranagar Hospital" or sorted_hospitals[-1]["name"] == "Electronic City Trauma Center"
