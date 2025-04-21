from ..serializers import PatientSerializer
from rest_framework.response import Response
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework import  status
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.db.models import Max
from datetime import datetime
from django.forms.models import model_to_dict
import json
from ..models import Patient

from datetime import datetime, timedelta
@api_view(['POST'])
@csrf_exempt
def create_patient(request):
    if request.method == 'POST':
        serializer = PatientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET'])
def get_latest_patient_id(request):
    # Fetch the latest patient ID from the database
    latest_patient = Patient.objects.aggregate(Max('patient_id'))
    # If there's a patient ID, increment it, otherwise start with SD001
    if latest_patient['patient_id__max']:
        current_id = int(latest_patient['patient_id__max'].replace('SD', ''))
        new_patient_id = f"SD{str(current_id + 1).zfill(3)}"
    else:
        new_patient_id = "SD001"
    return Response({"patient_id": new_patient_id}, status=status.HTTP_200_OK)
@api_view(['GET'])
def get_latest_bill_no(request):
    today = datetime.now().strftime('%Y%m%d')  # Get today's date in YYYYMMDD format
    # Get the latest bill_no that starts with today's date
    last_bill = Patient.objects.filter(bill_no__startswith=today).aggregate(Max('bill_no'))
    if last_bill['bill_no__max']:
        # Extract the numeric part of the last bill number and increment it
        last_id = int(last_bill['bill_no__max'][-4:])  # Extract the last 4 digits
        next_id = last_id + 1
    else:
        # Start with 0001 if no bills exist for today
        next_id = 1
    # Generate the new bill number
    new_bill_no = f"{today}{next_id:04d}"  # Format: YYYYMMDD0001
    return Response({"bill_no": new_bill_no}, status=status.HTTP_200_OK)


@api_view(['GET'])
@csrf_exempt
def get_all_patients(request):
    # Retrieve patients where segment is "B2B"
    patients = Patient.objects.filter(segment="B2B")

    serializer = PatientSerializer(patients, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_patients(request):
    """Fetch patients registered on a given date"""
    date_str = request.GET.get('date', None)  # Get date from request parameters
    if not date_str:
        return Response({"error": "Date parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()  # Convert to date object
        # Filter using range to get all records for the selected date
        next_day = selected_date + timedelta(days=1)
        patients = Patient.objects.filter(date__gte=selected_date, date__lt=next_day)
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except ValueError:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
def get_patient_details(request):
    patient_id = request.GET.get('patient_id')
    phone = request.GET.get('phone')
    patientname = request.GET.get('patientname')

    try:
        patient = None

        # Check for patient_id
        if patient_id:
            patient = Patient.objects.filter(patient_id=patient_id).first()
        # Check for phone
        elif phone:
            patient = Patient.objects.filter(phone=phone).first()
        # Check for patientname (case-insensitive, partial match)
        elif patientname:
            patient = Patient.objects.filter(patientname__icontains=patientname).first()
        else:
            return JsonResponse({'error': 'Please provide either patient_id, phone, or patientname'}, status=400)

        # If patient is found, return patient data
        if patient:
            patient_data = {
                'patient_id': patient.patient_id,
                'patientname': patient.patientname,
                'age': patient.age,
                'gender': patient.gender,
                'phone': patient.phone,
                'address': patient.address,
                'email': patient.email,
                'bill_no':patient.bill_no,
            }
            return JsonResponse(patient_data)
        else:
            return JsonResponse({'error': 'Patient not found'}, status=404)
   
    except Exception as e:
        return JsonResponse({'error': f'Error fetching patient details: {str(e)}'}, status=500)
    



def get_patients_by_date(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date and end_date:
        try:
            # Convert string to datetime
            start_date_parsed = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_parsed = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)  # Include the entire end date

            # Adjust filter based on field type
            patients = Patient.objects.filter(date__gte=start_date_parsed, date__lte=end_date_parsed)
            
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

    return JsonResponse({'error': 'Both start_date and end_date parameters are required.'}, status=400)


@api_view(['GET'])
def patient_overview(request):
    patients = Patient.objects.all()
    serializer = PatientSerializer(patients, many=True)  # Serialize the queryset
    return Response(serializer.data)



@csrf_exempt
def get_patient_by_id(request, patient_id):
    """
    API endpoint to fetch patient details based on patient ID.
    """
    if request.method == 'GET':
        try:
            # Fetch the patient using Django ORM
            patient = Patient.objects.get(patient_id=patient_id)
            # Convert the patient object to a dictionary
            patient_data = {
                "patient_id": patient.patient_id,
                "patientname": patient.patientname,
                "phone": patient.phone,
                "gender": patient.gender,
                "email": patient.email,
                "address": patient.address,
                "age": patient.age,
                "age_type": patient.age_type,
                "sample_collector": patient.sample_collector,
                "salesMapping": patient.salesMapping,
                "date": patient.date.strftime('%Y-%m-%d'),  # Format date as string
                "discount": patient.discount,
                "lab_id": patient.lab_id,
                "refby": patient.refby,
                "branch": patient.branch,
                "B2B": patient.B2B,
                "segment": patient.segment,
                "testname": patient.testname,
                "totalAmount": patient.totalAmount,
                "payment_method": patient.payment_method,
                "registeredby": patient.registeredby,
                "bill_no": patient.bill_no,
                "PartialPayment": patient.PartialPayment,
            }
            return JsonResponse(patient_data, safe=False)
        except Patient.DoesNotExist:
            return JsonResponse({"error": "Patient not found"}, status=404)
    return JsonResponse({"error": "Invalid HTTP method"}, status=405)
