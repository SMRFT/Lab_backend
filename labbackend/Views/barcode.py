from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework import  status
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.forms.models import model_to_dict
from django.db.models import Max
from ..models import BarcodeTestDetails,Patient
import logging
import json
#auth
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from pyauth.auth import HasRoleAndDataPermission


@api_view(['GET'])
@permission_classes([HasRoleAndDataPermission])
def get_existing_barcode(request):
    patient_id = request.GET.get('patient_id')
    date = request.GET.get('date')
    bill_no = request.GET.get('bill_no')

    if not patient_id and not bill_no:
        return JsonResponse({'error': 'Either Patient ID or Bill No is required.'}, status=400)

    try:
        parsed_date = datetime.strptime(date, '%Y-%m-%d').date() if date else None
        query_filter = {}

        if patient_id:
            query_filter['patient_id'] = patient_id
        if bill_no:
            query_filter['bill_no'] = bill_no
        if parsed_date:
            query_filter['date'] = parsed_date

        barcode_record = BarcodeTestDetails.objects.filter(**query_filter).first()

        if barcode_record:
            return JsonResponse({
                'patient_id': barcode_record.patient_id,
                'patientname': barcode_record.patientname,
                'age': barcode_record.age,
                'gender': barcode_record.gender,
                'date': barcode_record.date,
                'bill_no': barcode_record.bill_no,
                'tests': barcode_record.tests,  # Ensure tests are serialized correctly
                'barcode': barcode_record.barcode
            }, status=200)

        return JsonResponse({'message': 'No barcode found for the given details.'}, status=404)

    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)


logger = logging.getLogger(__name__)
@api_view(['GET'])
@permission_classes([HasRoleAndDataPermission])
def get_max_barcode(request):
    try:
        max_barcode = 0  # Initialize the maximum barcode value
        # Retrieve all 'tests' fields from the database
        all_tests = BarcodeTestDetails.objects.values_list('tests', flat=True)
        for tests in all_tests:
            try:
                # Parse the tests JSON string if needed
                if isinstance(tests, str):  
                    tests = eval(tests)  # Convert string representation to a list of dicts (use json.loads if stored as JSON)

                if isinstance(tests, list):  # Ensure it's a list of test dictionaries
                    for test in tests:
                        barcode = test.get("barcode", "")
                        if barcode:
                            # Extract numeric part from the barcode
                            numeric_part = ''.join(filter(str.isdigit, barcode))
                            if numeric_part.isdigit():
                                numeric_value = int(numeric_part)
                                max_barcode = max(max_barcode, numeric_value)
            except Exception as inner_exception:
                logger.warning(f"Error processing tests: {inner_exception}")
                continue

        # Increment the max barcode value by 1
        next_barcode = max_barcode + 1

        # Format as a zero-padded 6-digit string
        formatted_next_barcode = f"{next_barcode:06d}"
        logger.debug(f"Next barcode generated: {formatted_next_barcode}")
        return JsonResponse({'next_barcode': formatted_next_barcode}, status=200)

    except Exception as e:
        logger.error(f"Error in get_max_barcode: {e}")
        return JsonResponse({'error': 'Failed to generate barcode'}, status=500)
    

@api_view(["POST"])
@csrf_exempt
@permission_classes([HasRoleAndDataPermission])
def save_barcodes(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            bill_no = data.get('bill_no')

            # Check if bill_no already exists
            if BarcodeTestDetails.objects.filter(bill_no=bill_no).exists():
                return JsonResponse({'error': 'Bill number already exists!'}, status=400)

            patient_id = data.get('patient_id')
            patientname = data.get('patientname')
            age = data.get('age')
            gender = data.get('gender')
            segment = data.get('segment')
            sample_collector = data.get('sample_collector')
            barcode = data.get('barcode')
            date = data.get('date')  # Date as a string
            tests = data.get('tests')

            # Convert string to date object if needed
            if date:
                date = datetime.strptime(date, "%d/%m/%Y").date()  # Match format 'DD/MM/YYYY'

            # Save patient details
            BarcodeTestDetails.objects.create(
                patient_id=patient_id,
                patientname=patientname,
                age=age,
                gender=gender,
                date=date,
                segment=segment,
                sample_collector=sample_collector,
                barcode=barcode,
                bill_no=bill_no,
                tests=tests,
            )
            return JsonResponse({'message': 'Barcodes saved successfully!'}, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
        
@api_view(["GET"])
@permission_classes([HasRoleAndDataPermission])
def get_barcode_by_date(request):
    date = request.GET.get('date')  # Expecting 'YYYY-MM-DD'
    if date:
        try:
            parsed_date = datetime.strptime(date, '%Y-%m-%d')  # Parse the provided date
            start_of_day = datetime.combine(parsed_date, datetime.min.time())  # 2025-01-23 00:00:00
            end_of_day = datetime.combine(parsed_date, datetime.max.time())  # 2025-01-23 23:59:59.999999
           
            # Query patients with a range filter
            patients = Patient.objects.filter(date__gte=start_of_day, date__lte=end_of_day)
           
            # Process each patient to filter out refunded or cancelled tests
            patient_data = []
            for patient in patients:
                patient_dict = model_to_dict(patient)
                
                # Handle testname which could be a string or already a list
                tests = patient.testname
                
                # If tests is a string, parse it as JSON
                if isinstance(tests, str):
                    try:
                        tests = json.loads(tests)
                    except json.JSONDecodeError:
                        # Skip patients with invalid JSON in testname
                        continue
                
                # Filter out tests that are refunded or cancelled
                valid_tests = []
                for test in tests:
                    # Check if refund or cancellation keys exist and are True
                    if not test.get('refund', False) and not test.get('cancellation', False):
                        valid_tests.append(test)
                
                # If no valid tests remain after filtering, skip this patient entirely
                if not valid_tests:
                    continue
                
                # Replace the testname with filtered valid tests
                patient_dict['testname'] = valid_tests
                
                # Recalculate total amount based on valid tests only
                total_amount = sum(float(test.get('amount', 0)) for test in valid_tests)
                patient_dict['totalAmount'] = str(total_amount)
                
                patient_data.append(patient_dict)
            
            # Return the filtered patient data
            return JsonResponse({'data': patient_data}, safe=False)
            
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    return JsonResponse({'error': 'Date parameter is required.'}, status=400)


@api_view(["GET"])
@permission_classes([HasRoleAndDataPermission])
def check_barcode(request):
    patient_id = request.GET.get('patient_id')
    date = request.GET.get('date')
    if BarcodeTestDetails.objects.filter(patient_id=patient_id, date=date).exists():
        return JsonResponse({"exists": True})
    return JsonResponse({"exists": False})