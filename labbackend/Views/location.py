from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework import  status
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.forms.models import model_to_dict
from django.db.models import Max
import math

from ..models import SampleCollectorLocation

import json
#auth
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from pyauth.auth import HasRoleAndDataPermission

@api_view(['GET', 'POST', 'PUT'])
@csrf_exempt
@permission_classes([HasRoleAndDataPermission])
def sample_collector_location(request):
    """
    Handle GET, POST, and PUT requests for sample collector location
    GET: Retrieve location data
    POST: Create new location record (start tracking)
    PUT: Update existing location record (stop tracking)
    """
    if request.method == 'GET':
        try:
            # Extract parameters
            collector_name = request.GET.get('sampleCollector')
            date_str = request.GET.get('date', datetime.now().strftime('%Y-%m-%d'))
            if not collector_name:
                return JsonResponse({
                    'success': False,
                    'message': 'sampleCollector parameter is required'
                }, status=400)
            try:
                # Convert date string to date object
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid date format. Use YYYY-MM-DD.'
                }, status=400)
            # Find location data for the collector
            try:
                location = SampleCollectorLocation.objects.get(
                    sampleCollector=collector_name,
                    date=date_obj
                )
                # Convert Decimal128 values to float using safe_float function
                lat_start = location.latitudeStart
                long_start = location.longitudeStart
                lat_end = location.latitudeEnd
                long_end = location.longitudeEnd
                dist_travelled = location.distance_travelled
                return JsonResponse({
                    'success': True,
                    'id': str(location.id),
                    'sampleCollector': location.sampleCollector,
                    'date': date_str,
                    'latitudeStart': lat_start,
                    'longitudeStart': long_start,
                    'latitudeEnd': lat_end,
                    'longitudeEnd': long_end,
                    'distance_travelled': dist_travelled
                })
            except SampleCollectorLocation.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': f'No location data found for collector {collector_name} on {date_str}'
                }, status=404)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f'Error retrieving location data: {str(e)}'
            }, status=500)
    elif request.method == 'POST':
        # Create a new record (start tracking)
        try:
            data = json.loads(request.body)
            # Extract data from request
            sample_collector = data.get('sampleCollector')
            date_str = data.get('date')
            latitude_start = data.get('latitudeStart')
            longitude_start = data.get('longitudeStart')
            # Debug incoming data
            print(f"Received POST data: {data}")
            print(f"latitude_start type: {type(latitude_start)}, value: {latitude_start}")
            print(f"longitude_start type: {type(longitude_start)}, value: {longitude_start}")
            if not all([sample_collector, date_str, latitude_start is not None, longitude_start is not None]):
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required fields: sampleCollector, date, latitudeStart, longitudeStart'
                }, status=400)
            # Convert date string to date object
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            # Convert coordinates to Decimal - using string representation for consistency
            lat_start_decimal = latitude_start
            long_start_decimal = longitude_start
            # Debugging coordinate conversion
            print(f"Converted lat_start_decimal: {lat_start_decimal}")
            print(f"Converted long_start_decimal: {long_start_decimal}")
            if lat_start_decimal is None or long_start_decimal is None:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid coordinates provided. Could not convert to Decimal.'
                }, status=400)
            # Check if record already exists
            try:
                existing = SampleCollectorLocation.objects.get(
                    sampleCollector=sample_collector,
                    date=date_obj
                )
                # If it exists, update the start coordinates
                existing.latitudeStart = lat_start_decimal
                existing.longitudeStart = long_start_decimal
                existing.save()
                location = existing
            except SampleCollectorLocation.DoesNotExist:
                # Create new record
                location = SampleCollectorLocation(
                    sampleCollector=sample_collector,
                    date=date_obj,
                    latitudeStart=lat_start_decimal,
                    longitudeStart=long_start_decimal
                )
                location.save()
            return JsonResponse({
                'success': True,
                'message': 'Start location data saved successfully',
                'location_id': str(location.id)
            })
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f'Error saving start location data: {str(e)}'
            }, status=400)
    elif request.method == 'PUT':
        # Update an existing record (stop tracking)
        try:
            data = json.loads(request.body)
            # Extract data from request
            sample_collector = data.get('sampleCollector')
            date_str = data.get('date')
            latitude_end = data.get('latitudeEnd')
            longitude_end = data.get('longitudeEnd')
            # Debug incoming data
            print(f"Received PUT data: {data}")
            print(f"latitude_end type: {type(latitude_end)}, value: {latitude_end}")
            print(f"longitude_end type: {type(longitude_end)}, value: {longitude_end}")
            if not all([sample_collector, date_str, latitude_end is not None, longitude_end is not None]):
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required fields: sampleCollector, date, latitudeEnd, longitudeEnd'
                }, status=400)
            # Convert date string to date object
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            # Convert coordinates to Decimal - using string representation for consistency
            lat_end_decimal = latitude_end
            long_end_decimal = longitude_end
            # Debugging coordinate conversion
            print(f"Converted lat_end_decimal: {lat_end_decimal}")
            print(f"Converted long_end_decimal: {long_end_decimal}")
            if lat_end_decimal is None or long_end_decimal is None:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid coordinates provided. Could not convert to Decimal.'
                }, status=400)
            # Find existing record
            try:
                location = SampleCollectorLocation.objects.get(
                    sampleCollector=sample_collector,
                    date=date_obj
                )
                # Update end coordinates
                location.latitudeEnd = lat_end_decimal
                location.longitudeEnd = long_end_decimal
                # Calculate distance if start coordinates are available
                if location.latitudeStart is not None and location.longitudeStart is not None:
                    # Extract raw float values for calculation
                    lat1 = location.latitudeStart
                    lon1 = location.longitudeStart
                    lat2 = latitude_end
                    lon2 = longitude_end
                    print(f"Distance calculation inputs: ({lat1}, {lon1}) to ({lat2}, {lon2})")
                    if all([lat1 is not None, lon1 is not None, lat2 is not None, lon2 is not None]):
                        distance = calculate_distance(lat1, lon1, lat2, lon2)
                        print(f"Calculated distance: {distance}")
                        # Convert distance to Decimal for storage
                        distance_decimal = distance
                        location.distance_travelled = distance_decimal
                    else:
                        print("Cannot calculate distance: some coordinates are None")
                location.save()
                # Convert distance_travelled to float safely for response
                dist_travelled = location.distance_travelled
                return JsonResponse({
                    'success': True,
                    'message': 'End location data updated successfully',
                    'location_id': str(location.id),
                    'distance_travelled': dist_travelled
                })
            except SampleCollectorLocation.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': f'No location record found for {sample_collector} on {date_str}. Start tracking first.'
                }, status=404)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f'Error updating end location data: {str(e)}'
            }, status=400)
    else:
        return JsonResponse({
            'success': False,
            'message': 'Method not allowed'
        }, status=405)

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points on Earth using the Haversine formula
    Returns distance in meters
    """
    # Convert input values to float if they're not already
    lat1 = float(lat1)
    lon1 = float(lon1)
    lat2 = float(lat2)
    lon2 = float(lon2)
    # Earth's radius in meters
    R = 6371000
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    # Haversine formula
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    return round(distance, 2)  # Round to 2 decimal places