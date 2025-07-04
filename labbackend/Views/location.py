from rest_framework.response import Response
from django.http import JsonResponse
from datetime import datetime, timedelta
from rest_framework.decorators import api_view
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
import json
import math
from django.utils import timezone
from ..models import SampleCollectorLocation

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in meters
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in meters
    r = 6371000
    return c * r

@api_view(['GET', 'POST', 'PUT'])
@csrf_exempt
def sample_collector_location(request):
    """
    Enhanced endpoint for sample collector location tracking
    GET: Retrieve location data (supports both single collector and date-based queries)
    POST: Start tracking (save start location)
    PUT: Update current location or end tracking
    """
    
    if request.method == 'GET':
        try:
            date = request.GET.get('date')
            sample_collector = request.GET.get('sampleCollector')
            
            # If no parameters provided, return all data
            if not date and not sample_collector:
                # Return all location data for dashboard stats
                all_data = SampleCollectorLocation.objects.all().order_by('-date', '-lastUpdated')
                
                response_data = {
                    'success': True,
                    'data': []
                }
                
                for location_data in all_data:
                    # Parse route points if available
                    route_points = []
                    if location_data.routePoints:
                        try:
                            route_points = json.loads(location_data.routePoints)
                        except json.JSONDecodeError:
                            route_points = []
                    
                    response_data['data'].append({
                        'id': location_data.id,
                        'sampleCollector': location_data.sampleCollector,
                        'date': location_data.date,
                        'latitudeStart': location_data.latitudeStart,
                        'longitudeStart': location_data.longitudeStart,
                        'latitudeEnd': location_data.latitudeEnd,
                        'longitudeEnd': location_data.longitudeEnd,
                        'currentLatitude': location_data.currentLatitude,
                        'currentLongitude': location_data.currentLongitude,
                        'distance_travelled': location_data.distance_travelled or "0.00",
                        'startTime': location_data.startTime.isoformat() if location_data.startTime else None,
                        'endTime': location_data.endTime.isoformat() if location_data.endTime else None,
                        'totalDuration': location_data.totalDuration,
                        'isActive': location_data.isActive,
                        'lastUpdated': location_data.lastUpdated.isoformat(),
                        'routePoints': route_points
                    })
                
                return JsonResponse(response_data)
            
            # If only date is provided, return all collectors for that date
            elif date and not sample_collector:
                try:
                    # Parse the date string to ensure it's valid
                    date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                    
                    location_data_list = SampleCollectorLocation.objects.filter(
                        date=date_obj
                    ).order_by('-lastUpdated')
                    
                    response_data = {
                        'success': True,
                        'data': []
                    }
                    
                    for location_data in location_data_list:
                        # Parse route points if available
                        route_points = []
                        if location_data.routePoints:
                            try:
                                route_points = json.loads(location_data.routePoints)
                            except json.JSONDecodeError:
                                route_points = []
                        
                        response_data['data'].append({
                            'id': location_data.id,
                            'sampleCollector': location_data.sampleCollector,
                            'date': location_data.date,
                            'latitudeStart': location_data.latitudeStart,
                            'longitudeStart': location_data.longitudeStart,
                            'latitudeEnd': location_data.latitudeEnd,
                            'longitudeEnd': location_data.longitudeEnd,
                            'currentLatitude': location_data.currentLatitude,
                            'currentLongitude': location_data.currentLongitude,
                            'distance_travelled': location_data.distance_travelled or "0.00",
                            'startTime': location_data.startTime.isoformat() if location_data.startTime else None,
                            'endTime': location_data.endTime.isoformat() if location_data.endTime else None,
                            'totalDuration': location_data.totalDuration,
                            'isActive': location_data.isActive,
                            'lastUpdated': location_data.lastUpdated.isoformat(),
                            'routePoints': route_points
                        })
                    
                    if not response_data['data']:
                        return JsonResponse({
                            'success': False,
                            'message': 'No location data found for the specified date'
                        })
                    
                    return JsonResponse(response_data)
                    
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid date format. Please use YYYY-MM-DD format'
                    }, status=400)
            
            # If both date and sample_collector are provided
            else:
                try:
                    # Parse the date string to ensure it's valid
                    date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                    
                    location_data = SampleCollectorLocation.objects.get(
                        sampleCollector=sample_collector,
                        date=date_obj
                    )
                    
                    # Parse route points if available
                    route_points = []
                    if location_data.routePoints:
                        try:
                            route_points = json.loads(location_data.routePoints)
                        except json.JSONDecodeError:
                            route_points = []
                    
                    response_data = {
                        'success': True,
                        'data': [{
                            'id': location_data.id,
                            'sampleCollector': location_data.sampleCollector,
                            'date': location_data.date,
                            'latitudeStart': location_data.latitudeStart,
                            'longitudeStart': location_data.longitudeStart,
                            'latitudeEnd': location_data.latitudeEnd,
                            'longitudeEnd': location_data.longitudeEnd,
                            'currentLatitude': location_data.currentLatitude,
                            'currentLongitude': location_data.currentLongitude,
                            'distance_travelled': location_data.distance_travelled or "0.00",
                            'startTime': location_data.startTime.isoformat() if location_data.startTime else None,
                            'endTime': location_data.endTime.isoformat() if location_data.endTime else None,
                            'totalDuration': location_data.totalDuration,
                            'isActive': location_data.isActive,
                            'lastUpdated': location_data.lastUpdated.isoformat(),
                            'routePoints': route_points
                        }]
                    }
                    
                    return JsonResponse(response_data)
                    
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid date format. Please use YYYY-MM-DD format'
                    }, status=400)
                except SampleCollectorLocation.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'No location data found for the specified collector and date'
                    })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error retrieving location data: {str(e)}'
            }, status=500)
    
    elif request.method == 'POST':
        # Start tracking - save initial location
        try:
            data = json.loads(request.body.decode('utf-8'))
            sample_collector = data.get('sampleCollector')
            date = data.get('date')
            latitude_start = data.get('latitudeStart')
            longitude_start = data.get('longitudeStart')
            
            if not all([sample_collector, date, latitude_start, longitude_start]):
                return JsonResponse({
                    'success': False,
                    'message': 'sampleCollector, date, latitudeStart, and longitudeStart are required'
                }, status=400)
            
            # Parse the date string
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid date format. Please use YYYY-MM-DD format'
                }, status=400)
            
            # Create or update location record
            location_id = f"{sample_collector}_{date}"
            
            location_data, created = SampleCollectorLocation.objects.get_or_create(
                id=location_id,
                defaults={
                    'sampleCollector': sample_collector,
                    'date': date_obj,
                    'latitudeStart': str(latitude_start),
                    'longitudeStart': str(longitude_start),
                    'currentLatitude': str(latitude_start),
                    'currentLongitude': str(longitude_start),
                    'startTime': timezone.now(),
                    'isActive': True,
                    'routePoints': json.dumps([{
                        'lat': latitude_start, 
                        'lng': longitude_start, 
                        'timestamp': timezone.now().isoformat()
                    }])
                }
            )
            
            if not created:
                # Update existing record if restarting
                location_data.latitudeStart = str(latitude_start)
                location_data.longitudeStart = str(longitude_start)
                location_data.currentLatitude = str(latitude_start)
                location_data.currentLongitude = str(longitude_start)
                location_data.startTime = timezone.now()
                location_data.isActive = True
                location_data.endTime = None
                location_data.latitudeEnd = None
                location_data.longitudeEnd = None
                location_data.distance_travelled = None
                location_data.totalDuration = None
                location_data.routePoints = json.dumps([{
                    'lat': latitude_start, 
                    'lng': longitude_start, 
                    'timestamp': timezone.now().isoformat()
                }])
                location_data.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Location tracking started successfully',
                'data': {
                    'id': location_data.id,
                    'startTime': location_data.startTime.isoformat(),
                    'isActive': location_data.isActive
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error starting location tracking: {str(e)}'
            }, status=500)
    
    elif request.method == 'PUT':
        # Update current location or end tracking
        try:
            data = json.loads(request.body.decode('utf-8'))
            sample_collector = data.get('sampleCollector')
            date = data.get('date')
            
            if not sample_collector or not date:
                return JsonResponse({
                    'success': False,
                    'message': 'sampleCollector and date are required'
                }, status=400)
            
            # Parse the date string
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid date format. Please use YYYY-MM-DD format'
                }, status=400)
            
            # Get existing location record
            try:
                location_data = SampleCollectorLocation.objects.get(
                    sampleCollector=sample_collector,
                    date=date_obj
                )
            except SampleCollectorLocation.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'No active tracking session found for this collector and date'
                }, status=404)
            
            # Check if this is an end tracking request
            latitude_end = data.get('latitudeEnd')
            longitude_end = data.get('longitudeEnd')
            
            if latitude_end and longitude_end:
                # End tracking
                location_data.latitudeEnd = str(latitude_end)
                location_data.longitudeEnd = str(longitude_end)
                location_data.currentLatitude = str(latitude_end)
                location_data.currentLongitude = str(longitude_end)
                location_data.endTime = timezone.now()
                location_data.isActive = False
                
                # Calculate total distance if we have start and end points
                if location_data.latitudeStart and location_data.longitudeStart:
                    # Parse route points to calculate total distance
                    total_distance = 0
                    route_points = []
                    
                    if location_data.routePoints:
                        try:
                            route_points = json.loads(location_data.routePoints)
                        except json.JSONDecodeError:
                            route_points = []
                    
                    # Add end point to route
                    route_points.append({
                        'lat': latitude_end,
                        'lng': longitude_end,
                        'timestamp': timezone.now().isoformat()
                    })
                    
                    # Calculate distance between consecutive points
                    for i in range(1, len(route_points)):
                        prev_point = route_points[i-1]
                        curr_point = route_points[i]
                        distance = calculate_distance(
                            prev_point['lat'], prev_point['lng'],
                            curr_point['lat'], curr_point['lng']
                        )
                        total_distance += distance
                    
                    # Convert to kilometers
                    total_distance_km = total_distance / 1000
                    location_data.distance_travelled = f"{total_distance_km:.2f}"
                    location_data.routePoints = json.dumps(route_points)
                
                # Calculate duration
                if location_data.startTime:
                    location_data.totalDuration = location_data.calculate_duration()
                
                location_data.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Location tracking ended successfully',
                    'data': {
                        'distance_travelled': location_data.distance_travelled,
                        'totalDuration': location_data.totalDuration,
                        'endTime': location_data.endTime.isoformat()
                    }
                })
            
            else:
                # Update current location (live tracking)
                current_lat = data.get('currentLatitude')
                current_lng = data.get('currentLongitude')
                
                if current_lat and current_lng:
                    location_data.currentLatitude = str(current_lat)
                    location_data.currentLongitude = str(current_lng)
                    location_data.lastUpdated = timezone.now()
                    
                    # Add point to route
                    route_points = []
                    if location_data.routePoints:
                        try:
                            route_points = json.loads(location_data.routePoints)
                        except json.JSONDecodeError:
                            route_points = []
                    
                    # Add new point if it's significantly different from the last point
                    if not route_points or calculate_distance(
                        route_points[-1]['lat'], route_points[-1]['lng'],
                        current_lat, current_lng
                    ) > 10:  # Only add if moved more than 10 meters
                        route_points.append({
                            'lat': current_lat,
                            'lng': current_lng,
                            'timestamp': timezone.now().isoformat()
                        })
                        location_data.routePoints = json.dumps(route_points)
                    
                    location_data.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Current location updated successfully'
                    })
                
                return JsonResponse({
                    'success': False,
                    'message': 'No valid location data provided for update'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error updating location: {str(e)}'
            }, status=500)

