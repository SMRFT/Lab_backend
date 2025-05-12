
from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
import json
from urllib.parse import quote_plus
from django.utils import timezone 
from datetime import timedelta
from datetime import datetime
import os
from pymongo import MongoClient
#models
from ..models import SampleStatus 
from ..models import BarcodeTestDetails

from ..auth.permissions import SkipPermissionsIfDisabled
#auth
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from pyauth.auth import HasRoleAndDataPermission
from dotenv import load_dotenv

load_dotenv()

@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_samplepatients_by_date(request):
    date = request.GET.get('date')
    if not date:
        return JsonResponse({'error': 'Date parameter is required.'}, status=400)
    try:
        # Parse the input date with time (timezone-aware or naive)
        parsed_date = datetime.fromisoformat(date)
        # Get all patient IDs in SampleStatus with the given exact date and test details
        sample_status_ids = SampleStatus.objects.filter(date__gte=parsed_date, date__lt=parsed_date + timedelta(days=1)).values_list('patient_id', 'testdetails')
        # Prepare a set of patient_id-test combinations in SampleStatus
        existing_samples = set()
        for patient_id, testdetails in sample_status_ids:
            for test in testdetails:
                existing_samples.add((patient_id, test['testname']))
        # Filter patients that are not in SampleStatus
        patients = BarcodeTestDetails.objects.filter(date__gte=parsed_date, date__lt=parsed_date + timedelta(days=1)).exclude(
            patient_id__in=[item[0] for item in existing_samples]
        )
        # Check if test names overlap for each patient
        filtered_patients = []
        for patient in patients:
            patient_tests = {test['testname'] for test in patient.tests}
            if not any((patient.patient_id, test) in existing_samples for test in patient_tests):
                filtered_patients.append(patient)
        # Serialize the filtered patients
        patient_data = [model_to_dict(patient) for patient in filtered_patients]
        return JsonResponse({'data': patient_data}, safe=False)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DDTHH:MM:SS.'}, status=400)

