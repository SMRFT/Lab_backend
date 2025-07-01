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
from datetime import datetime, date 
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods
import os
#auth
from ..auth.permissions import SkipPermissionsIfDisabled
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from pyauth.auth import HasRoleAndDataPermission
from dotenv import load_dotenv

load_dotenv()

@api_view(['GET'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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

@api_view(['POST'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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
            client = MongoClient(os.getenv('LAB_DB_HOST'))
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

@api_view(['GET'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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

@api_view(['POST'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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
            client = MongoClient(os.getenv('LAB_DB_HOST'))
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



@api_view(['GET'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def logs_api(request):
    """Combined API endpoint for both refund and cancellation logs"""
    try:
        password = quote_plus('Smrft@2024')
        client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
        db = client.Lab
        patient_collection = db['labbackend_patient']
        
        # Get query parameters
        log_type = request.GET.get('type', 'refund')  # Default to refund if not specified
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base query - default to current date if no dates provided
        query = {}
        
        # Apply date filters
        if start_date or end_date:
            query['date'] = {}
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                query['date']['$gte'] = start_date
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                # Add 1 day to end_date to include the full day
                end_date = end_date.replace(hour=23, minute=59, second=59)
                query['date']['$lte'] = end_date
        else:
            # Default to current date if no dates provided
            today = datetime.now()
            today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today.replace(hour=23, minute=59, second=59, microsecond=999999)
            query['date'] = {'$gte': today_start, '$lte': today_end}
        
        # Additional optimization: Only fetch patients with refunded or cancelled tests
        if log_type == 'refund':
            # Add an additional filter to only fetch patients with refunded tests
            # Assuming testname is stored as a string that we can do basic text matching on
            query['testname'] = {'$regex': '"refund"\\s*:\\s*true', '$options': 'i'}
        elif log_type == 'cancellation':
            # Similar for cancellation
            query['testname'] = {'$regex': '"cancellation"\\s*:\\s*true', '$options': 'i'}
        
        patients = list(patient_collection.find(query))
        results = []
        
        if log_type == 'refund':
            # Process refund logs
            for patient in patients:
                try:
                    # Parse the testname JSON string
                    tests = json.loads(patient.get('testname', '[]'))
                    # Filter tests that have refund=true
                    refundable_tests = [test for test in tests if test.get('refund') is True]
                    
                    # If there are refundable tests, add to results
                    if refundable_tests:
                        # Calculate total refund amount for this patient
                        total_refund_amount = sum(float(test.get('amount', 0)) for test in refundable_tests)
                        
                        # List all refunded test names and their individual amounts
                        refunded_test_details = [f"{test.get('testname', 'Unknown Test')} (₹{float(test.get('amount', 0)):.2f})" 
                                               for test in refundable_tests]
                        
                        results.append({
                            'id': str(patient.get('_id')),
                            'patient_id': patient.get('patient_id'),
                            'patientname': patient.get('patientname'),
                            'bill_no': patient.get('bill_no'),
                            'date': patient.get('date').isoformat() if isinstance(patient.get('date'), datetime) else str(patient.get('date')),
                            'testname': ", ".join(refunded_test_details),
                            'refund_amount': total_refund_amount,
                            'refunded_tests': refundable_tests,  # Include full test objects for detailed info
                            'refund_count': len(refundable_tests),  # Add count of refunded tests
                            'reason': patient.get('refund_reason', 'Test Refunded')  # Try to get specific reason if available
                        })
                except (json.JSONDecodeError, AttributeError, KeyError) as e:
                    # Skip if there's an error parsing the testname JSON
                    print(f"Error processing patient {patient.get('_id')}: {str(e)}")
                    continue
        elif log_type == 'cancellation':
            # Process cancellation logs
            for patient in patients:
                try:
                    # Parse the testname JSON string
                    tests = json.loads(patient.get('testname', '[]'))
                    # Filter tests that are cancelled
                    cancelled_tests = [test for test in tests if test.get('cancellation') is True]
                    
                    # If there are cancelled tests, add to results
                    if cancelled_tests:
                        # Calculate total cancelled amount
                        total_cancelled_amount = sum(float(test.get('amount', 0)) for test in cancelled_tests)
                        
                        # List all cancelled test names with their individual amounts
                        cancelled_test_details = [f"{test.get('testname', 'Unknown Test')} (₹{float(test.get('amount', 0)):.2f})" 
                                               for test in cancelled_tests]
                        
                        results.append({
                            'id': str(patient.get('_id')),
                            'patient_id': patient.get('patient_id'),
                            'patientname': patient.get('patientname'),
                            'bill_no': patient.get('bill_no'),
                            'date': patient.get('date').isoformat() if isinstance(patient.get('date'), datetime) else str(patient.get('date')),
                            'testname': ", ".join(cancelled_test_details),
                            'refund_amount': total_cancelled_amount,
                            'cancelled_tests': cancelled_tests,  # Include full test objects for detailed info
                            'cancel_count': len(cancelled_tests),  # Add count of cancelled tests
                            'reason': patient.get('cancellation_reason', 'Test Cancelled')  # Try to get specific reason if available
                        })
                except (json.JSONDecodeError, AttributeError, KeyError) as e:
                    # Skip if there's an error parsing the testname JSON
                    print(f"Error processing patient {patient.get('_id')}: {str(e)}")
                    continue
        
        return JsonResponse(results, safe=False)
    except Exception as e:
        print(f"Error in logs_api: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
    



@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def dashboard_data(request):
    try:
        # Get date range and payment method from request parameters
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        payment_method = request.GET.get('payment_method')
        # Set default to current date if no dates provided
        if not from_date and not to_date:
            today = date.today()
            from_date = today.strftime('%Y-%m-%d')
            to_date = today.strftime('%Y-%m-%d')
        # Convert to datetime objects with timezone handling
        if from_date:
            from_date = datetime.strptime(from_date, '%Y-%m-%d')
        if to_date:
            # Set to end of day for inclusive filtering
            to_date = datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        # MongoDB connection
        password = quote_plus('Smrft@2024')
        client = MongoClient(os.getenv('LAB_DB_HOST'))
        db = client.Lab
        collection = db.labbackend_patient
        # Build the query for date filtering
        query = {}
        if from_date and to_date:
            query['date'] = {'$gte': from_date, '$lte': to_date}
        elif from_date:
            query['date'] = {'$gte': from_date}
        elif to_date:
            query['date'] = {'$lte': to_date}
        # Add payment method filtering if specified
        if payment_method:
            if payment_method == "PartialPayment":
                query['payment_method'] = {'$regex': 'PartialPayment', '$options': 'i'}
            else:
                # Check both direct payment_method and method inside PartialPayment
                query['$or'] = [
                    {'payment_method': {'$regex': f'"paymentmethod":"{payment_method}"', '$options': 'i'}},
                    {'PartialPayment': {'$regex': f'"method":"{payment_method}"', '$options': 'i'}}
                ]
        # Execute the query to get filtered patients
        patients = list(collection.find(query))
        # Process the data for dashboard
        total_patients = len(patients)
        total_revenue = 0
        # Payment method statistics
        payment_methods = {
            'Cash': 0,
            'Card': 0,
            'UPI': 0,
            'Credit': 0,
            'PartialPayment': 0
        }
        # Track revenue by payment method
        payment_method_amounts = {
            'Cash': 0,
            'Card': 0,
            'UPI': 0,
            'Credit': 0,
            'PartialPayment': 0
        }
        # Segment statistics
        segments = {
            'B2B': 0,
            'Walk-in': 0,
            'Home Collection': 0
        }
        # B2B client statistics
        b2b_clients = {}
        # Credit statistics
        total_credit = 0
        credit_paid = 0
        credit_pending = 0
        # Safe get method for handling potential string or None values
        def safe_get(obj, key, default=None):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return default
        # Helper function to parse JSON strings
        def parse_json(json_str, default=None):
            if not json_str:
                return default
            if isinstance(json_str, dict):
                return json_str
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return default
        # Process each patient
        for patient in patients:
            # Process total amount
            try:
                total_amount = float(safe_get(patient, 'totalAmount', 0))
                total_revenue += total_amount
            except (ValueError, TypeError):
                pass
            # Extract payment information
            payment_info = parse_json(safe_get(patient, 'payment_method'), {'paymentmethod': ''})
            patient_payment_method = safe_get(payment_info, 'paymentmethod', '')
            # Handle partial payments
            if patient_payment_method == 'PartialPayment':
                partial_payment_info = parse_json(safe_get(patient, 'PartialPayment'), {})
                actual_method = safe_get(partial_payment_info, 'method', '')
                # Record the partial payment for display in the dashboard
                payment_methods['PartialPayment'] += 1
                if actual_method and actual_method in payment_methods:
                    try:
                        # Calculate paid amount and credit amount
                        total_amount = float(safe_get(patient, 'totalAmount', 0))
                        credit_amount = float(safe_get(partial_payment_info, 'credit', 0))
                        paid_amount = total_amount - credit_amount
                        # Add paid amount to the actual payment method
                        payment_method_amounts[actual_method] += paid_amount
                        # Add credit amount to the 'Credit' category
                        payment_method_amounts['Credit'] += credit_amount
                        # Record total amount under PartialPayment for accurate statistics
                        payment_method_amounts['PartialPayment'] += total_amount
                    except (ValueError, TypeError):
                        pass
            elif patient_payment_method and patient_payment_method in payment_methods:
                payment_methods[patient_payment_method] += 1
                # Add amount to payment method total
                try:
                    payment_amount = float(safe_get(patient, 'totalAmount', 0))
                    payment_method_amounts[patient_payment_method] += payment_amount
                except (ValueError, TypeError):
                    pass
            # Process segment
            segment = safe_get(patient, 'segment', '')
            if segment and segment in segments:
                segments[segment] += 1
            # Process B2B clients
            if segment == 'B2B':
                b2b_name = safe_get(patient, 'B2B', '')
                if b2b_name:
                    b2b_clients[b2b_name] = b2b_clients.get(b2b_name, 0) + 1
            # Process credit information - from both direct credit and partial payments
            try:
                # Direct credit amount
                credit_amount = float(safe_get(patient, 'credit_amount', 0))
                # Add credit from partial payments if not already included
                if not credit_amount and patient_payment_method == 'PartialPayment':
                    partial_payment_info = parse_json(safe_get(patient, 'PartialPayment'), {})
                    partial_credit = float(safe_get(partial_payment_info, 'credit', 0))
                    credit_amount += partial_credit
                total_credit += credit_amount
            except (ValueError, TypeError):
                pass
            # Process credit details for paid amounts
            credit_details = parse_json(safe_get(patient, 'credit_details'), [])
            if isinstance(credit_details, list):
                for detail in credit_details:
                    if isinstance(detail, dict):
                        try:
                            amount_paid = float(safe_get(detail, 'amount_paid', 0))
                            credit_paid += amount_paid
                        except (ValueError, TypeError):
                            pass
        credit_pending = total_credit - credit_paid
        # Prepare payment method statistics for the filtered view
        filtered_payment_stats = {}
        if payment_method:
            filtered_payment_stats = {
                'count': 0,
                'amount': 0
            }
            # Count patients with the specified payment method (including partial payments)
            for patient in patients:
                payment_info = parse_json(safe_get(patient, 'payment_method'), {'paymentmethod': ''})
                patient_payment_method = safe_get(payment_info, 'paymentmethod', '')
                is_matching = False
                if patient_payment_method == payment_method:
                    is_matching = True
                elif patient_payment_method == 'PartialPayment':
                    partial_payment_info = parse_json(safe_get(patient, 'PartialPayment'), {})
                    actual_method = safe_get(partial_payment_info, 'method', '')
                    if actual_method == payment_method:
                        is_matching = True
                if is_matching:
                    filtered_payment_stats['count'] += 1
                    try:
                        filtered_payment_stats['amount'] += float(safe_get(patient, 'totalAmount', 0))
                    except (ValueError, TypeError):
                        pass
        # Prepare response data
        response_data = {
            'total_patients': total_patients,
            'total_revenue': round(total_revenue, 2),
            'payment_methods': payment_methods,
            'payment_method_amounts': {k: round(v, 2) for k, v in payment_method_amounts.items()},
            'segments': segments,
            'b2b_clients': dict(sorted(b2b_clients.items(), key=lambda x: x[1], reverse=True)),
            'credit_statistics': {
                'total_credit': round(total_credit, 2),
                'credit_paid': round(credit_paid, 2),
                'credit_pending': round(credit_pending, 2)
            }
        }
        if payment_method:
            response_data['filtered_payment_stats'] = {
                'count': filtered_payment_stats['count'],
                'amount': round(filtered_payment_stats['amount'], 2)
            }
        return JsonResponse({
            'success': True,
            'data': response_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
