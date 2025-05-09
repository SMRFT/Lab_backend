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
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User


from django.contrib.auth.hashers import make_password
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
    Handle GET, POST, PUT, and PATCH requests for sample collector location
    GET: Retrieve location data using Django ORM
    POST: Create new location record using Django ORM (start tracking)
    PUT: Update existing location record using MongoDB (stop tracking)
    PATCH: Update location history with new coordinates (live tracking)
    """
    if request.method == 'GET':
        try:
            # Extract parameters
            collector_name = request.GET.get('sampleCollector')
            date_str = request.GET.get('date', datetime.now(IST).strftime('%Y-%m-%d'))
            
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
            
            # Connect to MongoDB directly to avoid serialization issues
            client = None
            try:
                password = quote_plus('Smrft@2024')
                client = MongoClient(
                    'mongodb://admin:ifS2nTs6vm@103.205.141.208:27017/Lab?authSource=admin',
                    tls=True,
                    tlsAllowInvalidCertificates=True  # <-- bypass certificate verification
                )
                db = client.Lab
                collection = db['labbackend_samplecollectorlocation']
                
                # Find document directly in MongoDB
                start_of_day = datetime.combine(date_obj, datetime.min.time())
                end_of_day = datetime.combine(date_obj, datetime.max.time())
                
                filter_query = {
                    'sampleCollector': collector_name,
                    'date': {'$gte': start_of_day, '$lte': end_of_day}
                }
                
                docs = list(collection.find(filter_query))
                
                if docs:
                    location_list = []
                    for doc in docs:
                        # Convert MongoDB document to JSON-serializable format
                        # Convert UTC timestamps to IST for display
                        start_time_ist = doc.get('startTime').replace(tzinfo=timezone.utc).astimezone(IST).isoformat() if doc.get('startTime') else None
                        end_time_ist = doc.get('endTime').replace(tzinfo=timezone.utc).astimezone(IST).isoformat() if doc.get('endTime') else None
                        
                        # Convert location history timestamps to IST
                        location_history = doc.get('location_history', [])
                        for point in location_history:
                            if 'timestamp' in point:
                                try:
                                    # Parse the timestamp and convert to IST
                                    ts = datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00'))
                                    point['timestamp'] = ts.replace(tzinfo=timezone.utc).astimezone(IST).isoformat()
                                except (ValueError, AttributeError):
                                    # If timestamp format is unusual, keep the original
                                    pass
                        
                        location_data = {
                            'id': str(doc['_id']),
                            'sampleCollector': doc['sampleCollector'],
                            'date': doc['date'].replace(tzinfo=timezone.utc).astimezone(IST).strftime('%Y-%m-%d'),
                            'latitudeStart': doc.get('latitudeStart', ''),
                            'longitudeStart': doc.get('longitudeStart', ''),
                            'startTime': start_time_ist,
                            'latitudeEnd': doc.get('latitudeEnd', ''),
                            'longitudeEnd': doc.get('longitudeEnd', ''),
                            'endTime': end_time_ist,
                            'distance_travelled': doc.get('distance_travelled', '0.0'),
                            'location_history': location_history
                        }
                        location_list.append(location_data)
                    
                    return JsonResponse({
                        'success': True,
                        'data': location_list
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': f'No location data found for collector {collector_name} on {date_str}'
                    }, status=404)
            finally:
                if client:
                    client.close()
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'message': f'Error retrieving location data: {str(e)}'
            }, status=500)
            
    elif request.method == 'POST':
        # Create a new record (start tracking) using Django ORM
        try:
            data = json.loads(request.body)
            
            # Extract data from request
            sample_collector = data.get('sampleCollector')
            date_str = data.get('date')
            latitude_start = data.get('latitudeStart')
            longitude_start = data.get('longitudeStart')
            
            # Debug incoming data
            print(f"Received POST data: {data}")
            
            if not all([sample_collector, date_str, latitude_start is not None, longitude_start is not None]):
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required fields: sampleCollector, date, latitudeStart, longitudeStart'
                }, status=400)
            
            # Convert date string to date object
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Use current time in IST
            current_time = datetime.now(IST)
            
            # Check if record already exists using Django ORM
            existing_location = SampleCollectorLocation.objects.filter(
                sampleCollector=sample_collector,
                date=date_obj
            ).first()
            
            if existing_location:
                # Update existing record
                existing_location.latitudeStart = str(latitude_start)
                existing_location.longitudeStart = str(longitude_start)
                existing_location.startTime = current_time
                
                # Initialize or reset location history with start point
                initial_history = [{
                    'timestamp': current_time.isoformat(),
                    'latitude': str(latitude_start),
                    'longitude': str(longitude_start)
                }]
                existing_location.location_history = initial_history
                
                existing_location.save()
                
                serializer = SampleCollectorLocationSerializer(existing_location)
                return JsonResponse({
                    'success': True,
                    'message': 'Location record updated successfully',
                    'data': serializer.data
                })
            else:
                # Create new record with location history
                initial_history = [{
                    'timestamp': current_time.isoformat(),
                    'latitude': str(latitude_start),
                    'longitude': str(longitude_start)
                }]
                
                new_location = SampleCollectorLocation.objects.create(
                    sampleCollector=sample_collector,
                    date=date_obj,
                    latitudeStart=str(latitude_start),
                    longitudeStart=str(longitude_start),
                    startTime=current_time,
                    latitudeEnd="",
                    longitudeEnd="", 
                    endTime=None,
                    distance_travelled="",
                    location_history=initial_history
                )

                serializer = SampleCollectorLocationSerializer(new_location)
                return JsonResponse({
                    'success': True,
                    'message': 'New location record created successfully',
                    'data': serializer.data
                })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'message': f'Error saving start location data: {str(e)}'
            }, status=400)
            
    elif request.method == 'PUT':
        # Update an existing record (stop tracking) using MongoDB directly
        try:
            data = json.loads(request.body)
            
            # Extract data from request
            sample_collector = data.get('sampleCollector')
            date_str = data.get('date')
            latitude_end = data.get('latitudeEnd')
            longitude_end = data.get('longitudeEnd')
            
            # Debug incoming data
            print(f"Received PUT data: {data}")
            
            if not all([sample_collector, date_str, latitude_end is not None, longitude_end is not None]):
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required fields: sampleCollector, date, latitudeEnd, longitudeEnd'
                }, status=400)
            
            # Convert date string to date object
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Use current time in IST
            current_time = datetime.now(IST)
            
            # Connect to MongoDB
            client = None
            try:
                password = quote_plus('Smrft@2024')
                client = MongoClient(
                    'mongodb://admin:ifS2nTs6vm@103.205.141.208:27017/Lab?authSource=admin',
                    tls=True,
                    tlsAllowInvalidCertificates=True  # <-- bypass certificate verification
                )
                db = client.Lab
                collection = db['labbackend_samplecollectorlocation']
                
                # Find document directly in MongoDB using sample collector and date
                # Convert date to ISODate format for MongoDB query
                start_of_day = datetime.combine(date_obj, datetime.min.time())
                end_of_day = datetime.combine(date_obj, datetime.max.time())
                
                filter_query = {
                    'sampleCollector': sample_collector,
                    'date': {'$gte': start_of_day, '$lte': end_of_day}
                }
                
                # Get existing document to calculate distance
                existing_doc = collection.find_one(filter_query)
                
                if existing_doc:
                    print(f"Found existing doc: {existing_doc}")
                    
                    # Add the end location to location_history
                    location_history = existing_doc.get('location_history', [])
                    if not isinstance(location_history, list):
                        location_history = []
                    
                    location_history.append({
                        'timestamp': current_time.isoformat(),
                        'latitude': str(latitude_end),
                        'longitude': str(longitude_end)
                    })
                    
                    # Calculate distance if start coordinates are available
                    distance_travelled = "0.0"
                    if 'latitudeStart' in existing_doc and 'longitudeStart' in existing_doc:
                        try:
                            # Calculate total distance through all points in location_history
                            total_distance = 0
                            for i in range(1, len(location_history)):
                                prev_point = location_history[i-1]
                                curr_point = location_history[i]
                                
                                try:
                                    lat1 = float(prev_point['latitude'])
                                    lon1 = float(prev_point['longitude'])
                                    lat2 = float(curr_point['latitude'])
                                    lon2 = float(curr_point['longitude'])
                                    
                                    segment_distance = calculate_distance(lat1, lon1, lat2, lon2)
                                    total_distance += segment_distance
                                except (ValueError, TypeError, KeyError) as e:
                                    print(f"Error calculating segment distance: {e}")
                            
                            # Round and convert to string
                            distance_travelled = str(round(total_distance / 1000, 2))  # Convert to km
                            print(f"Calculated total distance: {distance_travelled} km")
                        except (ValueError, TypeError) as e:
                            print(f"Error calculating distance: {e}")
                    
                    # Update the document
                    update_data = {
                        '$set': {
                            'latitudeEnd': str(latitude_end),
                            'longitudeEnd': str(longitude_end),
                            'endTime': current_time.replace(tzinfo=None),  # Remove timezone for MongoDB
                            'distance_travelled': distance_travelled,
                            'location_history': location_history
                        }
                    }
                    
                    # Perform the update operation
                    result = collection.update_one({'_id': existing_doc['_id']}, update_data)
                    
                    if result.modified_count > 0 or result.matched_count > 0:
                        # Get the updated document
                        updated_doc = collection.find_one({'_id': existing_doc['_id']})
                        
                        # Convert timestamps to IST for response
                        start_time_ist = updated_doc.get('startTime').replace(tzinfo=timezone.utc).astimezone(IST).isoformat() if updated_doc.get('startTime') else None
                        end_time_ist = updated_doc.get('endTime').replace(tzinfo=timezone.utc).astimezone(IST).isoformat() if updated_doc.get('endTime') else None
                        
                        return JsonResponse({
                            'success': True,
                            'message': 'End location data updated successfully',
                            'data': {
                                'id': str(updated_doc['_id']),
                                'sampleCollector': updated_doc['sampleCollector'],
                                'date': updated_doc['date'].replace(tzinfo=timezone.utc).astimezone(IST).strftime('%Y-%m-%d'),
                                'latitudeStart': updated_doc.get('latitudeStart', ''),
                                'longitudeStart': updated_doc.get('longitudeStart', ''),
                                'startTime': start_time_ist,
                                'latitudeEnd': updated_doc.get('latitudeEnd', ''),
                                'longitudeEnd': updated_doc.get('longitudeEnd', ''),
                                'endTime': end_time_ist,
                                'distance_travelled': updated_doc.get('distance_travelled', ''),
                                'location_history': updated_doc.get('location_history', [])
                            }
                        })
                    else:
                        return JsonResponse({
                            'success': False,
                            'message': 'Document found but not updated. No changes made.'
                        }, status=400)
                
                else:
                    # Alternative approach: Try to find by ObjectId if we have the ID
                    if '_id' in data and data['_id']:
                        try:
                            object_id = ObjectId(data['_id'])
                            existing_doc = collection.find_one({'_id': object_id})
                            if existing_doc:
                                # Similar logic as above for updating the document
                                # (Code would be duplicated here)
                                pass
                        except Exception as e:
                            print(f"Error finding document by ObjectId: {e}")
                    
                    # If we still haven't found the document, return an error
                    return JsonResponse({
                        'success': False,
                        'message': f'No location record found for {sample_collector} on {date_str}. Start tracking first.'
                    }, status=404)
            finally:
                if client:
                    client.close()
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'message': f'Error updating end location data: {str(e)}'
            }, status=400)
    
    elif request.method == 'PATCH':
        # Update location history with new coordinates (for live tracking)
        try:
            data = json.loads(request.body)
            
            # Extract data from request
            sample_collector = data.get('sampleCollector')
            date_str = data.get('date')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            if not all([sample_collector, date_str, latitude is not None, longitude is not None]):
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required fields: sampleCollector, date, latitude, longitude'
                }, status=400)
            
            # Convert date string to date object
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Use current time in IST
            current_time = datetime.now(IST)
            
            # Connect to MongoDB
            client = None
            try:
                password = quote_plus('Smrft@2024')
                client = MongoClient(
                    'mongodb://admin:ifS2nTs6vm@103.205.141.208:27017/Lab?authSource=admin',
                    tls=True,
                    tlsAllowInvalidCertificates=True  # <-- bypass certificate verification
                )
                db = client.Lab
                collection = db['labbackend_samplecollectorlocation']
                
                # Find document directly in MongoDB
                start_of_day = datetime.combine(date_obj, datetime.min.time())
                end_of_day = datetime.combine(date_obj, datetime.max.time())
                
                filter_query = {
                    'sampleCollector': sample_collector,
                    'date': {'$gte': start_of_day, '$lte': end_of_day}
                }
                
                existing_doc = collection.find_one(filter_query)
                
                if existing_doc:
                    # Add the new location to location_history
                    location_history = existing_doc.get('location_history', [])
                    if not isinstance(location_history, list):
                        location_history = []
                    
                    # Add new point with IST timestamp
                    new_point = {
                        'timestamp': current_time.isoformat(),
                        'latitude': str(latitude),
                        'longitude': str(longitude)
                    }
                    location_history.append(new_point)
                    
                    # Calculate running distance
                    distance_travelled = "0.0"
                    if len(location_history) > 1:
                        try:
                            # Calculate total distance through all points in location_history
                            total_distance = 0
                            for i in range(1, len(location_history)):
                                prev_point = location_history[i-1]
                                curr_point = location_history[i]
                                
                                try:
                                    lat1 = float(prev_point['latitude'])
                                    lon1 = float(prev_point['longitude'])
                                    lat2 = float(curr_point['latitude'])
                                    lon2 = float(curr_point['longitude'])
                                    
                                    segment_distance = calculate_distance(lat1, lon1, lat2, lon2)
                                    total_distance += segment_distance
                                except (ValueError, TypeError, KeyError) as e:
                                    print(f"Error calculating segment distance: {e}")
                            
                            # Round and convert to string (km)
                            distance_travelled = str(round(total_distance / 1000, 2))
                        except Exception as e:
                            print(f"Error calculating total distance: {e}")
                    
                    # Update the document
                    update_data = {
                        '$set': {
                            'location_history': location_history,
                            'distance_travelled': distance_travelled
                        }
                    }
                    
                    result = collection.update_one({'_id': existing_doc['_id']}, update_data)
                    
                    if result.modified_count > 0 or result.matched_count > 0:
                        # Get the updated document
                        updated_doc = collection.find_one({'_id': existing_doc['_id']})
                        
                        return JsonResponse({
                            'success': True,
                            'message': 'Location history updated successfully',
                            'data': {
                                'id': str(updated_doc['_id']),
                                'sampleCollector': updated_doc['sampleCollector'],
                                'currentLocation': new_point,
                                'distance_travelled': updated_doc.get('distance_travelled', ''),
                                'location_history': updated_doc.get('location_history', [])
                            }
                        })
                    else:
                        return JsonResponse({
                            'success': False,
                            'message': 'Document found but not updated. No changes made.'
                        }, status=400)
                else:
                    return JsonResponse({
                        'success': False,
                        'message': f'No active tracking session found for {sample_collector} on {date_str}. Start tracking first.'
                    }, status=404)
            finally:
                if client:
                    client.close()
                    
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'message': f'Error updating location history: {str(e)}'
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