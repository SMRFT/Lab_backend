from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework import viewsets, status
from datetime import datetime, timedelta
from django.db.models import Max
from urllib.parse import quote_plus
from pymongo import MongoClient
from django.views.decorators.http import require_GET
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
import json

from .serializers import RegisterSerializer

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from .models import Register
from .serializers import RegisterSerializer

from .serializers import RegisterSerializer


from .serializers import RegisterSerializer
@api_view(['GET', 'POST', 'PUT'])
@csrf_exempt
def registration(request):
    if request.method == 'POST':
        # Handle Registration
        name = request.data.get('name')
        role = request.data.get('role')
        password = request.data.get('password')
        confirm_password = request.data.get('confirmPassword')
        if password != confirm_password:
            return Response({"error": "Passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)
        if Register.objects.filter(name=name, role=role).exists():
            return Response({"error": "User with this name and role already exists"}, status=status.HTTP_400_BAD_REQUEST)
        Register.objects.create(name=name, role=role, password=password)
        return Response({"message": "Registration successful!"}, status=status.HTTP_201_CREATED)
    
    elif request.method == 'PUT':
        name = request.data.get('name')
        role = request.data.get('role')
        old_password = request.data.get('oldPassword')
        new_password = request.data.get('password')
        confirm_password = request.data.get('confirmPassword')
        
        if new_password != confirm_password:
            return Response({"error": "New passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            password = quote_plus('Smrft@2024')
            client = MongoClient(
                f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
                tls=True,
                tlsCAFile=certifi.where()
            )
            db = client.Lab
            collection = db['labbackend_register']
            
            # Find the user
            user = collection.find_one({"name": name, "role": role})

            if not user:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Verify old password
            if user.get('password') != old_password:
                return Response({"error": "Incorrect current password"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Update password
            result = collection.update_one(
                {"name": name, "role": role},
                {"$set": {"password": new_password}}
            )

            if result.matched_count == 0:
                return Response({"error": "No matching user found"}, status=status.HTTP_404_NOT_FOUND)

            if result.modified_count == 1:
                return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Password update failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({"error": f"Database error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if 'client' in locals():
                client.close()

    elif request.method == 'GET':
        # Handle fetching users with the role "Sales Person"
        sales_persons = Register.objects.filter(role='Sales Person')
        serializer = RegisterSerializer(sales_persons, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

   

from .models import Register
@api_view(['POST'])
def login(request):
    name = request.data.get('name')
    password = request.data.get('password')
    try:
        user = Register.objects.get(name=name)
        if user.password == password:
            return Response({
                "message": f"Login successful as {user.role}, {user.name}",
                "role": user.role,
                "name": user.name
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED)
    except Register.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
   

from .serializers import PatientSerializer
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


from datetime import datetime
from django.http import JsonResponse
from .models import BarcodeTestDetails

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






import logging
from django.http import JsonResponse
from .models import BarcodeTestDetails  # Replace with your actual model import

logger = logging.getLogger(__name__)

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






   

from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import BarcodeTestDetails

@csrf_exempt
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

   

from .serializers import PatientSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from .models import Patient  # Ensure you import the Patient model

@api_view(['GET'])
@csrf_exempt
def get_all_patients(request):
    # Retrieve patients where segment is "B2B"
    patients = Patient.objects.filter(segment="B2B")

    serializer = PatientSerializer(patients, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)



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
   

from django.http import JsonResponse
from .models import Patient
from django.forms.models import model_to_dict
from datetime import datetime, timedelta

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

            # Convert queryset to JSON
            patient_data = [model_to_dict(patient) for patient in patients]
            return JsonResponse({'data': patient_data}, safe=False)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

    return JsonResponse({'error': 'Both start_date and end_date parameters are required.'}, status=400)




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

from collections import defaultdict
def convert_to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

from collections import defaultdict
import json
from datetime import datetime, timedelta
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
def convert_to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
@api_view(['GET'])
def patient_report(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    if not start_date_str or not end_date_str:
        return JsonResponse({"error": "Start date and end date are required"}, status=400)
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)  # Include full end date
    except ValueError:
        return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
    # MongoDB Connection Setup
    password = quote_plus('Smrft@2024')
    client = MongoClient(
        f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
        tls=True,
        tlsCAFile=certifi.where()
    )
    db = client.Lab
    patients_collection = db["labbackend_patient"]  # MongoDB collection
    # Query MongoDB directly
    patients = patients_collection.find({
        "date": {"$gte": start_date, "$lt": end_date}
    })
    # Check if there are any patients
    patient_count = patients_collection.count_documents({
        "date": {"$gte": start_date, "$lt": end_date}
    })
    if patient_count == 0:
        return JsonResponse({'message': "No data available for the selected date range.", 'report': []})
    # Dictionary to group data by date
    report_by_date = defaultdict(lambda: {
        'gross_amount': 0,
        'discount': 0,
        'due_amount': 0,
        'net_amount': 0,
        'pending_amount': 0,
        'total_collection': 0,
        'credit_payment_received': 0,  # Track credit payments received
        'payment_totals': {'Cash': 0, 'UPI': 0, 'Neft': 0, 'Cheque': 0, 'Credit': 0, 'PartialPayment': 0}
    })
    # Process each patient's data
    for patient in patients:
        date_key = patient['date'].strftime("%Y-%m-%d")  # Convert date to string for JSON response
        gross_amount = convert_to_float(patient.get('totalAmount', 0))
        discount = convert_to_float(patient.get('discount', 0))
        # Process PartialPayment - Handle it as a possible JSON string
        partial_payment = patient.get('PartialPayment', '')
        partial_payment_dict = {}
        if isinstance(partial_payment, str):
            # Remove any extra quotes if it's a JSON string within a string (like "\"\"")
            partial_payment = partial_payment.strip('"\'')
            if partial_payment:
                try:
                    partial_payment_dict = json.loads(partial_payment)
                except json.JSONDecodeError:
                    partial_payment_dict = {}
        elif isinstance(partial_payment, dict):
            partial_payment_dict = partial_payment
        # Get due amount from PartialPayment
        due_amount = 0
        if isinstance(partial_payment_dict, dict):
            due_amount = convert_to_float(partial_payment_dict.get('credit', 0))
        # Process credit_details - this is for payments against previous credits
        credit_details = patient.get('credit_details', '')
        credit_details_list = []
        if isinstance(credit_details, str) and credit_details.strip():
            try:
                credit_details_list = json.loads(credit_details)
            except json.JSONDecodeError:
                credit_details_list = []
        elif isinstance(credit_details, list):
            credit_details_list = credit_details
        # Process each credit payment entry
        if isinstance(credit_details_list, list):
            for payment in credit_details_list:
                payment_date_str = payment.get('paid_date')
                if payment_date_str:
                    try:
                        payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()
                        # If payment date falls within report range, add to the appropriate date
                        if start_date.date() <= payment_date < end_date.date():
                            payment_date_key = payment_date.strftime("%Y-%m-%d")
                            amount_paid = convert_to_float(payment.get('amount_paid', 0))
                            payment_method = payment.get('payment_method')
                            # Add to credit payment received for that day
                            report_by_date[payment_date_key]['credit_payment_received'] += amount_paid
                            # Add to payment method totals
                            if payment_method in report_by_date[payment_date_key]['payment_totals']:
                                report_by_date[payment_date_key]['payment_totals'][payment_method] += amount_paid
                    except ValueError:
                        # Invalid date format, skip this payment
                        continue
        # Update values for the date
        report_by_date[date_key]['gross_amount'] += gross_amount
        report_by_date[date_key]['discount'] += discount
        report_by_date[date_key]['due_amount'] += due_amount
        # Process payment method totals from main payment
        payment_method = patient.get('payment_method', '')
        payment_method_dict = {}
        if isinstance(payment_method, str) and payment_method.strip():
            try:
                payment_method_dict = json.loads(payment_method)
            except json.JSONDecodeError:
                payment_method_dict = {}
        elif isinstance(payment_method, dict):
            payment_method_dict = payment_method
        if isinstance(payment_method_dict, dict):
            method = payment_method_dict.get('paymentmethod')
            if method in report_by_date[date_key]['payment_totals']:
                # Only add to payment totals if it's not a credit transaction
                if method != 'Credit':
                    report_by_date[date_key]['payment_totals'][method] += gross_amount
                else:
                    # If it's credit, add to the Credit payment method total
                    report_by_date[date_key]['payment_totals']['Credit'] += gross_amount
    # Convert to list format
    report_list = []
    for date, data in sorted(report_by_date.items()):
        # Calculate net amount (gross - discount - due)
        net_amount = data['gross_amount'] - (data['discount'] + data['due_amount'])
        # Total collection includes direct payments plus credit payments received
        total_collection = net_amount + data['credit_payment_received']
        report_list.append({
            'date': date,
            'gross_amount': round(data['gross_amount'], 2),
            'discount': round(data['discount'], 2),
            'due_amount': round(data['due_amount'], 2),
            'credit_payment_received': round(data['credit_payment_received'], 2),
            'net_amount': round(net_amount, 2),
            'total_collection': round(total_collection, 2),
            'payment_totals': {key: round(value, 2) for key, value in data['payment_totals'].items()},
        })
    client.close()  # Close MongoDB connection
    return Response({'report': report_list})




from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import json
import certifi
from urllib.parse import quote_plus
@csrf_exempt  # Allow GET, POST, and PATCH requests without CSRF protection
def get_test_details(request):
    try:
        # Securely encode password
        password = quote_plus('Smrft@2024')
        # MongoDB connection with TLS certificate
        client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )
        db = client.Lab  # Database name
        collection = db.labbackend_testdetails  # Collection name
        if request.method == 'GET':
            # Retrieve all documents in Testdetails collection
            test_details = list(collection.find({}, {'_id': 0}))  # Exclude MongoDB's default _id field
            return JsonResponse(test_details, safe=False, status=200)
        elif request.method == 'POST':
            try:
                data = json.loads(request.body.decode('utf-8'))
                if 'parameters' in data and isinstance(data['parameters'], list):
                    if not all(isinstance(param, dict) for param in data['parameters']):
                        return JsonResponse({'error': 'Invalid format for parameters: all elements must be dictionaries'}, status=400)
                    data['parameters'] = json.dumps(data['parameters'])
                else:
                    return JsonResponse({'error': 'Parameters should be a JSON array of dictionaries'}, status=400)
                # Insert data into MongoDB
                collection.insert_one(data)
                return JsonResponse({'message': 'Test details added successfully'}, status=201)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON data'}, status=400)
            except Exception as e:
                print("Error:", e)
                return JsonResponse({'error': 'An error occurred while saving data'}, status=500)
        elif request.method == 'PATCH':
            try:
                data = json.loads(request.body.decode('utf-8'))
                test_name = data.get('test_name')
                updated_parameters = data.get('parameters')
                if not test_name or updated_parameters is None:
                    return JsonResponse({'error': 'test_name and parameters are required'}, status=400)
                updated_parameters_json = json.dumps(updated_parameters)
                result = collection.update_one(
                    {'test_name': test_name},
                    {'$set': {'parameters': updated_parameters_json}}
                )
                if result.matched_count > 0:
                    return JsonResponse({'message': 'Parameters updated successfully'}, status=200)
                else:
                    return JsonResponse({'error': 'Test not found'}, status=404)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print("Error:", e)
        return JsonResponse({'error': 'An error occurred'}, status=500)


@csrf_exempt
def handle_patch_request(request):
    try:
        # MongoDB connection setup inside the function
        password = quote_plus('Smrft@2024')
        # MongoDB connection with TLS certificate
        client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )
        db = client.Lab  # Database name
        collection = db.labbackend_testdetails  # Collection name
        data = json.loads(request.body.decode('utf-8'))
        test_name = data.get('test_name')
        if not test_name:
            return JsonResponse({'error': 'test_name is required'}, status=400)
        # Update fields, excluding 'test_name'
        update_fields = {k: v for k, v in data.items() if k != 'test_name'}
        if update_fields:
            result = collection.update_one({'test_name': test_name}, {'$set': update_fields})
            if result.matched_count > 0:
                return JsonResponse({'message': 'Test details updated successfully'}, status=200)
            else:
                return JsonResponse({'error': 'Test not found'}, status=404)
        return JsonResponse({'message': 'No updates provided'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print("Error:", e)
        return JsonResponse({'error': 'An error occurred while updating data'}, status=500)


@csrf_exempt
def get_test_parameters(request, test_name):
    try:
        # MongoDB connection setup
        password = quote_plus('Smrft@2024')

        # MongoDB connection with TLS certificate
        client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )

        db = client.Lab  # Database name
        collection = db.labbackend_testdetails
        # Fetch the test details based on the test_name
        test = collection.find_one({"test_name": test_name}, {"_id": 0, "parameters": 1})  # Assuming parameters is a field in your document
        if test:
            return JsonResponse({"parameters": test.get("parameters", [])}, status=200)
        else:
            return JsonResponse({"error": "Test not found"}, status=404)
    except Exception as e:
        print("Error fetching parameters:", e)
        return JsonResponse({"error": "Failed to fetch parameters"}, status=500)


from .models import SampleCollector
from .serializers import SampleCollectorSerializer
@api_view(['GET', 'POST'])
def sample_collector(request):
    if request.method == 'POST':
        serializer = SampleCollectorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'GET':
        collectors = SampleCollector.objects.all()
        serializer = SampleCollectorSerializer(collectors, many=True)
        return Response(serializer.data)


# from .models import ClinicalName
# from .serializers import ClinicalNameSerializer
# @api_view(['GET', 'POST'])
# def clinical_name(request):
#     if request.method == 'POST':
#         serializer = ClinicalNameSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#     elif request.method == 'GET':
#         organisations = ClinicalName.objects.all()
#         serializer = ClinicalNameSerializer(organisations, many=True)
#         return Response(serializer.data)
   
# def get_last_referrer_code(request):
#     last_clinical = ClinicalName.objects.order_by('-referrerCode').first()
#     if last_clinical:
#         return JsonResponse({'referrerCode': last_clinical.referrerCode})
#     return JsonResponse({'referrerCode': 'SD0000'})
   

from .models import RefBy
from .serializers import RefBySerializer
@api_view(['GET', 'POST'])
def refby(request):
    if request.method == 'POST':
        serializer = RefBySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'GET':
        collectors = RefBy.objects.all()
        serializer = RefBySerializer(collectors, many=True)
        return Response(serializer.data)


from .models import Patient
def compare_test_details(request):
    # MongoDB connection setup
    password = quote_plus('Smrft@2024')
        # MongoDB connection with TLS certificate
    client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )
    db = client.Lab  # Database name
    collection = db.labbackend_testdetails  # Collection name
    # Retrieve the date and patient ID from the request
    date = request.GET.get('date')
    patient_id = request.GET.get('patient_id')
    if not date or not patient_id:
        return JsonResponse({'error': 'Date and patient_id parameters are required'}, status=400)
    try:
        # Validate the date format
        formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Expected YYYY-MM-DD.'}, status=400)
    # Query SampleStatus for patients with status 'Received' and matching patient_id
    received_samples = SampleStatus.objects.filter(
        patient_id=patient_id,
        testdetails__isnull=False
    )
    test_data = []
    for sample in received_samples:
        try:
            # Check if testdetails is a string or list
            if isinstance(sample.testdetails, str):
                test_list = json.loads(sample.testdetails)  # Parse JSON string
            elif isinstance(sample.testdetails, list):
                test_list = sample.testdetails  # Already a list
            else:
                return JsonResponse({'error': 'Invalid testdetails format'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid testdetails format'}, status=400)
        for test_item in test_list:
            testname = test_item.get('testname')
            samplestatus = test_item.get('samplestatus')
            # Only process if the sample status is 'Received'
            if samplestatus == "Received":
                # Fetch test details directly from MongoDB Testdetails collection
                test_details = collection.find({"test_name": testname})
                for test_detail in test_details:
                    # Extract parameters as JSON from the test detail
                    parameters_json = test_detail.get('parameters')
                    # Parse the parameters JSON string into a Python object if it exists
                    if parameters_json:
                        try:
                            parameters = json.loads(parameters_json)
                        except json.JSONDecodeError:
                            return JsonResponse({'error': 'Invalid parameters JSON format'}, status=400)
                    else:
                        parameters = None  # Handle case where 'parameters' is missing or null
                    # Assuming you want to compare with a specific parameter
                    requested_parameter = request.GET.get('parameter')
                    if requested_parameter and parameters and requested_parameter not in parameters:
                        continue  # Skip if the requested parameter is not found
                    test_info = {
                        "patient_id": sample.patient_id,
                        "patientname": sample.patientname,
                        "testname": test_detail.get('test_name'),
                        "parameters": parameters,
                        "specimen_type": test_detail.get('specimen_type'),
                        "unit": test_detail.get('unit'),
                        "reference_range": test_detail.get('reference_range'),
                        "status": samplestatus,
                        "barcode": sample.barcode,
                        "method": test_detail.get('method', ''),  # Add method
                        "department": test_detail.get('department', '')  # Add department
                    }
                    test_data.append(test_info)  # Append each test detail to test_data
    # Return all collected test details in the response
    return JsonResponse({'data': test_data})








from .models import SampleStatus
from .serializers import SampleStatusSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import json

@api_view(['GET'])
def get_samplestatus_testvalue(request):
    try:
        # Get the date from the query parameter
        date_str = request.query_params.get('date', None)
        # Ensure the date is provided
        if not date_str:
            return Response({"error": "Date parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        # Convert the date string to a datetime object
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        # Get the start and end of the selected date range (to compare the datetime portion)
        start_of_day = datetime.combine(selected_date, datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)
        # Get all records from the SampleStatus table for the selected date
        sample_statuses = SampleStatus.objects.filter(date__gte=start_of_day, date__lt=end_of_day)
        filtered_sample_statuses = []
        # Iterate through each record to filter the testdetails array
        for sample_status in sample_statuses:
            # Parse testdetails if it's a string
            try:
                testdetails = json.loads(sample_status.testdetails) if isinstance(sample_status.testdetails, str) else sample_status.testdetails
            except json.JSONDecodeError:
                # If testdetails cannot be parsed, skip this record
                continue
            # Filter tests with samplestatus 'Received' or 'Outsource'
            filtered_tests = [
                test for test in testdetails
                if test.get('samplestatus') in ['Received', 'Outsource']
            ]
            if filtered_tests:
                # If matching tests are found, add the whole record to the filtered list
                sample_status_dict = sample_status.__dict__.copy()  # Make a copy of the sample_status dictionary
                sample_status_dict['testdetails'] = filtered_tests
                filtered_sample_statuses.append(sample_status_dict)
        # Serialize the filtered data
        serializer = SampleStatusSerializer(filtered_sample_statuses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)









 

from .serializers import TestValueSerializer
from .models import Patient
@api_view(['GET', 'POST','PATCH'])
def save_test_value(request):
    if request.method == 'GET':
        patient_id = request.GET.get('patient_id')
        date = request.GET.get('date')
        testname = request.GET.get('testname')
        # Validate required parameters
        if not patient_id or not date or not testname:
            return Response({"error": "patient_id, date, and testname are required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Fetch the test value record for the patient and date
            test_value_record = TestValue.objects.get(patient_id=patient_id, date=date)
            test_details = test_value_record.testdetails
            # Find the specific test by testname
            test = next((t for t in test_details if t['testname'] == testname), None)
            if not test:
                return Response({"error": "Test not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(test, status=status.HTTP_200_OK)
        except TestValue.DoesNotExist:
            return Response({"error": "No test values found for the given patient and date"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    elif request.method == 'POST':
        payload = request.data
        try:
            patient = Patient.objects.get(patient_id=payload['patient_id'])
            test_details_json = payload.get("testdetails", [])
            barcode=payload.get("barcode")
            if not isinstance(test_details_json, list) or not test_details_json:
                return Response({"error": "Invalid test details format"}, status=status.HTTP_400_BAD_REQUEST)
            test_value_record, created = TestValue.objects.get_or_create(
                patient_id=patient.patient_id,
                date=payload.get('date'),
                defaults={
                    'patientname': patient.patientname,
                    'age': patient.age,
                    "barcode": barcode,
                    'testdetails': test_details_json,
                }
            )
            existing_test_details = test_value_record.testdetails if not created else []
            for test in test_details_json:
                testname = test.get('testname')
                if not testname:
                    return Response({"error": "Missing testname in test details"}, status=status.HTTP_400_BAD_REQUEST)
                existing_test = next((t for t in existing_test_details if t['testname'] == testname), None)
                if existing_test:
                    if 'parameters' in test and isinstance(test['parameters'], list):
                        if 'parameters' not in existing_test:
                            existing_test['parameters'] = []
                        for param in test['parameters']:
                            existing_param = next(
                                (p for p in existing_test['parameters'] if p['unit'] == param.get('unit')), None
                            )
                            if existing_param:
                                existing_param.update(param)
                            else:
                                existing_test['parameters'].append(param)
                    else:
                        existing_test['value'] = test.get('value', '')
                else:
                    existing_test_details.append(test)
            test_value_record.testdetails = existing_test_details
            test_value_record.save()
            return Response({"message": "Test details saved successfully."}, status=status.HTTP_200_OK)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print("Error in POST method:", str(e))  # Debugging
            return Response({"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    elif request.method == 'PATCH':
            # MongoDB connection
        password = quote_plus('Smrft@2024')
        # MongoDB connection with TLS certificate
        client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )
        db = client.Lab  # Database name
        collection = db.labbackend_testvalue
        # Extract parameters from the request
        patient_id = request.data.get("patient_id")
        date_str = request.data.get("date")  # Date as string
        test_details_json = request.data.get("testdetails", [])
        # Validate required fields
        if not patient_id or not date_str:
            return Response({"error": "patient_id and date are required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Convert the date string to a datetime object
            date = datetime.strptime(date_str, "%Y-%m-%d")
            # Find the existing document for the patient and date
            test_value_record = collection.find_one({"patient_id": patient_id, "date": date})
            if not test_value_record:
                return Response(
                    {"error": "No record found for the given patient and date"},
                    status=status.HTTP_404_NOT_FOUND
                )
            # Fetch and deserialize existing test details
            existing_test_details = test_value_record.get("testdetails", "[]")
            if isinstance(existing_test_details, str):
                existing_test_details = json.loads(existing_test_details)
            # Process new test details
            for new_test in test_details_json:
                testname = new_test["testname"]
                # Check if the test already exists in the existing test details
                existing_test = next((t for t in existing_test_details if t["testname"] == testname), None)
                if existing_test:
                    # Update the existing test details
                    if "parameters" in new_test and new_test["parameters"]:
                        for new_param in new_test["parameters"]:
                            param_name = new_param["name"]
                            existing_param = next(
                                (p for p in existing_test.get("parameters", []) if p["name"] == param_name), None
                            )
                            if existing_param:
                                existing_param["value"] = new_param["value"]  # Update existing parameter value
                            else:
                                existing_test.setdefault("parameters", []).append(new_param)  # Add new parameter
                    else:
                        # Update the value and other details for tests without parameters
                        existing_test["value"] = new_test.get("value", existing_test.get("value", ""))
                        existing_test["unit"] = new_test.get("unit", existing_test.get("unit", "N/A"))
                        existing_test["reference_range"] = new_test.get("reference_range", existing_test.get("reference_range", "N/A"))
                        existing_test["specimen_type"] = new_test.get("specimen_type", existing_test.get("specimen_type", "N/A"))
                else:
                    # Add the new test to the test details
                    existing_test_details.append(new_test)
            # Update the document in the database
            collection.update_one(
                {"patient_id": patient_id, "date": date},
                {"$set": {"testdetails": json.dumps(existing_test_details)}}  # Serialize back to string
            )
            return Response({"message": "Test details updated successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['PATCH'])
def update_test_value(request):
    # MongoDB connection
    password = quote_plus('Smrft@2024')
    # MongoDB connection with TLS certificate
    client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )
    db = client.Lab  # Database name
    collection = db.labbackend_testvalue
    try:
        payload = request.data
        patient_id = payload.get("patient_id")
        date_str = payload.get("date")  # date coming as string
        test_details = payload.get("testdetails", [])
        if not test_details:
            return Response(
                {"error": "Missing or empty 'testdetails' field."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return Response({"error": "Invalid date format. Expected 'YYYY-MM-DD'."}, status=status.HTTP_400_BAD_REQUEST)
        # Fetch the relevant TestValue entry from MongoDB
        test_entry = collection.find_one({"patient_id": patient_id, "date": date})
        if not test_entry:
            return Response(
                {"error": "Test entry not found for the given patient and date."},
                status=status.HTTP_404_NOT_FOUND
            )
        # Parse the testdetails field if it's a string
        test_entry_details = json.loads(test_entry["testdetails"]) if isinstance(test_entry["testdetails"], str) else test_entry["testdetails"]
        # Update specific test values and remarks in the testdetails field
        for updated_test in test_details:
            for existing_test in test_entry_details:
                if existing_test["testname"] == updated_test["testname"]:
                    existing_test["value"] = updated_test.get("value", existing_test["value"])
                    existing_test["remarks"] = updated_test.get("remarks", existing_test.get("remarks", ""))  # Update remarks field
                    if "rerun" in updated_test:
                        existing_test["rerun"] = updated_test["rerun"]  # Update rerun only if explicitly provided
                    break
        # Update the test details in MongoDB
        collection.update_one(
            {"_id": test_entry["_id"]},
            {"$set": {"testdetails": json.dumps(test_entry_details)}}
        )
        return Response(
            {"message": "Test values updated successfully."},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from datetime import datetime
import pytz
import json
from pymongo import MongoClient
import certifi
from urllib.parse import quote_plus
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# Define IST timezone
TIME_ZONE = 'Asia/Kolkata'
IST = pytz.timezone(TIME_ZONE)

@api_view(['PATCH'])
def update_dispatch_status(request, patient_id):
    # MongoDB connection
    password = quote_plus('Smrft@2024')

    # MongoDB connection with TLS certificate
    client = MongoClient(
        f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
        tls=True,  # Enable TLS/SSL
        tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
    )

    db = client.Lab  # Database name
    collection = db.labbackend_testvalue

    try:
        # Find the document for the given patient_id
        test_value_record = collection.find_one({"patient_id": patient_id})

        if not test_value_record:
            return Response({"error": "TestValue record not found"}, status=status.HTTP_404_NOT_FOUND)

        # Parse the testdetails field (convert JSON string to a Python list)
        test_details = json.loads(test_value_record.get("testdetails", "[]"))

        # Update dispatch status to true for all tests
        for test in test_details:
            test["dispatch"] = True
            # Only set dispatch_time if dispatch is True
            if test.get("dispatch", False):
                test["dispatch_time"] = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')  # Convert to IST format

        # Convert the updated testdetails back to a JSON string
        updated_test_details = json.dumps(test_details)

        # Update the document in MongoDB
        result = collection.update_one(
            {"patient_id": patient_id},  # Match the document
            {"$set": {"testdetails": updated_test_details}}  # Update the testdetails field
        )

        if result.matched_count == 0:
            return Response({"error": "Failed to update dispatch status"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Dispatch status updated successfully."}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from .models import  TestValue
@api_view(['GET'])
def get_test_report(request):
    day = request.GET.get('day')
    month = request.GET.get('month')
    queryset = TestValue.objects.all()

    # Filter based on day and month by constructing the date manually
    if day and month:
        queryset = [obj for obj in queryset if obj.date.day == int(day) and obj.date.month == int(month)]
    elif month:
        queryset = [obj for obj in queryset if obj.date.month == int(month)]

    report_data = [
        {
            "patient_id": obj.patient_id,
            "patientname": obj.patientname,
            "age": obj.age,
            "date": obj.date,
            "testdetails": obj.testdetails,
        }
        for obj in queryset
    ]
    return Response({"data": report_data})



def get_test_values(request):
    # Get date from request parameters
    date = request.GET.get('date')
    if date:
        try:
            # Ensure the date is in the correct format
            parsed_date = datetime.strptime(date, '%Y-%m-%d').date()  # This gets a date object
            # Filter patients by parsed date
            patients = TestValue.objects.filter(date=parsed_date)
            # Serialize patient details
            patient_data = [
                {
                    "patient_id": patient.patient_id,
                    "patientname": patient.patientname,
                    "age": patient.age,
                    "barcode": patient.barcode,
                    "date": patient.date,
                    "testdetails": patient.testdetails
                }
                for patient in patients
            ]
            return JsonResponse(patient_data, safe=False)
        except ValueError:
            # Handle date parsing error
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    else:
        # If no date is provided, return all test values ordered by date
        test_values = TestValue.objects.order_by('-date')
        # Serialize the test values into a list of dictionaries
        data = [
            {
                "patient_id": test.patient_id,
                "patientname": test.patientname,
                "barcode": test.barcode,
                "age": test.age,
                "date": test.date,
                "testdetails": test.testdetails
            }
            for test in test_values
        ]
        return JsonResponse(data, safe=False)


@api_view(['GET'])
def test_values(request):
    # Get the date parameter from the request
    date_str = request.GET.get('date')
    try:
        # Convert the date string to a Python date object
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        # Fetch the TestValue data for the given date
        test_values = TestValue.objects.filter(date=selected_date)
        # Serialize the data
        serializer = TestValueSerializer(test_values, many=True)
        # Return the serialized data in the response
        return Response(serializer.data)
    except ValueError:
        return Response({"error": "Invalid date format"}, status=400)


from django.utils import timezone  # Import Django's timezone module
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pymongo import MongoClient
import json
import certifi
from urllib.parse import quote_plus
@csrf_exempt
@require_http_methods(["PATCH"])
def approve_test_detail(request, patient_id, test_index):
    # MongoDB connection
    password = quote_plus('Smrft@2024')
    # MongoDB connection with TLS certificate
    client = MongoClient(
        f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
        tls=True,  # Enable TLS/SSL
        tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
    )
    db = client.Lab  # Database name
    collection = db.labbackend_testvalue  # Your collection name
    # Log the incoming request body
    # Check if the body is empty
    if not request.body:
        return JsonResponse({"error": "Empty request body."}, status=400)
    # Load the request data
    try:
        update_data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)
    # Find the test value document for the given patient_id
    test_value = collection.find_one({"patient_id": patient_id})
    # Check if the document exists
    if test_value is None:
        return JsonResponse({"error": "Patient not found."}, status=404)
    # Convert testdetails from string to list
    try:
        test_details = json.loads(test_value.get("testdetails", "[]"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Failed to decode test details."}, status=500)
    # Check for valid index
    if 0 <= test_index < len(test_details):
        # Update approve status based on request data
        if "approve" in update_data:
            test_details[test_index]["approve"] = update_data["approve"]
            # If approve is set to True, update approve_time with formatted timestamp
        if update_data["approve"]:
            # Get the timezone-aware current time
            approve_time = timezone.localtime(timezone.now())  # Convert to local timezone
            # Format the timestamp to the desired format (e.g., '2025-02-14 15:23:45')
            formatted_time = approve_time.strftime('%Y-%m-%d %H:%M:%S')  # Use the same format as your first example
            test_details[test_index]["approve_time"] = formatted_time
        # Update the document in the MongoDB collection
        result = collection.update_one(
            {"patient_id": patient_id},
            {"$set": {"testdetails": json.dumps(test_details)}}
        )
        # Check if the update was acknowledged
        if result.acknowledged:
            return JsonResponse({"message": "Test detail approved successfully."})
        else:
            return JsonResponse({"error": "Failed to update test detail."}, status=500)
    else:
        return JsonResponse({"error": "Invalid test index."}, status=400)
@csrf_exempt
@require_http_methods(["PATCH"])
def rerun_test_detail(request, patient_id, test_index):
    # MongoDB connection
    password = quote_plus('Smrft@2024')
        # MongoDB connection with TLS certificate
    client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )
    db = client.Lab  # Database name
    collection = db.labbackend_testvalue  # Your collection name
    """Rerun the test detail at the given index for the specified patient."""
    # Check if the request body is empty
    if not request.body:
        return JsonResponse({"error": "Empty request body."}, status=400)
    # Load the request data
    try:
        update_data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)
    # Find the test value document for the given patient_id
    test_value = collection.find_one({"patient_id": patient_id})
    # Check if the document exists
    if test_value is None:
        return JsonResponse({"error": "Patient not found."}, status=404)
    # Convert testdetails from string to list
    try:
        test_details = json.loads(test_value.get("testdetails", "[]"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Failed to decode test details."}, status=500)
    # Check for valid index
    if 0 <= test_index < len(test_details):
        # Update rerun status
        if "rerun" in update_data:
            test_details[test_index]["rerun"] = update_data["rerun"]
        # Update the document in the MongoDB collection
        result = collection.update_one(
            {"patient_id": patient_id},
            {"$set": {"testdetails": json.dumps(test_details)}}
        )
        # Check if the update was acknowledged
        if result.acknowledged:
            return JsonResponse({"message": "Test detail rerun status updated successfully."})
        else:
            return JsonResponse({"error": "Failed to update rerun status."}, status=500)
    else:
        return JsonResponse({"error": "Invalid test index."}, status=400)

@csrf_exempt
@api_view(['PATCH'])
def update_test_detail(request, patient_id):
    # MongoDB connection
    password = quote_plus('Smrft@2024')

        # MongoDB connection with TLS certificate
    client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )

    db = client.Lab  # Database name
    collection = db.labbackend_testvalue  # Your collection name
    """
    Update the value and rerun status of a specific test detail for a given patient in MongoDB.
    """
    try:
        # Find the document for the given patient_id
        test_value = collection.find_one({"patient_id": patient_id})

        if not test_value:
            return Response({'error': 'Patient data not found'}, status=status.HTTP_404_NOT_FOUND)

        # Extract test details and ensure it is in list form
        test_details = test_value.get("testdetails")
        if isinstance(test_details, str):  # If it's a JSON string, parse it into a list
            test_details = json.loads(test_details)

        # Extract data from the request
        testname = request.data.get('testname')
        new_value = request.data.get('value')

        # Find and update the specific test in the test details
        for detail in test_details:
            if detail['testname'] == testname:
                detail['value'] = new_value  # Update the value
                detail['rerun'] = False      # Set rerun to False
                break

        # Update the document in MongoDB with the modified test details as JSON
        collection.update_one(
            {"patient_id": patient_id},
            {"$set": {"testdetails": json.dumps(test_details)}}  # Encode as JSON string
        )

        return Response({'message': 'Test detail updated successfully'}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)



from django.http import JsonResponse
from .models import SampleStatus, BarcodeTestDetails
from django.forms.models import model_to_dict
import json
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







   
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import SampleStatus
@csrf_exempt
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








from django.utils import timezone  # Import Django's timezone module
from django.http import JsonResponse
from pymongo import MongoClient
import json
import certifi
from urllib.parse import quote_plus
from django.views.decorators.csrf import csrf_exempt

from django.utils import timezone  # Import Django's timezone module
from django.http import JsonResponse
from pymongo import MongoClient
import json
import certifi
from urllib.parse import quote_plus
from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
def update_sample_status(request, patient_id):
    password = quote_plus('Smrft@2024')
    # MongoDB connection with TLS certificate
    client = MongoClient(
        f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
        tls=True,  # Enable TLS/SSL
        tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
    )
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

@csrf_exempt
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

       
from datetime import datetime
from django.utils import timezone  # Import Django's timezone module
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import json
import certifi
from urllib.parse import quote_plus

from django.utils import timezone  # Import Django's timezone module
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import json
import certifi
from urllib.parse import quote_plus
@csrf_exempt
def update_sample_collected(request, patient_id):
    # MongoDB connection setup
    password = quote_plus('Smrft@2024')
    # MongoDB connection with TLS certificate
    client = MongoClient(
        f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
        tls=True,  # Enable TLS/SSL
        tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
    )
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
            for update in updates:
                testIndex = update.get("testIndex")
                new_status = update.get("samplestatus")
                received_by = update.get("received_by")
                rejected_by = update.get("rejected_by")
                outsourced_by = update.get("oursourced_by")
                remarks = update.get("remarks")  # New field for rejection remarks
                if testIndex is None or new_status is None:
                    return JsonResponse({"error": "samplestatus and testIndex are required"}, status=400)
                # Ensure testIndex is valid
                if testIndex < 0 or testIndex >= len(testdetails):
                    return JsonResponse({"error": "Invalid testIndex"}, status=400)
                test_entry = testdetails[testIndex]
                # Update the sample status and associated fields
                test_entry['samplestatus'] = new_status
                # Get current time in the correct timezone
                current_time = timezone.now().astimezone(timezone.get_current_timezone())
                formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')  # Format the time
                if new_status == "Received":
                    test_entry['received_time'] = formatted_time
                    test_entry['received_by'] = received_by
                elif new_status == "Rejected":
                    test_entry['rejected_time'] = formatted_time
                    test_entry['rejected_by'] = rejected_by
                    test_entry['remarks'] = remarks  # Add rejection remarks
                elif new_status == "Outsource":
                    test_entry['oursourced_time'] = formatted_time
                    test_entry['oursourced_by'] = outsourced_by
            # Save changes back to the database
            collection.update_one(
                {"patient_id": patient_id},
                {"$set": {"testdetails": json.dumps(testdetails)}}  # Re-serialize testdetails as JSON
            )
            return JsonResponse({"message": "Sample status updated successfully"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
def patient_overview(request):
    patients = Patient.objects.all()
    serializer = PatientSerializer(patients, many=True)  # Serialize the queryset
    return Response(serializer.data)



   
from .models import Patient  # Adjust the import based on your project structure
def get_barcode_by_date(request):
    date = request.GET.get('date')  # Expecting 'YYYY-MM-DD'
    if date:
        try:
            parsed_date = datetime.strptime(date, '%Y-%m-%d')  # Parse the provided date
            start_of_day = datetime.combine(parsed_date, datetime.min.time())  # 2025-01-23 00:00:00
            end_of_day = datetime.combine(parsed_date, datetime.max.time())  # 2025-01-23 23:59:59.999999
           
            # Query patients with a range filter
            patients = Patient.objects.filter(date__gte=start_of_day, date__lte=end_of_day)
           
            # Serialize the data
            patient_data = [model_to_dict(patient) for patient in patients]
            return JsonResponse({'data': patient_data}, safe=False)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    return JsonResponse({'error': 'Date parameter is required.'}, status=400)

from django.http import JsonResponse
from .models import BarcodeTestDetails
def check_barcode(request):
    patient_id = request.GET.get('patient_id')
    date = request.GET.get('date')
    if BarcodeTestDetails.objects.filter(patient_id=patient_id, date=date).exists():
        return JsonResponse({"exists": True})
    return JsonResponse({"exists": False})
def get_patient_test_details(request):
    patient_id = request.GET.get('patient_id')
    if not patient_id:
        return JsonResponse({'error': 'Patient ID is required'}, status=400)

    try:
        # Fetch TestValue, SampleStatus, and BarcodeTestDetails based on patient_id
        test_values = TestValue.objects.filter(patient_id=patient_id)
        sample_status = SampleStatus.objects.filter(patient_id=patient_id)
        barcode_details = BarcodeTestDetails.objects.filter(patient_id=patient_id).first()

        # If no test values are found
        if not test_values:
            return JsonResponse({'error': 'Test values not found for the given patient ID'}, status=404)

        # Parse barcodes from BarcodeTestDetails
        barcodes = []
        if barcode_details:
            try:
                tests = json.loads(barcode_details.tests) if isinstance(barcode_details.tests, str) else barcode_details.tests
                barcodes = [test.get("barcode") for test in tests if test.get("barcode")]
            except json.JSONDecodeError:
                barcodes = []

        # Prepare patient details
        patient_details = {
            "patient_id": test_values[0].patient_id,
            "patientname": test_values[0].patientname,
            "age": test_values[0].age,
            "date": test_values[0].date,
            "barcodes": barcodes,
            "testdetails": []
        }

        # Extract test details from TestValue and SampleStatus
        for test in test_values[0].testdetails:
            testname = test.get("testname")
            department = test.get("department", "N/A")
            parameters = test.get("parameters", [])

            # Fetch corresponding SampleStatus for this testname
            status = next(
                (status for status in sample_status[0].testdetails if status.get("testname") == testname), None)
            samplecollected_time = status.get("samplecollected_time") if status else None
            received_time = status.get("received_time") if status else None

            # Construct test detail dictionary
            test_detail = {
                "department": department,
                "testname": testname,
                "samplecollected_time": samplecollected_time,
                "received_time": received_time
            }

            # If parameters exist, only include testname and parameters
            if parameters:
                test_detail["parameters"] = parameters
            else:
                # Include these fields only if there are no parameters
                test_detail.update({
                    "method": test.get("method", "N/A"),
                    "specimen_type": test.get("specimen_type", "N/A"),
                    "value": test.get("value", "N/A"),
                    "unit": test.get("unit", "N/A"),
                    "reference_range": test.get("reference_range", "N/A")
                })

            patient_details["testdetails"].append(test_detail)

        return JsonResponse(patient_details, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
  

from django.http import JsonResponse
from datetime import datetime
from django.utils.timezone import make_aware
from .models import SampleStatus, TestValue
import traceback
def patient_test_status(request):
    try:
        patient_ids = request.GET.getlist('patient_id')  # Accept multiple patient IDs
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        if not patient_ids:
            return JsonResponse({'error': 'Missing patient_id'}, status=400)
        if not from_date or not to_date:
            today = make_aware(datetime.now())
            from_date = today.strftime("%Y-%m-%d")
            to_date = today.strftime("%Y-%m-%d")
        from_datetime = make_aware(datetime.strptime(from_date, "%Y-%m-%d"))
        to_datetime = make_aware(datetime.strptime(to_date, "%Y-%m-%d")).replace(hour=23, minute=59, second=59)
        response_data = {}
        # Query SampleStatus and TestValue in bulk
        sample_status_records = SampleStatus.objects.filter(
            patient_id__in=patient_ids,
            date__range=(from_datetime, to_datetime)
        ).values("patient_id", "testdetails")
        test_value_records = TestValue.objects.filter(
            patient_id__in=patient_ids,
            date__range=(from_datetime, to_datetime)
        ).values("patient_id", "barcode", "testdetails")
        # Organize sample statuses
        sample_status_map = {}
        for record in sample_status_records:
            patient_id = record["patient_id"]
            test_details = record["testdetails"]
            if patient_id not in sample_status_map:
                sample_status_map[patient_id] = []
            sample_status_map[patient_id].extend(test_details)
        # Organize test values
        test_value_map = {}
        for record in test_value_records:
            patient_id = record["patient_id"]
            barcode = record["barcode"]
            test_details = record["testdetails"]
            if patient_id not in test_value_map:
                test_value_map[patient_id] = {"barcode": barcode, "testdetails": []}
            test_value_map[patient_id]["testdetails"].extend(test_details)
        # Process each patient ID
        for patient_id in patient_ids:
            barcode = None
            status = "Registered"
            sample_test_details = sample_status_map.get(patient_id, [])
            test_value_details = test_value_map.get(patient_id, {}).get("testdetails", [])
            # **Determine Sample Collection & Reception Status**
            all_collected = all(test.get("samplestatus") == "Sample Collected" for test in sample_test_details) if sample_test_details else False
            partially_collected = any(test.get("samplestatus") == "Sample Collected" for test in sample_test_details)
            all_received = all(test.get("samplestatus") == "Received" for test in sample_test_details) if sample_test_details else False
            partially_received = any(test.get("samplestatus") == "Received" for test in sample_test_details)
            if all_collected:
                status = "Collected"
            elif partially_collected:
                status = "Partially Collected"
            if all_received:
                status = "Received"
            elif partially_received:
                status = "Partially Received"
            # **Process Test Values**
            if test_value_details:
                barcode = test_value_map[patient_id]["barcode"]
                all_tested = all(test.get("value") is not None for test in test_value_details)
                partially_tested = any(test.get("value") is not None for test in test_value_details)
                approve_all = all(test.get("approve", False) for test in test_value_details)
                approve_partial = any(test.get("approve", False) for test in test_value_details)
                dispatch_all = all(test.get("dispatch", False) for test in test_value_details)
                # **Update status hierarchy**
                if all_received or partially_received:
                    if all_tested:
                        status = "Tested"
                    elif partially_tested:
                        status = "Partially Tested"
                if approve_all:
                    status = "Approved"
                elif approve_partial:
                    status = "Partially Approved"
                if dispatch_all:
                    status = "Dispatched"
            # **Store in response**
            response_data[patient_id] = {
                "patient_id": patient_id,
                "barcode": barcode,
                "status": status,  # Now includes all statuses (approved, dispatched, etc.)
            }
        return JsonResponse(response_data)
    except Exception as e:
        print("Critical Error:", str(e))
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime, timedelta
from pymongo import MongoClient
from urllib.parse import quote_plus
import certifi
@csrf_exempt
def overall_report(request):
    # MongoDB Connection Setup
    password = quote_plus('Smrft@2024')
    client = MongoClient(
        f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
        tls=True,
        tlsCAFile=certifi.where()
    )
    db = client.Lab
    patients_collection = db["labbackend_patient"]  # MongoDB collection
    if request.method == "GET":
        # Get query parameters
        patient_id = request.GET.get("patient_id", None)
        from_date = request.GET.get("from_date", None)
        to_date = request.GET.get("to_date", None)
        # Parse date filters
        try:
            if from_date:
                from_date = datetime.strptime(from_date, "%Y-%m-%d")
            if to_date:
                to_date = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        # Fetch patient data from MongoDB
        query = {}
        if patient_id:
            query["patient_id"] = patient_id
        if from_date and to_date:
            query["date"] = {"$gte": from_date, "$lt": to_date}
        patients = list(patients_collection.find(query))
        if not patients:
            return JsonResponse([], safe=False)  # Return empty list if no data found
        formatted_data = []
        for patient in patients:
            # Extract values safely
            age_combined = f"{patient.get('age', 'N/A')} {patient.get('age_type', '')}"
            discount = int(patient.get('discount', 0) or 0)
            # Parse test names
            test_list = []
            if isinstance(patient.get("testname"), str) and patient["testname"].strip():
                try:
                    test_list = json.loads(patient["testname"])
                except json.JSONDecodeError:
                    test_list = []
            elif isinstance(patient.get("testname"), list):
                test_list = patient["testname"]
            testnames = ", ".join([test["testname"] for test in test_list]) if test_list else ""
            no_of_tests = len(test_list)
            # Parse payment method - FIX HERE
            payment_data = {}
            paymentmethod = "N/A"
            # First, ensure we're working with valid payment_method data
            payment_method_raw = patient.get("payment_method", "")
            # Handle empty string or None cases
            if not payment_method_raw or payment_method_raw == "\"\"":
                paymentmethod = "N/A"
            else:
                # If it's already a dict, use it directly
                if isinstance(payment_method_raw, dict):
                    payment_data = payment_method_raw
                    paymentmethod = payment_data.get("paymentmethod", "N/A")
                # If it's a string, try to parse it as JSON
                elif isinstance(payment_method_raw, str):
                    try:
                        # Remove any extra quotes that might cause JSON parsing issues
                        cleaned_payment_data = payment_method_raw.strip()
                        if cleaned_payment_data.startswith('"') and cleaned_payment_data.endswith('"'):
                            cleaned_payment_data = cleaned_payment_data[1:-1]
                        # Try to parse as JSON
                        if cleaned_payment_data and cleaned_payment_data != "\"\"":
                            payment_data = json.loads(cleaned_payment_data)
                            if isinstance(payment_data, dict):
                                paymentmethod = payment_data.get("paymentmethod", "N/A")
                            else:
                                paymentmethod = str(payment_data)
                        else:
                            paymentmethod = "N/A"
                    except json.JSONDecodeError:
                        # If it can't be parsed as JSON, use the raw string
                        paymentmethod = payment_method_raw
            # Parse credit_details
            credit_details = []
            if "credit_details" in patient and patient["credit_details"]:
                try:
                    if isinstance(patient["credit_details"], str):
                        credit_details = json.loads(patient["credit_details"])  # Convert JSON string to list
                    elif isinstance(patient["credit_details"], list):
                        credit_details = patient["credit_details"]
                except json.JSONDecodeError:
                    credit_details = []
            # Ensure credit_amount and total_amount are integers
            try:
                total_amount = int(float(patient.get("totalAmount", 0) or 0))
            except (ValueError, TypeError):
                total_amount = 0
            try:
                credit_amount = int(float(patient.get("credit_amount", 0) or 0))
            except (ValueError, TypeError):
                credit_amount = 0
            # Parse partial payment method
            partial_payment_method = "N/A"
            if paymentmethod == "PartialPayment":
                partial_payment_data = {}
                partial_payment_raw = patient.get("PartialPayment", "")
                if not partial_payment_raw or partial_payment_raw == "\"\"":
                    partial_payment_method = "PartialPayment"
                else:
                    # If it's already a dict, use it directly
                    if isinstance(partial_payment_raw, dict):
                        partial_payment_data = partial_payment_raw
                    # If it's a string, try to parse it as JSON
                    elif isinstance(partial_payment_raw, str):
                        try:
                            # Remove any extra quotes that might cause JSON parsing issues
                            cleaned_data = partial_payment_raw.strip()
                            if cleaned_data.startswith('"') and cleaned_data.endswith('"'):
                                cleaned_data = cleaned_data[1:-1]
                            # Try to parse as JSON
                            if cleaned_data and cleaned_data != "\"\"":
                                partial_payment_data = json.loads(cleaned_data)
                            else:
                                partial_payment_data = {}
                        except json.JSONDecodeError:
                            partial_payment_data = {}
                    if isinstance(partial_payment_data, dict):
                        partial_payment_method = partial_payment_data.get("method", "PartialPayment")
                    else:
                        partial_payment_method = "PartialPayment"
            else:
                partial_payment_method = paymentmethod
            # Format response data
            formatted_data.append({
                "date": patient.get("date").strftime("%Y-%m-%d") if "date" in patient else "N/A",
                "patient_id": patient.get("patient_id", "N/A"),
                "patient_name": patient.get("patientname", "N/A"),
                "gender": patient.get("gender", "N/A"),
                "refby": patient.get("refby", "N/A"),
                "age": age_combined,
                "b2b": patient.get("B2B", "N/A"),
                "sample_collector": patient.get("sample_collector", "N/A"),
                "salesMapping": patient.get("salesMapping", "N/A"),
                "total_amount": total_amount,
                "credit_amount": credit_amount,
                "credit_details": credit_details,
                "discount": discount,
                "payment_method": partial_payment_method,
                "test_names": testnames,
                "no_of_tests": no_of_tests,
            })
        return JsonResponse(formatted_data, safe=False)
    return JsonResponse({"error": "Invalid request method. Only GET is allowed."}, status=405)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from .models import TestValue  # Import your model
@csrf_exempt
def patient_test_sorting(request):
    try:
        patient_id = request.GET.get('patient_id')
        date = request.GET.get('date', datetime.now().strftime("%Y-%m-%d"))
        if not patient_id:
            return JsonResponse({'error': 'Missing patient_id'}, status=400)
        # Ensure the date is in YYYY-MM-DD format
        try:
            formatted_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
        # Filter test values for the exact date
        tests = TestValue.objects.filter(patient_id=patient_id, date=formatted_date).values("testdetails")
        test_list = []
        for test in tests:
            testdetails_data = test["testdetails"]
            if isinstance(testdetails_data, str):
                try:
                    testdetails_list = json.loads(testdetails_data)
                except json.JSONDecodeError:
                    continue  # Skip invalid JSON
            elif isinstance(testdetails_data, list):
                testdetails_list = testdetails_data
            else:
                continue
            test_list.extend(testdetails_list)
        return JsonResponse({patient_id: {"testdetails": test_list}})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from pymongo import MongoClient
from urllib.parse import quote_plus
import certifi
from datetime import datetime
@csrf_exempt
def credit_amount_update(request, patient_id):
    password = quote_plus('Smrft@2024')
    # MongoDB connection with TLS certificate
    client = MongoClient(
        f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
        tls=True,
        tlsCAFile=certifi.where()
    )
    db = client.Lab
    collection = db['labbackend_patient']
    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
            # Convert incoming values
            credit_amount = str(body.get("credit_amount", "0"))  # Store as a string
            amount_paid = int(float(body.get("amount_paid", 0)))
            paid_date = body.get("paid_date", None)
            payment_method = body.get("payment_method", "N/A")  # Default to "N/A" if missing
            # Validate required fields
            if not credit_amount:
                return JsonResponse({"error": "Missing required field: credit_amount."}, status=400)
            # Fetch the patient document
            patient = collection.find_one({"patient_id": patient_id})
            if not patient:
                return JsonResponse({"error": "Patient not found."}, status=404)
            # Parse existing credit details safely
            credit_details = patient.get("credit_details", [])
            if isinstance(credit_details, str):
                try:
                    credit_details = json.loads(credit_details)
                except json.JSONDecodeError:
                    credit_details = []
            # Calculate the updated credit amount
            current_credit_amount = int(float(patient.get("credit_amount", 0)))
            updated_credit_amount = str(current_credit_amount - amount_paid)  # Store as string
            # Append the new entry to `credit_details`
            credit_details.append({
                "credit_amount": credit_amount,  # Stored as a string
                "amount_paid": amount_paid,
                "paid_date": paid_date,
                "payment_method": payment_method,  # Store payment method
                "remaining_amount": updated_credit_amount  # Stored as a string
            })
            # Update the database
            collection.update_one(
                {"patient_id": patient_id},
                {
                    "$set": {
                        "credit_amount": updated_credit_amount,  # Store as a string
                        "credit_details": json.dumps(credit_details)  # Store as JSON string
                    }
                }
            )
            return JsonResponse({
                "message": "Credit amount updated successfully.",
                "credit_details": credit_details
            })
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method. Only PATCH is allowed."}, status=405)



@api_view(['PATCH'])
def update_credit_amount(request, patient_id):
    # MongoDB connection setup
    password = quote_plus('Smrft@2024')

        # MongoDB connection with TLS certificate
    client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )

    db = client.Lab  # Database name
    collection = db['labbackend_patient']
    # Retrieve the Django patient record, return 404 if not found
    patient = get_object_or_404(Patient, patient_id=patient_id)
    # Update only the credit amount if provided in the request data
    credit_amount = request.data.get("credit_amount")
    if credit_amount is not None:
        # Convert credit_amount to an integer for MongoDB consistency
        try:
            credit_amount = (credit_amount)
        except ValueError:
            return Response({"error": "Credit amount must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
        # Update the credit amount in Django
        patient.credit_amount = credit_amount
        patient_id_str = str(patient_id)
        # Update MongoDB with credit_amount as an integer
        result = collection.update_one(
            {"patient_id": patient_id_str},
            {"$set": {"credit_amount": credit_amount}},
            upsert=False
        )
        # Check if the document was matched in MongoDB
        if result.matched_count == 0:
            return Response({"error": "Patient not found in MongoDB."}, status=status.HTTP_404_NOT_FOUND)
        # Save the updated credit amount in the Django model
        try:
            patient.save()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "message": "Credit amount updated successfully",
            "credit_amount": credit_amount
        }, status=status.HTTP_200_OK)
    # Return an error if credit_amount was not provided in the request
    return Response({"error": "Credit amount is required."}, status=status.HTTP_400_BAD_REQUEST)


from django.core.mail import EmailMessage
from django.conf import settings  # To access the settings for DEFAULT_FROM_EMAIL
@api_view(['POST'])
def send_email(request):
    try:
        subject = request.data.get('subject', 'No Subject')
        message = request.data.get('message', 'No Message')
        # Use default recipient if none provided
        recipient_list = request.data.get('recipients', ['parthibansmrft@gmail.com'])  # Default recipient
        # Use default sender if none provided
        from_email = request.data.get('from_email', settings.DEFAULT_FROM_EMAIL)  # Default sender
        signature = 'Contact Us, \n Shanmuga Hospital, \n 24, Saradha College Road,\n Salem-636007 Tamil Nadu,\n \n 6369131631,0427 270 6666,\n info@shanmugahospital.com,\n https://shanmugahospital.com/'
        files = request.FILES.getlist('attachments')
        # Ensure recipient_list is a list
        if isinstance(recipient_list, str):
            recipient_list = [recipient_list]  # Convert string to list if only one email address is provided
        # Ensure at least one recipient is provided
        if not recipient_list:
            return JsonResponse({'status': 'error', 'message': 'At least one recipient is required to send the email.'}, status=400)
        email = EmailMessage(
            subject=subject,
            body=message+"\n\n"+signature,
            from_email=from_email,  # Sender's email
            to=recipient_list,      # List of recipients
        )
        for file in files:
            email.attach(file.name, file.read(), file.content_type)
        email.send()
        return JsonResponse({'status': 'success', 'message': 'Email sent successfully!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
   
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import SalesVisitLog
from .serializers import SalesVisitLogSerializer
from datetime import datetime, timedelta

from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import SalesVisitLog
from .serializers import SalesVisitLogSerializer
from datetime import datetime
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import SalesVisitLog
from .serializers import SalesVisitLogSerializer

from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import SalesVisitLog
from .serializers import SalesVisitLogSerializer
import re

@csrf_exempt
@api_view(['GET', 'POST'])
def salesvisitlog(request):
    if request.method == 'POST':
        serializer = SalesVisitLogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET':
        date = request.query_params.get('date', None)
        month = request.query_params.get('month', None)
        week = request.query_params.get('week', None)  # Expecting "YYYY-Wxx"
        salesPerson = request.query_params.get('salesPerson', None)

        logs = SalesVisitLog.objects.all()

        # Filter by a specific date
        if date:
            logs = logs.filter(date=datetime.strptime(date, "%Y-%m-%d").date())

        # Filter by month (YYYY-MM format)
        if month:
            try:
                year, month = map(int, month.split('-'))
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1)
                else:
                    end_date = datetime(year, month + 1, 1)
                logs = logs.filter(date__gte=start_date, date__lt=end_date)
            except ValueError:
                return Response({"error": "Invalid month format. Use YYYY-MM."}, status=status.HTTP_400_BAD_REQUEST)

        # Filter by week (YYYY-Wxx format)
        if week:
            try:
                match = re.match(r"(\d{4})-W(\d{1,2})", week)
                if not match:
                    return Response({"error": "Invalid week format. Use YYYY-Wxx."}, status=status.HTTP_400_BAD_REQUEST)

                year, week_number = map(int, match.groups())
                start_date = datetime.strptime(f"{year}-W{week_number}-1", "%Y-W%W-%w").date()
                end_date = start_date + timedelta(days=6)  # Week ends on Sunday
                
                logs = logs.filter(date__range=[start_date, end_date])
            except ValueError:
                return Response({"error": "Invalid week format. Use YYYY-Wxx."}, status=status.HTTP_400_BAD_REQUEST)

        # Filter by salesperson name
        if salesPerson:
            logs = logs.filter(salesMapping__iexact=salesPerson)

        serializer = SalesVisitLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SalesVisitLog
from .serializers import SalesVisitLogSerializer
import datetime
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SalesVisitLog  # Ensure you import your model
from .serializers import SalesVisitLogSerializer

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SalesVisitLog
from .serializers import SalesVisitLogSerializer
from datetime import datetime, date  # Import `date` separately

@csrf_exempt
def get_sales_log(request):
    date_param = request.GET.get("date")  # YYYY-MM or YYYY-MM-DD
    salesMapping = request.GET.get("salesMapping")

    if not date_param or not salesMapping:
        return JsonResponse({"error": "Date and user salesmapping name are required"}, status=400)

    try:
        if len(date_param) == 7:  # Filtering by month (YYYY-MM)
            year, month = map(int, date_param.split("-"))
            start_date = date(year, month, 1)  # First day of the month
            if month == 12:
                end_date = date(year + 1, 1, 1)  # Start of next year
            else:
                end_date = date(year, month + 1, 1)  # Start of next month
            sales_logs = SalesVisitLog.objects.filter(
                date__gte=start_date, date__lt=end_date, salesMapping=salesMapping
            )
        else:  # Filtering by full date (YYYY-MM-DD)
            selected_date = datetime.strptime(date_param, "%Y-%m-%d").date()  # Correct usage
            sales_logs = SalesVisitLog.objects.filter(date=selected_date, salesMapping=salesMapping)

    except ValueError:
        return JsonResponse({"error": "Invalid date format"}, status=400)

    serializer = SalesVisitLogSerializer(sales_logs, many=True)
    return JsonResponse(serializer.data, safe=False)



from .models import HospitalLab
from .serializers import HospitalLabSerializer
@api_view(['GET', 'POST'])
def hospitallabform(request):
    if request.method == 'GET':
        # Retrieve all HospitalLab objects and serialize them
        hospital_labs = HospitalLab.objects.all()
        serializer = HospitalLabSerializer(hospital_labs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        # Handle the creation of a new HospitalLab object
        serializer = HospitalLabSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Hospital/Lab details saved successfully."},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
   

from .models import LogisticData
from .serializers import LogisticDataSerializer
@api_view(['POST'])
def save_logistic_data(request):
    if request.method == 'POST':
        serializer = LogisticDataSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # Save the logistic data
            return Response({"message": "Data saved successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
   
   
@api_view(['GET'])
def get_logistic_data(request):
    if request.method == 'GET':
        data = LogisticData.objects.all()  # Fetch all logistic data
        serializer = LogisticDataSerializer(data, many=True)
        return Response(serializer.data)
   

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from .models import LogisticTask
from .serializers import LogisticTaskSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import LogisticTask
from .serializers import LogisticTaskSerializer
from datetime import datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import LogisticTask
from .serializers import LogisticTaskSerializer
from datetime import datetime
@api_view(['POST', 'GET'])
def savesamplecollectordetails(request):
    if request.method == 'POST':
        tasks_data = request.data
        if isinstance(tasks_data, dict):  # Convert single object into a list
            tasks_data = [tasks_data]
        for task_data in tasks_data:
            # Exclude samplePickedUp and samplePickedUpTime initially
            task_data.pop("samplePickedUp", None)
            task_data.pop("samplePickedUpTime", None)
            # Check if the task already exists
            existing_task = LogisticTask.objects.filter(
                sampleCollector=task_data.get("sampleCollector"),
                date=task_data.get("date"),
                lab_name=task_data.get("lab_name"),
                salesMapping=task_data.get("salesMapping"),
            ).exists()
            if not existing_task:
                serializer = LogisticTaskSerializer(data=task_data)
                if serializer.is_valid():
                    serializer.save()
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Tasks saved successfully."}, status=status.HTTP_201_CREATED)
    elif request.method == 'GET':
        tasks = LogisticTask.objects.all()  # Fetch all logistic data
        serializer = LogisticTaskSerializer(tasks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
from rest_framework.decorators import api_view
from datetime import datetime
from pymongo import MongoClient
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from pymongo import MongoClient
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
@api_view(['PATCH'])
def update_sample_collector_details(request):
    password = quote_plus('Smrft@2024')
    client = MongoClient(
        f"mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority",
        tls=True,
        tlsCAFile=certifi.where(),
    )
    db = client["Lab"]
    collection = db["labbackend_logistictask"]
    try:
        sampleCollector = request.data.get("sampleCollector")
        date_str = request.data.get("date")
        lab_name = request.data.get("lab_name")
        salesperson = request.data.get("salesperson")
        # Convert date to datetime object for matching MongoDB format
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        filter_query = {
            "sampleCollector": sampleCollector,
            "date": date_obj,
            "lab_name": lab_name,
            "salesperson": salesperson,
            "status": None  # Only update if status is initially null
        }
        sample_picked_up = request.data.get("samplePickedUp", False)
        sample_picked_up_time = request.data.get("samplePickedUpTime")
        if sample_picked_up and sample_picked_up_time:
            update_fields = {
                "status": "samplepickedup",
                "samplepickeduptime": sample_picked_up_time
            }
            result = collection.update_one(filter_query, {"$set": update_fields})
            if result.matched_count == 0:
                return Response({"error": "No matching task found or status already updated."}, status=status.HTTP_404_NOT_FOUND)
            return Response({"message": "Task updated successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
   

def getlogisticdatabydate(request):
    # Get query parameters
    sample_collector = request.GET.get('sampleCollector', None)
    if not sample_collector:
        return JsonResponse({"error": "sampleCollector is required"}, status=400)
    # Filter data by sampleCollector
    data = LogisticData.objects.filter(sampleCollector=sample_collector)
    # Serialize the data
    serializer = LogisticDataSerializer(data, many=True)
    return JsonResponse(serializer.data, safe=False)
   

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


from datetime import datetime, timedelta
import pytz
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Patient, SampleStatus, TestValue
from .serializers import PatientSerializer, SampleStatusSerializer, TestValueSerializer

# Define the timezone for India Standard Time (IST)
IST = pytz.timezone('Asia/Kolkata')

class ConsolidatedDataView(APIView):
    def get(self, request):
        # Default to today's date if no date is provided
        date = request.query_params.get('date', datetime.now().strftime('%Y-%m-%d'))
        try:
            # Parse the input date
            input_date = datetime.strptime(date, '%Y-%m-%d').date()
            
            # Retrieve all patients and filter those that have a non-null date
            patients = Patient.objects.all()
            filtered_patients = [
                patient for patient in patients 
                if patient.date and patient.date.astimezone(IST).date() == input_date
            ]
            
            response_data = []
            for patient in filtered_patients:
                sample_status = SampleStatus.objects.filter(patient_id=patient.patient_id).first()
                test_value = TestValue.objects.filter(patient_id=patient.patient_id).first()
                
                if not (sample_status and test_value):
                    continue

                barcode = sample_status.barcode if sample_status.barcode else "N/A"
                
                for test in sample_status.testdetails:
                    matching_test = next(
                        (tv for tv in test_value.testdetails if tv['testname'] == test['testname']),
                        None
                    )
                    if matching_test:
                        samplecollected_time = test.get('samplecollected_time', 'pending')
                        dispatch_time = matching_test.get('dispatch_time', 'pending')
                        department = test.get('department')

                        if samplecollected_time == 'pending' or dispatch_time == 'pending':
                            total_processing_time = 'pending'
                        else:
                            try:
                                samplecollected_time_dt = datetime.fromisoformat(samplecollected_time).replace(tzinfo=IST)
                                dispatch_time_dt = datetime.fromisoformat(dispatch_time).replace(tzinfo=IST)
                                total_seconds = int((dispatch_time_dt - samplecollected_time_dt).total_seconds())

                                # Convert seconds to hh:mm:ss format
                                total_processing_time = str(timedelta(seconds=total_seconds))
                            except ValueError:
                                total_processing_time = 'pending'

                        # Convert patient.date to IST format
                        patient_date_ist = patient.date.astimezone(IST).strftime('%Y-%m-%d %H:%M:%S')

                        response_data.append({
                            "patient_id": patient.patient_id,
                            "patient_name": patient.patientname,
                            "age": patient.age,
                            "date": patient_date_ist,  # Updated to IST format
                            "barcode": barcode,
                            "test_name": test['testname'],
                            "department": department,
                            "collected_time": samplecollected_time,
                            "received_time": test.get('received_time', 'pending'),
                            "approval_time": matching_test.get('approve_time', 'pending'),
                            "dispatch_time": dispatch_time,
                            "total_processing_time": total_processing_time  # Now in hh:mm:ss format
                        })

            return Response(response_data, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)




from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from pymongo import MongoClient
from urllib.parse import quote_plus
import certifi
from bson import ObjectId

# Function to get MongoDB collection
def get_mongo_collection():
    password = quote_plus("Smrft@2024")
    client = MongoClient(
        f"mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority",
        tls=True,
        tlsCAFile=certifi.where(),
    )
    db = client["Lab"]
    return db["labbackend_invoice"]


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from pymongo import MongoClient
from urllib.parse import quote_plus
import certifi
from bson import ObjectId


# Function to get MongoDB collection
def get_mongo_collection():
    password = quote_plus("Smrft@2024")
    client = MongoClient(
        f"mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority",
        tls=True,
        tlsCAFile=certifi.where(),
    )
    db = client["Lab"]
    return db["labbackend_invoice"]

@csrf_exempt
def generate_invoice(request):
    collection = get_mongo_collection()
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            # Extract patient IDs from the request
            patient_ids = [patient["patient_id"] for patient in data.get("patients", [])]
            
            # Update credit_amount to "0" for selected patients in Django database
            Patient.objects.filter(patient_id__in=patient_ids).update(credit_amount="0")

            # Insert invoice data into MongoDB
            result = collection.insert_one(data)

            return JsonResponse(
                {"message": "Invoice stored successfully, credit amount updated", "id": str(result.inserted_id)},
                status=201,
            )
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)



def get_invoices(request):
    collection = get_mongo_collection()
    invoices = list(collection.find({}, {"_id": 0}))  # Exclude MongoDB's `_id` field
    return JsonResponse(invoices, safe=False)


@csrf_exempt
def update_invoice(request, invoice_number):
    """Update the invoice with total, paid, and pending amounts."""
    collection = get_mongo_collection()

    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            new_credit_amount = data.get("totalCreditAmount")
            paid_amount = data.get("paidAmount", "0.00")

            if new_credit_amount is None:
                return JsonResponse({"error": "Missing totalCreditAmount field"}, status=400)

            # Calculate pending amount
            total = float(new_credit_amount)
            paid = float(paid_amount)
            pending = max(0, total - paid)
            
            # Update the invoice with all three values
            result = collection.update_one(
                {"invoiceNumber": invoice_number},
                {"$set": {
                    "totalCreditAmount": new_credit_amount,
                    "paidAmount": paid_amount,
                    "pendingAmount": str(pending)
                }},
            )

            if result.matched_count == 0:
                return JsonResponse({"error": "Invoice not found"}, status=404)

            return JsonResponse({
                "message": "Invoice updated successfully",
                "pendingAmount": str(pending)
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)




        
@csrf_exempt
def delete_invoice(request, invoice_id):
    """Delete an invoice based on invoice_id"""
    collection = get_mongo_collection()

    if request.method == "DELETE":
        try:
            result = collection.delete_one({"invoiceNumber": invoice_id})

            if result.deleted_count == 0:
                return JsonResponse({"error": "Invoice not found"}, status=404)

            return JsonResponse({"message": "Invoice deleted successfully"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)


from django.http import JsonResponse
from .models import Patient
from datetime import datetime, timedelta
import json
def salesdashboard(request):
    sales_mapping = request.GET.get("salesMapping")
    date_str = request.GET.get("date")  # YYYY-MM-DD
    month_str = request.GET.get("month")  # YYYY-MM (optional for monthly data)
    if not sales_mapping:
        return JsonResponse({"error": "Missing salesMapping parameter"}, status=400)
    try:
        if date_str:  # Date-based filtering
            start_date = datetime.strptime(date_str, "%Y-%m-%d")
            end_date = start_date + timedelta(days=1)  # End of the day
        elif month_str:  # Month-based filtering
            start_date = datetime.strptime(month_str, "%Y-%m")
            end_date = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1)  # First day of next month
        else:
            return JsonResponse({"error": "Missing date or month parameter"}, status=400)
        # Query data from MongoDB
        patients = Patient.objects.filter(
            salesMapping=sales_mapping,
            date__gte=start_date,
            date__lt=end_date
        )
        # Calculate total patients
        total_patients = patients.count()
        # Calculate total amount
        total_amount = sum(int(patient.totalAmount) for patient in patients if str(patient.totalAmount).isdigit())
        # Count test occurrences
        test_counts = {}
        total_tests = 0
        for patient in patients:
            test_data = patient.testname
            if isinstance(test_data, str):
                try:
                    test_data = json.loads(test_data)
                except json.JSONDecodeError:
                    continue  # Skip invalid JSON
            if isinstance(test_data, list):
                for test in test_data:
                    test_name = test.get("testname", "Unknown")
                    test_counts[test_name] = test_counts.get(test_name, 0) + 1
                    total_tests += 1
        return JsonResponse({
            "totalPatients": total_patients,
            "totalAmount": total_amount,
            "totalTests": total_tests,
            "testCounts": test_counts
        })
    except ValueError:
        return JsonResponse({"error": "Invalid date or month format"}, status=400)
    

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import SalesVisitLog
from .serializers import SalesVisitLogSerializer
@api_view(['GET'])
def getsalesmapping(request):
    if request.method == 'GET':
        data = SalesVisitLog.objects.all()
        serializer = SalesVisitLogSerializer(data, many=True)
        return Response(serializer.data)
    

from django.shortcuts import get_list_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import LogisticTask
from .serializers import LogisticTaskSerializer
from django.shortcuts import get_list_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Patient
from .serializers import PatientSerializer
@api_view(['GET'])
def logisticdashboard(request):
    sample_collector = request.GET.get('sampleCollector')
    selected_date = request.GET.get('date')
    if not sample_collector:
        return Response({"error": "Sample collector is required"}, status=400)
    try:
        data = Patient.objects.filter(sample_collector=sample_collector)
        if selected_date:
            data = data.filter(date=selected_date)  # Filter by selected date
        serializer = PatientSerializer(data, many=True)
        return Response(serializer.data)
    except Patient.DoesNotExist:
        return Response({"error": "No data found"}, status=404)


import json
import random
from pymongo import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
client = MongoClient("mongodb+srv://shinovalab:Smrft%402024@cluster0.xbq9c.mongodb.net/?retryWrites=true&w=majority")
db = client["Lab"]
collection = db["labbackend_patient"]
@csrf_exempt
def update_patient(request, patient_id):
    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            # Ensure valid fields are updated
            update_data = {
                key: value for key, value in data.items() if value != "" and value is not None
            }
            # Convert date string to datetime object if it exists
            if "date" in update_data:
                try:
                    update_data["date"] = datetime.fromisoformat(update_data["date"])
                except ValueError:
                    return JsonResponse({"error": "Invalid date format"}, status=400)
            result = collection.update_one({"patient_id": patient_id}, {"$set": update_data})
            if result.modified_count > 0:
                return JsonResponse({"message": "Patient updated successfully"}, status=200)
            else:
                return JsonResponse({"message": "No changes made"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=400)

@csrf_exempt
def search_refund(request):
    if request.method == "GET":
        patient_id = request.GET.get('patient_id')
        select_date = request.GET.get('date')  # Expected in YYYY-MM-DD format
        if not patient_id or not select_date:
            return JsonResponse({"error": "Patient ID and Date are required"}, status=400)
        try:
            selected_date = datetime.strptime(select_date, "%Y-%m-%d")
            # Define start and end of the selected date
            start_of_day = make_aware(datetime.combine(selected_date, datetime.min.time()))
            end_of_day = make_aware(datetime.combine(selected_date, datetime.max.time()))
            # Query using date range
            patients = Patient.objects.filter(
                patient_id=patient_id,
                date__gte=start_of_day,
                date__lt=end_of_day  # Use `<` to exclude the next day's midnight
            )
            result = list(patients.values())
            return JsonResponse({"patients": result}, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
       

# Temporary dictionary to hold OTPs (non-persistent)
otp_storage_refund = {}

@csrf_exempt
def generate_otp_refund(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get("email")
            patient_details = data.get("patient_details", {})

            if not email:
                return JsonResponse({"error": "Email is required"}, status=400)
           
            otp = str(random.randint(100000, 999999))  # Generate 6-digit OTP
            otp_storage_refund[email] = otp  # Store in a temporary dictionary
           
            # Construct a professional email message with patient details
            subject = "Refund Verification OTP"
            message = f"""Hi Sir/ Madam,

A refund request has been initiated with the following details:

Patient Information:
- Patient ID: {patient_details.get('patient_id', 'N/A')}
- Patient Name: {patient_details.get('patient_name', 'N/A')}

Refund Details:
- Tests: {patient_details.get('tests', 'N/A')}
- Total Refund Amount: ₹{patient_details.get('total_refund_amount', 'N/A')}

Reason for Refund:
{patient_details.get('reason', 'No reason provided')}

Your OTP for verifying this refund is: {otp}

Please enter this OTP to process the refund. 
This OTP will expire shortly.

Best regards,
Shanmuga Diagnostics"""

            from_email = settings.EMAIL_HOST_USER

            try:
                send_mail(subject, message, from_email, [email])
                return JsonResponse({
                    "message": "OTP sent successfully", 
                    "otp": otp  # Only for testing, remove in production
                }, status=200)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)


@csrf_exempt
def verify_and_process_refund(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get("email")
            entered_otp = str(data.get("otp"))
            patient_id = data.get("patient_id")
            selected_tests = data.get("selected_tests")

            if not email or not entered_otp or not patient_id or not selected_tests:
                return JsonResponse({"error": "Email, OTP, Patient ID, and selected tests are required."}, status=400)

            # Verify OTP from temporary dictionary
            stored_otp = otp_storage_refund.get(email)
            if stored_otp is None:
                print(f"OTP for {email} not found")
                return JsonResponse({"error": "OTP expired or not found"}, status=400)

            if str(stored_otp) != entered_otp:
                return JsonResponse({"error": "Invalid OTP"}, status=400)

            # Connect to MongoDB
            password = quote_plus('Smrft@2024')
            client = MongoClient(
                f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
                tls=True,
                tlsCAFile=certifi.where()
            )
            db = client.Lab
            patients_collection = db["labbackend_patient"]

            # Find patient record
            patient_record = patients_collection.find_one({"patient_id": patient_id})
            if not patient_record:
                return JsonResponse({"error": "Patient not found."}, status=404)

            # Parse test names
            test_list = json.loads(patient_record.get("testname", "[]"))
            remaining_tests = [test for test in test_list if test["testname"] not in selected_tests]
            refund_amount = sum(test["amount"] for test in test_list if test["testname"] in selected_tests)

            # Update totalAmount and credit_amount if applicable
            updated_total = int(patient_record["totalAmount"]) - refund_amount
            updated_credit_amount = int(patient_record["credit_amount"]) - refund_amount if "credit_amount" in patient_record else 0

            # Update the database
            update_data = {
                "testname": json.dumps(remaining_tests),
                "totalAmount": str(updated_total),
            }
            if "payment_method" in patient_record and "Credit" in patient_record["payment_method"]:
                update_data["credit_amount"] = str(updated_credit_amount)

            patients_collection.update_one({"patient_id": patient_id}, {"$set": update_data})

            # Remove OTP after successful verification
            del otp_storage_refund[email]

            return JsonResponse({"message": "Refund processed successfully", "refund_amount": refund_amount}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)

@csrf_exempt
def search_cancellation(request):
    if request.method == "GET":
        patient_id = request.GET.get('patient_id')
        current_date = datetime.now().date()  # Get current date
        
        if not patient_id:
            return JsonResponse({"error": "Patient ID is required"}, status=400)
        
        try:
            # Convert current_date to aware datetime
            start_time = make_aware(datetime.combine(current_date, datetime.min.time()))  # 12:00 AM
            end_time = make_aware(datetime.combine(current_date, datetime.max.time()))  # 11:59 PM
           
            # Fetch patients for the specific patient_id within the date range
            patients = Patient.objects.filter(
                Q(patient_id=patient_id) &  # Explicitly filter by patient_id
                Q(date__range=(start_time, end_time))
            )
           
            # Convert queryset to list of dictionaries
            result = []
            for patient in patients:
                patient_dict = {
                    'patient_id': patient.patient_id,
                    'patientname': patient.patientname,
                    'date': patient.date,
                    'testname': json.loads(patient.testname) if isinstance(patient.testname, str) else patient.testname
                }
                result.append(patient_dict)
            
            return JsonResponse({"patients": result}, safe=False)
        
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        

# Temporary dictionary to hold OTPs (non-persistent)
otp_storage_cancellation = {}

@csrf_exempt
def generate_otp_cancellation(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get("email")
            patient_details = data.get("patient_details", {})

            if not email:
                return JsonResponse({"error": "Email is required"}, status=400)
           
            otp = str(random.randint(100000, 999999))  # Generate 6-digit OTP
            otp_storage_cancellation[email] = otp  # Store in a temporary dictionary
           
            # Construct a professional email message with patient details
            subject = "Cancellation Verification OTP"
            message = f"""Hi Sir/ Madam,

A cancellation request has been initiated with the following details:

Patient Information:
- Patient ID: {patient_details.get('patient_id', 'N/A')}
- Patient Name: {patient_details.get('patient_name', 'N/A')}

Cancellation Details:
- Tests: {patient_details.get('tests', 'N/A')}
- Total Cancellation Amount: ₹{patient_details.get('total_cancellation_amount', 'N/A')}

Reason for Cancellation:
{patient_details.get('reason', 'No reason provided')}

Your OTP for verifying this cancellation is: {otp}

Please enter this OTP to process the cancellation. 
This OTP will expire shortly.

Best regards,
Shanmuga Diagnostics"""

            from_email = settings.EMAIL_HOST_USER

            try:
                send_mail(subject, message, from_email, [email])
                return JsonResponse({
                    "message": "OTP sent successfully", 
                    "otp": otp  # Only for testing, remove in production
                }, status=200)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)


@csrf_exempt
def verify_and_process_cancellation(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get("email")
            entered_otp = str(data.get("otp"))
            patient_id = data.get("patient_id")
            selected_tests = data.get("selected_tests")

            if not email or not entered_otp or not patient_id or not selected_tests:
                return JsonResponse({"error": "Email, OTP, Patient ID, and selected tests are required."}, status=400)

            # Verify OTP
            stored_otp = otp_storage_cancellation.get(email)
            if stored_otp is None:
                return JsonResponse({"error": "OTP expired or not found"}, status=400)

            if str(stored_otp) != entered_otp:
                return JsonResponse({"error": "Invalid OTP"}, status=400)

            # Connect to MongoDB
            password = quote_plus('Smrft@2024')
            client = MongoClient(
                f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
                tls=True,
                tlsCAFile=certifi.where()
            )
            db = client.Lab
            patients_collection = db["labbackend_patient"]

            # Find patient record
            patient_record = patients_collection.find_one({"patient_id": patient_id})
            if not patient_record:
                return JsonResponse({"error": "Patient not found."}, status=404)

            # Get today's date in the correct format
            today_date = datetime.now().strftime("%Y-%m-%d")

            # Convert MongoDB date to a comparable format
            record_date = patient_record.get("date")
            if isinstance(record_date, dict) and "$date" in record_date:
                record_date = datetime.strptime(record_date["$date"][:10], "%Y-%m-%d").strftime("%Y-%m-%d")
            elif isinstance(record_date, datetime):
                record_date = record_date.strftime("%Y-%m-%d")
            else:
                return JsonResponse({"error": "Invalid date format in patient record."}, status=500)

            # Allow cancellation only if the record date is today
            if record_date != today_date:
                return JsonResponse({"error": "Only tests booked today can be canceled."}, status=400)

            # Parse test names from the record
            test_list = json.loads(patient_record.get("testname", "[]"))
            same_day_tests = [test for test in test_list if test["testname"] in selected_tests]

            if not same_day_tests:
                return JsonResponse({"error": "No matching tests found for cancellation."}, status=400)

            # Calculate refund amount and filter remaining tests
            refund_amount = sum(test["amount"] for test in same_day_tests)
            remaining_tests = [test for test in test_list if test["testname"] not in selected_tests]

            # Update totalAmount and credit_amount if applicable
            updated_total = int(patient_record["totalAmount"]) - refund_amount
            updated_credit_amount = int(patient_record["credit_amount"]) - refund_amount if "credit_amount" in patient_record else 0

            # Prepare update data
            update_data = {
                "testname": json.dumps(remaining_tests),
                "totalAmount": str(updated_total),
            }
            if "payment_method" in patient_record and "Credit" in patient_record["payment_method"]:
                update_data["credit_amount"] = str(updated_credit_amount)

            # Update the database
            patients_collection.update_one({"patient_id": patient_id}, {"$set": update_data})

            # Remove OTP after successful verification
            del otp_storage_cancellation[email]

            return JsonResponse({"message": "Cancellation processed successfully", "refund_amount": refund_amount}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)



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
    

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from .models import Patient
from .serializers import PatientSerializer

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
from .models import Patient

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
from datetime import datetime, timedelta
from .models import Patient

@api_view(['GET'])
def get_patient_tests(request, patient_id, date):
    """Fetch test details for a given patient ID and date"""
    try:
        # Convert string date to a datetime object
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return Response({"error": "Invalid date format, use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        # Define start and end of the day to match any time on that date
        start_of_day = datetime(date_obj.year, date_obj.month, date_obj.day, 0, 0, 0)
        end_of_day = datetime(date_obj.year, date_obj.month, date_obj.day, 23, 59, 59)

        # Retrieve the patient test details using a date range
        patient = Patient.objects.filter(patient_id=patient_id, date__gte=start_of_day, date__lte=end_of_day).first()

        if not patient:
            return Response({"error": "No tests found for the given date and patient ID"}, status=status.HTTP_404_NOT_FOUND)

        # Ensure tests are in the correct format (list)
        tests = patient.testname  # Assuming `testname` is stored as JSON

        if isinstance(tests, str):
            try:
                tests = json.loads(tests)  # Convert JSON string to list
            except json.JSONDecodeError:
                return Response({"error": "Invalid test data format"}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(tests, list):
            tests = []  # Default to an empty list if tests are not in a valid format

        # Parse payment method if stored as JSON string
        payment_method = patient.payment_method
        if isinstance(payment_method, str):
            try:
                payment_method = json.loads(payment_method)
            except json.JSONDecodeError:
                payment_method = {}

        # Prepare response data
        response_data = {
            "testname": tests,
            "discount": patient.discount,
            "payment_method": payment_method
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from pymongo import MongoClient
import certifi
import json
from urllib.parse import quote_plus

@api_view(['PATCH'])
def update_billing(request, patient_id):
    password = quote_plus('Smrft@2024')
    client = MongoClient(
        f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
        tls=True,
        tlsCAFile=certifi.where()
    )
    db = client.Lab
    collection = db['labbackend_patient']

    # Check if patient exists
    patient = collection.find_one({"patient_id": patient_id})
    if not patient:
        return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)

    new_data = request.data

    # Convert `totalAmount` and `credit_amount` to numbers if possible
    if "totalAmount" in new_data:
        try:
            new_data["totalAmount"] = str(new_data["totalAmount"])
        except ValueError:
            return Response({"error": "Invalid totalAmount format"}, status=status.HTTP_400_BAD_REQUEST)

    if "credit_amount" in new_data:
        try:
            new_data["credit_amount"] = str(new_data["credit_amount"]) if new_data["credit_amount"] else '0'
        except ValueError:
            return Response({"error": "Invalid credit_amount format"}, status=status.HTTP_400_BAD_REQUEST)

    # Ensure `testname` remains unchanged
    if "testname" in new_data:
        if not isinstance(new_data["testname"], (list, str)):
            return Response({"error": "Invalid testname format"}, status=status.HTTP_400_BAD_REQUEST)

    # Update MongoDB document
    collection.update_one({"patient_id": patient_id}, {"$set": new_data})

    # Fetch updated patient data
    updated_patient = collection.find_one({"patient_id": patient_id})
    if updated_patient and "_id" in updated_patient:
        updated_patient["_id"] = str(updated_patient["_id"])

    return Response(updated_patient, status=status.HTTP_200_OK)



from pymongo import MongoClient
import gridfs
from .models import ClinicalName
from .serializers import ClinicalNameSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from gridfs import GridFS
import certifi
from rest_framework.decorators import action
# MongoDB Connection Setup
from .models import ClinicalName
from .serializers import ClinicalNameSerializer
# MongoDB Connection Setup
def get_mongodb_connection():
    # Properly escape the password
    username = quote_plus("shinovalab")
    password = quote_plus("Smrft@2024")

    # MongoDB connection with TLS certificate
    client = MongoClient(
        f"mongodb+srv://{username}:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority",
        tls=True,  # Enable TLS/SSL
        tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
    )

    db = client.Lab  # Database name
    return db, GridFS(db)

# View for handling referrer code generation
@api_view(['GET'])
def get_last_referrer_code(request):
    try:
        last_clinical = ClinicalName.objects.all().order_by('-referrerCode').first()
        if last_clinical:
            return Response({'referrerCode': last_clinical.referrerCode})
        else:
            return Response({'referrerCode': 'SD0000'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['POST', 'GET'])
@csrf_exempt
def clinical_name(request):
    if request.method == 'POST':
        mou_copy = request.FILES.get('mouCopy')
        data = request.data.copy()
        
        if not data.get('clinicalname'):
            return Response({"error": "Clinical name is required"}, status=status.HTTP_400_BAD_REQUEST)

        if mou_copy:
            del data['mouCopy']
            
        # Set initial approval status
        data['status'] = 'PENDING_APPROVAL'
        data['first_approved'] = False
        data['final_approved'] = False

        serializer = ClinicalNameSerializer(data=data)

        if serializer.is_valid():
            try:
                clinical_name_instance = serializer.save()

                if mou_copy:
                    db, fs = get_mongodb_connection()
                    file_content = mou_copy.read()
                    file_id = fs.put(
                        file_content, 
                        filename=mou_copy.name,
                        content_type=mou_copy.content_type,
                        clinical_name=clinical_name_instance.clinicalname  
                    )
                    clinical_name_instance.mou_file_id = str(file_id)
                    clinical_name_instance.save()

                return Response(serializer.data, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response(
                    {'error': 'Clinical name creation failed', 'details': str(e)}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET':
        clinical_names = ClinicalName.objects.filter(status="APPROVED")  # Filter only approved entries
        serializer = ClinicalNameSerializer(clinical_names, many=True)
        return Response(serializer.data)
@api_view(['GET'])
def get_last_referrer_code(request):
    last_clinical = ClinicalName.objects.order_by('-referrerCode').first()
    if last_clinical:
        return JsonResponse({'referrerCode': last_clinical.referrerCode})
    return JsonResponse({'referrerCode': 'SD0000'})
@api_view(['GET'])
def download_mou_file(request, clinical_name_id):
    try:
        db, fs = get_mongodb_connection()
        # Find the file by clinical_name_id
        file_record = fs.find_one({'clinical_name_id': clinical_name_id})
        if file_record:
            file_data = file_record.read()
            response = HttpResponse(
                file_data,
                content_type=file_record.content_type
            )
            response['Content-Disposition'] = f'attachment; filename="{file_record.filename}"'
            return response
        else:
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {'error': 'File retrieval failed', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ViewSet for managing clinical names with approval workflow
class ClinicalNameViewSet(viewsets.ModelViewSet):
    queryset = ClinicalName.objects.all()
    serializer_class = ClinicalNameSerializer
    
    def get_queryset(self):
        queryset = ClinicalName.objects.all()
        status_filter = self.request.query_params.get('status', None)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset
    
    @action(detail=False, methods=['patch'], url_path='(?P<referrerCode>[^/.]+)/first_approve')
    def first_approve(self, request, referrerCode=None):
        try:
            clinical_name = get_object_or_404(ClinicalName, referrerCode=referrerCode)
            
            if clinical_name.status != 'PENDING_APPROVAL':
                return Response({"error": "This clinical name is not pending first approval."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Update approval status
            clinical_name.first_approved = True
            clinical_name.first_approved_timestamp = timezone.now()
            clinical_name.status = 'PENDING_FINAL'
            clinical_name.save()
            
            return Response(
                {"message": "First approval completed successfully", "referrerCode": clinical_name.referrerCode},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['patch'], url_path='(?P<referrerCode>[^/.]+)/final_approve')
    def final_approve(self, request, referrerCode=None):
        try:
            clinical_name = get_object_or_404(ClinicalName, referrerCode=referrerCode)
            
            if clinical_name.status != 'PENDING_FINAL':
                return Response({"error": "This clinical name is not pending final approval."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Update final approval status
            clinical_name.final_approved = True
            clinical_name.final_approved_timestamp = timezone.now()
            clinical_name.status = 'APPROVED'
            clinical_name.save()
            
            return Response(
                {"message": "Final approval completed successfully", "referrerCode": clinical_name.referrerCode},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