@api_view(['GET'])
def get_active_collectors(request):
    """Get all currently active collectors for live tracking"""
    try:
        today = datetime.now().date()
        active_collectors = SampleCollectorLocation.objects.filter(
            date=today,
            isActive=True
        ).values(
            'sampleCollector',
            'currentLatitude',
            'currentLongitude',
            'startTime',
            'lastUpdated',
            'distance_travelled'
        )
        
        return JsonResponse({
            'success': True,
            'data': list(active_collectors)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error retrieving active collectors: {str(e)}'
        }, status=500)

@api_view(['GET'])
def get_collector_route(request):
    """Get the complete route for a collector on a specific date"""
    try:
        sample_collector = request.GET.get('sampleCollector')
        date = request.GET.get('date')
        
        if not sample_collector or not date:
            return JsonResponse({
                'success': False,
                'message': 'sampleCollector and date parameters are required'
            }, status=400)
        
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            
            location_data = SampleCollectorLocation.objects.get(
                sampleCollector=sample_collector,
                date=date_obj
            )
            
            route_points = []
            if location_data.routePoints:
                try:
                    route_points = json.loads(location_data.routePoints)
                except json.JSONDecodeError:
                    route_points = []
            
            return JsonResponse({
                'success': True,
                'data': {
                    'sampleCollector': location_data.sampleCollector,
                    'date': location_data.date,
                    'routePoints': route_points,
                    'distance_travelled': location_data.distance_travelled,
                    'totalDuration': location_data.totalDuration,
                    'isActive': location_data.isActive
                }
            })
            
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid date format. Please use YYYY-MM-DD format'
            }, status=400)
        except SampleCollectorLocation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'No route data found for the specified collector and date'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error retrieving route data: {str(e)}'
        }, status=500)

