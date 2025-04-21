from rest_framework.response import Response
from django.http import JsonResponse
import json
from urllib.parse import quote_plus
from pymongo import MongoClient
import certifi
from ..models import Patient
from datetime import datetime
from django.utils.timezone import make_aware
import random
from django.db.models import Q
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings  #
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
            
            # Process each patient record to filter out tests with refund=true
            for patient in result:
                if 'testname' in patient and isinstance(patient['testname'], list):
                    # Check if all tests have refund=true
                    all_refunded = all(test.get('refund', False) for test in patient['testname'])
                    
                    if all_refunded:
                        # If all tests are refunded, replace the tests with a message
                        patient['all_refunded'] = True
                        patient['testname'] = []
                    else:
                        # Filter out tests where refund=true
                        patient['all_refunded'] = False
                        patient['testname'] = [test for test in patient['testname'] if not test.get('refund', False)]
            
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

            # Get current date and time in ISO format
            current_datetime = datetime.now().isoformat()
            
            # Parse test names and update refund status and refunded_date
            test_list = json.loads(patient_record.get("testname", "[]"))
            refunded_tests = []
            
            for test in test_list:
                if test["testname"] in selected_tests:
                    test["refund"] = True
                    test["refunded_date"] = current_datetime  # Add the refunded date
                    refunded_tests.append(test["testname"])
            
            # Update only the test list with refund flags and dates
            update_data = {
                "testname": json.dumps(test_list)
            }

            patients_collection.update_one({"patient_id": patient_id}, {"$set": update_data})

            # Remove OTP after successful verification
            del otp_storage_refund[email]

            return JsonResponse({
                "message": f"Refund status updated successfully for {len(refunded_tests)} tests", 
                "refunded_tests": refunded_tests,
                "refunded_date": current_datetime
            }, status=200)

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
                # Get the testname data (handle both string and list formats)
                test_data = json.loads(patient.testname) if isinstance(patient.testname, str) else patient.testname
                
                # Check if all tests have cancellation=true
                all_cancelled = all(test.get('cancellation', False) for test in test_data)
                
                # Create patient dictionary with appropriate data
                patient_dict = {
                    'patient_id': patient.patient_id,
                    'patientname': patient.patientname,
                    'date': patient.date,
                    'all_cancelled': all_cancelled,
                }
                
                if all_cancelled:
                    # If all tests are cancelled, just keep the flag and empty test list
                    patient_dict['testname'] = []
                else:
                    # Filter out tests where cancellation=true
                    patient_dict['testname'] = [test for test in test_data if not test.get('cancellation', False)]
                
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
            
            # Get current date and time in ISO format for cancelled_date
            current_datetime = datetime.now().isoformat()

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
            refund_amount = 0
            cancelled_tests = []
            
            # Update the cancellation status for selected tests and add cancelled_date
            for test in test_list:
                if test["testname"] in selected_tests:
                    test["cancellation"] = True
                    test["cancelled_date"] = current_datetime  # Add the cancelled date
                    refund_amount += test["amount"]
                    cancelled_tests.append(test["testname"])
            
            # If no tests were found for cancellation
            if refund_amount == 0:
                return JsonResponse({"error": "No matching tests found for cancellation."}, status=400)
                
            # Update totalAmount and credit_amount if applicable
            updated_total = int(patient_record["totalAmount"]) - refund_amount
            updated_credit_amount = int(patient_record.get("credit_amount", "0")) - refund_amount if "credit_amount" in patient_record else 0

            # Prepare update data
            update_data = {
                "testname": json.dumps(test_list),
                "totalAmount": str(updated_total),
            }
            if "payment_method" in patient_record and "Credit" in patient_record["payment_method"]:
                update_data["credit_amount"] = str(max(0, updated_credit_amount))

            # Update the database
            patients_collection.update_one({"patient_id": patient_id}, {"$set": update_data})

            # Remove OTP after successful verification
            del otp_storage_cancellation[email]

            return JsonResponse({
                "message": "Cancellation processed successfully", 
                "refund_amount": refund_amount,
                "cancelled_tests": cancelled_tests,
                "cancelled_date": current_datetime
            }, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)