@api_view(['POST'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def sample_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            for entry in data:
                patient_id = entry['patient_id']
                patientname = entry['patientname']
                barcode = entry['barcode']
                age = entry['age']
                segment = entry['segment']
                date = entry.get('date', '')
                testdetails = entry.get('testdetails', [])
                # Check if an entry with the same date, patient_id, patientname, and testdetails exists
                existing_entry = SampleStatus.objects.filter(
                    patient_id=patient_id,
                    patientname=patientname,
                    barcode=barcode,
                    age=age,
                    segment=segment,
                    date=date,
                    testdetails=testdetails
                ).first()
                if existing_entry:
                    return JsonResponse({'message': 'Data already exists'}, status=409)
                # If no existing entry, save the new one
                patient = SampleStatus(
                    patient_id=patient_id,
                    patientname=patientname,
                    barcode=barcode,
                    age=age,
                    segment=segment,
                    date=date,
                    testdetails=testdetails
                )
                patient.save()
            return JsonResponse({'message': 'Data saved successfully'}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['PUT'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def update_sample_status(request, patient_id):
    password = quote_plus('Smrft@2024')
    # MongoDB connection with TLS certificate
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
    db = client.Lab  # Database name
    collection = db.labbackend_samplestatus
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)  # Parse the incoming JSON data
            updates = data  # Use updates array directly
            # Find all patients with the given patient_id in MongoDB
            patients = collection.find({"patient_id": patient_id})
            if not patients:
                return JsonResponse({'error': 'No patients found with the given patient_id'}, status=404)
            update_count = 0
            for patient in patients:
                if isinstance(patient.get('testdetails'), str):
                    try:
                        patient['testdetails'] = json.loads(patient['testdetails'])  # Parse JSON string to list
                    except json.JSONDecodeError:
                        return JsonResponse({'error': 'Invalid test details format'}, status=400)
                updated_testdetails = []
                test_found = False  # Flag to check if the test is found
                for entry in patient['testdetails']:
                    if isinstance(entry, dict) and entry.get('testname') in [update['testname'] for update in updates]:
                        for update in updates:
                            if entry['testname'] == update['testname']:
                                entry['samplestatus'] = update['samplestatus']
                                entry['collectd_by'] = update['collectd_by']
                                # Store collected time in IST with the desired format
                                ist_time = timezone.now().astimezone(timezone.get_current_timezone())
                                # Format the timestamp to the desired format (e.g., '2025-02-14 15:23:45')
                                formatted_time = ist_time.strftime('%Y-%m-%d %H:%M:%S')  # Use the same format as your first example
                                if update['samplestatus'] == "Sample Collected":
                                    entry['samplecollected_time'] = formatted_time
                                test_found = True
                        updated_testdetails.append(entry)
                if not test_found:
                    continue  # Skip if no test found
                # Update the testdetails array in MongoDB
                result = collection.update_one(
                    {"_id": patient['_id']},
                    {"$set": {"testdetails": json.dumps(updated_testdetails)}}
                )
                if result.modified_count > 0:
                    update_count += 1
            if update_count > 0:
                return JsonResponse({'message': f'Successfully updated sample status for {update_count} patients.'}, status=200)
            else:
                return JsonResponse({'error': 'No updates were made'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@api_view(['GET'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_sample_collected(request):
    if request.method == "GET":
        try:
            # Fetch all sample statuses
            samples = SampleStatus.objects.all()
            patient_data = {}
            # Prepare the data grouped by patient
            for sample in samples:
                # Deserialize testdetails if it's a string
                if isinstance(sample.testdetails, str):
                    test_details = json.loads(sample.testdetails)
                else:
                    test_details = sample.testdetails
                # Filter test details based on samplestatus only
                for detail in test_details:
                    if detail.get("samplestatus") == "Sample Collected":
                        # If patient is not already in the dictionary, add them
                        if sample.patient_id not in patient_data:
                            patient_data[sample.patient_id] = {
                                "date":sample.date,
                                "patient_id": sample.patient_id,
                                "patientname": sample.patientname,
                                "barcode": sample.barcode,
                                "age": sample.age,
                                "segment": sample.segment,
                                "testdetails": []
                            }
                        # Append the test details
                        patient_data[sample.patient_id]["testdetails"].append({
                            "testname": detail.get("testname", "N/A"),
                            "container": detail.get("container", "N/A"),
                            "department": detail.get("department", "N/A"),
                            "samplecollector": detail.get("samplecollector", "N/A"),
                            "samplestatus": detail.get("samplestatus", "N/A"),
                            "samplecollected_time": detail.get("samplecollected_time", "N/A"),
                        })
            # Convert the dictionary to a list
            data = list(patient_data.values())
            # Return the filtered data as a response
            return JsonResponse({"data": data}, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        

@api_view(['PUT'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def update_sample_collected(request, patient_id):
    # MongoDB connection setup
    #password = quote_plus('Smrft@2024')
    # MongoDB connection with TLS certificate
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
    db = client.Lab  # Database name
    collection = db.labbackend_samplestatus  # Collection name
    if request.method == "PUT":
        try:
            body = json.loads(request.body)
            updates = body.get("updates", [])
            if not updates:
                return JsonResponse({"error": "Updates are required"}, status=400)
            # Find the patient sample record
            patient_sample = collection.find_one({"patient_id": patient_id})
            if not patient_sample:
                return JsonResponse({"error": "Sample not found"}, status=404)
            # Parse testdetails as a Python list
            testdetails = json.loads(patient_sample.get('testdetails', '[]'))
            # Apply updates based on testIndex
            
            # Import the proper Django timezone module
            from django.utils import timezone
            import pytz
            
            # Configure IST timezone
            ist_timezone = pytz.timezone('Asia/Kolkata')
            
            for update in updates:
                testIndex = update.get("testIndex")
                new_status = update.get("samplestatus")
                received_by = update.get("received_by")
                rejected_by = update.get("rejected_by")
                outsourced_by = update.get("outsourced_by")  # Fixed typo in variable name
                remarks = update.get("remarks")  # New field for rejection remarks
                if testIndex is None or new_status is None:
                    return JsonResponse({"error": "samplestatus and testIndex are required"}, status=400)
                # Ensure testIndex is valid
                if testIndex < 0 or testIndex >= len(testdetails):
                    return JsonResponse({"error": "Invalid testIndex"}, status=400)
                test_entry = testdetails[testIndex]
                # Update the sample status and associated fields
                test_entry['samplestatus'] = new_status
                
                # Get current time in IST timezone
                current_time = timezone.now().astimezone(ist_timezone)
                formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')  # Format the time
                
                if new_status == "Received":
                    test_entry['received_time'] = formatted_time
                    test_entry['received_by'] = received_by
                elif new_status == "Rejected":
                    test_entry['rejected_time'] = formatted_time
                    test_entry['rejected_by'] = rejected_by
                    test_entry['remarks'] = remarks  # Add rejection remarks
                elif new_status == "Outsource":
                    test_entry['outsourced_time'] = formatted_time  # Fixed typo in field name
                    test_entry['outsourced_by'] = outsourced_by  # Fixed typo in field name
            
            # Save changes back to the database
            collection.update_one(
                {"patient_id": patient_id},
                {"$set": {"testdetails": json.dumps(testdetails)}}  # Re-serialize testdetails as JSON
            )
            return JsonResponse({"message": "Sample status updated successfully"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@api_view(['GET'])       
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_received_samples(request):
    # Get patient_id and date from the query parameters
    patient_id = request.GET.get('patient_id')
    date_str = request.GET.get('date')

    if not patient_id or not date_str:
        return JsonResponse({'error': 'Missing patient_id or date parameter'}, status=400)

    try:
        # Fetch SampleStatus entries for the given patient_id
        received_samples = SampleStatus.objects.filter(patient_id=patient_id)

        test_data = []
        for sample in received_samples:
            # Check if testdetails is a string or a list
            if isinstance(sample.testdetails, str):
                try:
                    test_list = json.loads(sample.testdetails)  # Parse JSON string
                except json.JSONDecodeError:
                    return JsonResponse({'error': 'Invalid testdetails format'}, status=400)
            elif isinstance(sample.testdetails, list):
                test_list = sample.testdetails  # Use as-is
            else:
                continue  # Skip invalid testdetails format

            for test_item in test_list:
                testname = test_item.get('testname')
                samplestatus = test_item.get('samplestatus')

                # Only include tests with 'Received' status and matching date
                if samplestatus == 'Received' and str(sample.date) == date_str:
                    test_info = {
                        "patient_id": sample.patient_id,
                        "patientname": sample.patientname,
                        "testname": testname,
                        "samplestatus": samplestatus,
                        "date": sample.date,
                        "segment": sample.segment
                    }
                    test_data.append(test_info)

        return JsonResponse({'data': test_data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)       