@api_view(['GET'])
def get_live_tracking_data(request):
    """Get live tracking data for current date"""
    try:
        today = datetime.now().date()
        
        # Get all location data for today
        today_data = SampleCollectorLocation.objects.filter(
            date=today
        ).order_by('-lastUpdated')
        
        response_data = {
            'success': True,
            'data': []
        }
        
        for location_data in today_data:
            # Parse route points if available
            route_points = []
            if location_data.routePoints:
                try:
                    route_points = json.loads(location_data.routePoints)
                except json.JSONDecodeError:
                    route_points = []
            
            response_data['data'].append({
                'id': location_data.id,
                'sampleCollector': location_data.sampleCollector,
                'date': location_data.date,
                'latitudeStart': location_data.latitudeStart,
                'longitudeStart': location_data.longitudeStart,
                'latitudeEnd': location_data.latitudeEnd,
                'longitudeEnd': location_data.longitudeEnd,
                'currentLatitude': location_data.currentLatitude,
                'currentLongitude': location_data.currentLongitude,
                'distance_travelled': location_data.distance_travelled or "0.00",
                'startTime': location_data.startTime.isoformat() if location_data.startTime else None,
                'endTime': location_data.endTime.isoformat() if location_data.endTime else None,
                'totalDuration': location_data.totalDuration,
                'isActive': location_data.isActive,
                'lastUpdated': location_data.lastUpdated.isoformat(),
                'routePoints': route_points
            })
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error retrieving live tracking data: {str(e)}'
        }, status=500)