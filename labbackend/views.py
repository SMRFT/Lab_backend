from rest_framework.response import Response
from django.http import JsonResponse , HttpResponse
from datetime import datetime
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework import  status
from urllib.parse import quote_plus
from pymongo import MongoClient

from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from django.utils import timezone  # Import Django's timezone module
import re
from django.core.mail import EmailMessage
from django.conf import settings  # To access the settings for DEFAULT_FROM_EMAIL
  # Import your model
from django.utils.timezone import make_aware
from datetime import datetime, date  # Import `date` separately
import pytz
from rest_framework.views import APIView
import traceback
from django.conf import settings  # To access the settings for DEFAULT_FROM_EMAIL
import json
import certifi
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from pyauth.auth import HasRoleAndDataPermission
from .auth.permissions import SkipPermissionsIfDisabled
#Models
from .models import Patient
from .models import SampleStatus
from .models import TestValue
from .models import SampleStatus
from .models import BarcodeTestDetails

#Serializer
from .serializers import SampleStatusSerializer
from .serializers import TestValueSerializer

import os
from dotenv import load_dotenv
load_dotenv()






@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@csrf_exempt  # Allow GET, POST, and PATCH requests without CSRF protection
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_test_details(request):
    try:
        # Securely encode password
        # MongoDB connection with TLS certificate
        client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
        db = client.Lab  # Database name
        collection = db.labbackend_testdetails  # Collection name
        if request.method == 'GET':
            # Retrieve only documents with status "Approved"
            approved_tests = list(collection.find({"status": "Approved"}, {'_id': 0}))
            return JsonResponse(approved_tests, safe=False, status=200)
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
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def send_approval_email(request):
    if request.method == 'POST':
        try:
            print("Received approval email request")
            # Parse JSON request data
            try:
                data = json.loads(request.body.decode('utf-8'))
                test_name = data.get('test_name')
                recipient_email = data.get('recipient_email')
                print(f"Test name from request: {test_name}")
                print(f"Recipient email from request: {recipient_email}")
                if not test_name:
                    print("Error: Test name is missing")
                    return JsonResponse({'error': 'Test name is required'}, status=400)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            # Connect to MongoDB to verify the test exists
            try:
                password = quote_plus('Smrft@2024')
                client = MongoClient(os.getenv('LAB_DB_HOST'))
                db = client.Lab
                collection = db.labbackend_testdetails
                # Check if test exists and get all test details
                test = collection.find_one({'test_name': test_name})
                if not test:
                    print(f"Test not found: {test_name}")
                    return JsonResponse({'error': 'Test not found'}, status=404)
                # Convert ObjectId to string for JSON serialization if needed
                if '_id' in test:
                    test['_id'] = str(test['_id'])
                print(f"Test found: {test_name}")
            except Exception as mongo_err:
                print(f"MongoDB connection error: {mongo_err}")
                return JsonResponse({'error': f'Database error: {str(mongo_err)}'}, status=500)
            # Generate approval URL
            base_url = request.build_absolute_uri('/').rstrip('/')
            approval_url = f"{base_url}/approve_test/?test_name={test_name}"
            print(f"Generated approval URL: {approval_url}")
            # For local development, override the URL if needed
            if '127.0.0.1' in base_url or 'localhost' in base_url:
                base_url = 'http://127.0.0.1:1305'
            else:
                base_url = 'https://shinova.in1.cloudlets.co.in'

            approval_url = f"{base_url}/approve_test/?test_name={test_name}"

            # Format test details for email
            test_details_str = ""
            for key, value in test.items():
                if key != '_id' and key != 'parameters':
                    test_details_str += f"{key.replace('_', ' ').title()}: {value}\n"
            # Handle parameters separately if they exist and are in JSON format
            if 'parameters' in test:
                try:
                    parameters = json.loads(test['parameters']) if isinstance(test['parameters'], str) else test['parameters']
                    if parameters:
                        test_details_str += "\nParameters:\n"
                        for i, param in enumerate(parameters, 1):
                            test_details_str += f"  Parameter {i}:\n"
                            for param_key, param_value in param.items():
                                test_details_str += f"    {param_key.replace('_', ' ').title()}: {param_value}\n"
                except (json.JSONDecodeError, TypeError):
                    test_details_str += f"\nParameters: {test.get('parameters', 'Not available')}\n"
            # Compose email with HTML for better formatting and button
            subject = f'Approval Request: Test {test_name}'
            # HTML email template with direct approval button - improved for spam prevention
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Test Approval Request</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; color: #333333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                    .header {{ background-color: #F5F5F5; padding: 10px; border-radius: 5px; margin-bottom: 20px; }}
                    .test-details {{ white-space: pre-line; margin-bottom: 20px; }}
                    .button {{ display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white;
                               text-decoration: none; border-radius: 5px; font-weight: bold; }}
                    .footer {{ font-size: 12px; color: #666; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 10px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Lab Test Approval Request</h2>
                    </div>
                    <p>Hello,</p>
                    <p>A new lab test has been submitted and requires your approval. Here are the details:</p>
                    <div class="test-details">
                        {test_details_str}
                    </div>
                    <p>To approve this test, please click the button below:</p>
                    <p><a href="{approval_url}" class="button">Approve Test</a></p>
                    <div class="footer">
                        <p>This is an automated message from Shanmuga Diagnostics Laboratory System. If you did not request this approval, please ignore this email.</p>
                        <p>© 2025 Shanmuga Diagnostics. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            # Plain text version for email clients that don't support HTML
            plain_message = f"""
            Lab Test Approval Request
            Hello,
            A new lab test has been submitted and requires your approval. Here are the details:
            {test_details_str}
            To approve this test, please click on the following link:
            {approval_url}
            This is an automated message from Shanmuga Diagnostics System. If you did not request this approval, please ignore this email.
            © 2025 Shanmuga Diagnostics. All rights reserved.
            """
            # Create the recipient list
            # Use provided email if available, otherwise use default
            recipient_list = []
            if recipient_email:
                recipient_list.append(recipient_email)

            # Always include default emails
            default_emails = ['drprabusankar@smrft.org', 'drpriya@smrft.org']
            for email in default_emails:
                if email not in recipient_list:
                    recipient_list.append(email)

            # Send email using smtplib directly for more control
            try:
                print(f"Sending email to: {recipient_list}")
                import smtplib
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText
                from email.utils import formatdate, make_msgid
                # Set up the SMTP server
                smtp_server = "smtp.gmail.com"
                smtp_port = 587
                smtp_username = settings.EMAIL_HOST_USER
                smtp_password = settings.EMAIL_HOST_PASSWORD  # Make sure this is an app password if using Gmail
                # Create message container
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = f"Shanmuga Diagnostics<{smtp_username}>"
                msg['To'] = ", ".join(recipient_list)
                msg['Date'] = formatdate(localtime=True)
                msg['Message-ID'] = make_msgid(domain='shinovadatabase.in')
                # Add custom headers to reduce chance of being marked as spam
                msg.add_header('X-Priority', '1')  # 1 = High priority
                msg.add_header('X-MSMail-Priority', 'High')
                msg.add_header('Importance', 'High')
                msg.add_header('X-Mailer', 'Shanmuga Diagnostics Approval System')
                # Record-Route might help with deliverability
                msg.add_header('Return-Path', smtp_username)
                # Attach parts
                part1 = MIMEText(plain_message, 'plain')
                part2 = MIMEText(html_message, 'html')
                msg.attach(part1)
                msg.attach(part2)
                # Create SMTP session
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_username, smtp_password)
                # Send email
                server.sendmail(smtp_username, recipient_list, msg.as_string())
                server.quit()
                print("Email sent successfully using direct SMTP")
                return JsonResponse({'message': 'Approval email sent successfully'}, status=200)
            except Exception as email_err:
                print(f"Email sending error: {email_err}")
                return JsonResponse({'error': f'Email sending failed: {str(email_err)}'}, status=500)
        except Exception as e:
            print(f"General error sending approval email: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    print("Invalid request method for send_approval_email")
    return JsonResponse({'error': 'Invalid request method'}, status=405)


# For handling test approval
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def approve_test(request):
    if request.method == 'PATCH':
        try:
            data = json.loads(request.body.decode('utf-8'))
            test_name = data.get('test_name')
           
            if not test_name:
                return JsonResponse({'error': 'Test name is required'}, status=400)
           
            # Connect to MongoDB
            password = quote_plus('Smrft@2024')
            client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
            db = client.Lab
            collection = db.labbackend_testdetails
           
            # Update test status to "Approved"
            result = collection.update_one(
                {'test_name': test_name},
                {'$set': {'status': 'Approved'}}
            )
           
            if result.modified_count > 0:
                return JsonResponse({'message': 'Test approved successfully'}, status=200)
            else:
                return JsonResponse({'error': 'Test not found or already approved'}, status=404)
               
        except Exception as e:
            print(f"Error approving test: {e}")
            return JsonResponse({'error': str(e)}, status=500)
   
    # For GET requests with test_name as query parameter (from email link)
    elif request.method == 'GET':
        try:
            # Get test_name from query parameters
            test_name = request.GET.get('test_name')
           
            if not test_name:
                return JsonResponse({'error': 'Test name is required'}, status=400)
           
            # Connect to MongoDB
            
            client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
            db = client.Lab
            collection = db.labbackend_testdetails
           
            # Find and update the test with matching name
            result = collection.update_one(
                {'test_name': test_name},
                {'$set': {'status': 'Approved'}}
            )
           
            if result.modified_count > 0:
                # Return a simple HTML response confirming approval
                html_response = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Test Approval Confirmation</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; text-align: center; background-color: #f5f5f5; }
                        .container { max-width: 600px; margin: 0 auto; padding: 30px; background-color: white;
                                    border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
                        .success { color: #4caf50; font-size: 28px; margin-bottom: 20px; }
                        .icon { font-size: 50px; color: #4caf50; margin-bottom: 20px; }
                        .button { display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white;
                                text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">✓</div>
                        <div class="success">Test Approved Successfully</div>
                        <p>The test has been approved and is now active in the system.</p>
                        <p>Test Name: <strong>""" + test_name + """</strong></p>
                        <p>Status: <strong>Approved</strong></p>
                        <p>You can close this window.</p>
                    </div>
                </body>
                </html>
                """
                return HttpResponse(html_response, content_type='text/html')
            else:
                html_error = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Test Approval Error</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; text-align: center; background-color: #f5f5f5; }
                        .container { max-width: 600px; margin: 0 auto; padding: 30px; background-color: white;
                                    border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
                        .error { color: #f44336; font-size: 28px; margin-bottom: 20px; }
                        .icon { font-size: 50px; color: #f44336; margin-bottom: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">✗</div>
                        <div class="error">Approval Failed</div>
                        <p>The test was not found or has already been approved.</p>
                        <p>Test Name: <strong>""" + test_name + """</strong></p>
                        <p>Please contact the administrator for assistance.</p>
                    </div>
                </body>
                </html>
                """
                return HttpResponse(html_error, content_type='text/html', status=404)
        except Exception as e:
            print(f"Error processing approval: {e}")
            return JsonResponse({'error': str(e)}, status=500)
   
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def handle_patch_request(request):
    try:
        # MongoDB connection setup inside the function
        password = quote_plus('Smrft@2024')
        # MongoDB connection with TLS certificate
        client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
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

@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_test_parameters(request, test_name):
    try:        
        client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
        db = client.Lab  # Database name
        collection = db.labbackend_testdetails  # Collection name
        # Fetch the test details based on the test_name
        test = collection.find_one({"test_name": test_name}, {"_id": 0, "parameters": 1})  # Assuming parameters is a field in your document
        if test:
            return JsonResponse({"parameters": test.get("parameters", [])}, status=200)
        else:
            return JsonResponse({"error": "Test not found"}, status=404)
    except Exception as e:
        print("Error fetching parameters:", e)
        return JsonResponse({"error": "Failed to fetch parameters"}, status=500)

    


@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([HasRoleAndDataPermission])
def compare_test_details(request):
    # MongoDB connection setup
    #password = quote_plus('Smrft@2024')
        # MongoDB connection with TLS certificate
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
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

@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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


@api_view(['GET', 'POST','PATCH'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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
            verified_by = payload.get('verified_by')
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
                    'verified_by': verified_by,
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
        client = MongoClient(os.getenv('LAB_DB_HOST'))
        db = client.Lab
        collection = db.labbackend_testvalue
        patient_id = request.data.get("patient_id")
        date_str = request.data.get("date")
        test_details_json = request.data.get("testdetails", [])
        if not patient_id or not date_str:
            return Response({"error": "patient_id and date are required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            test_value_record = collection.find_one({"patient_id": patient_id, "date": date})
            if not test_value_record:
                return Response({"error": "No record found for the given patient and date"}, status=status.HTTP_404_NOT_FOUND)
            existing_test_details = test_value_record.get("testdetails", [])
            if isinstance(existing_test_details, str):
                existing_test_details = json.loads(existing_test_details)
            for new_test in test_details_json:
                testname = new_test["testname"]
                existing_test = next((t for t in existing_test_details if t["testname"] == testname), None)
                if existing_test:
                    # Set remarks and rerun on test level
                    existing_test["remarks"] = new_test.get("remarks", existing_test.get("remarks", ""))
                    existing_test["rerun"] = False  # Always false when edited
                    if "parameters" in new_test and new_test["parameters"]:
                        for new_param in new_test["parameters"]:
                            param_name = new_param["name"]
                            existing_param = next(
                                (p for p in existing_test.get("parameters", []) if p["name"] == param_name), None
                            )
                            if existing_param:
                                existing_param["value"] = new_param["value"]
                            else:
                                existing_test.setdefault("parameters", []).append(new_param)
                    else:
                        existing_test["value"] = new_test.get("value", existing_test.get("value", ""))
                        existing_test["unit"] = new_test.get("unit", existing_test.get("unit", "N/A"))
                        existing_test["reference_range"] = new_test.get("reference_range", existing_test.get("reference_range", "N/A"))
                        existing_test["specimen_type"] = new_test.get("specimen_type", existing_test.get("specimen_type", "N/A"))
                        existing_test["remarks"] = new_test.get("remarks", existing_test.get("remarks", ""))
                        existing_test["rerun"] = False
                else:
                    # New test — add to list
                    new_test["rerun"] = False
                    existing_test_details.append(new_test)
            collection.update_one(
                {"patient_id": patient_id, "date": date},
                {"$set": {"testdetails": json.dumps(existing_test_details)}}  # Or remove json.dumps if Mongo stores natively
            )
            return Response({"message": "Test details updated successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
@api_view(['PATCH'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def update_test_value(request):
    # MongoDB connection
    #password = quote_plus('Smrft@2024')
    # MongoDB connection with TLS certificate
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
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




# Define IST timezone
TIME_ZONE = 'Asia/Kolkata'
IST = pytz.timezone(TIME_ZONE)

@api_view(['PATCH'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def update_dispatch_status(request, patient_id):
    # MongoDB connection
    password = quote_plus('Smrft@2024')

    # MongoDB connection with TLS certificate
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))

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

@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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


@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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


@api_view(["PATCH"])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def approve_test_detail(request, patient_id, test_index):
    # MongoDB connection
    password = quote_plus('Smrft@2024')
    # MongoDB connection with TLS certificate
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
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
    
@api_view(['PATCH'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def rerun_test_detail(request, patient_id, test_index):
    # MongoDB connection
    password = quote_plus('Smrft@2024')
        # MongoDB connection with TLS certificate
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
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
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def update_test_detail(request, patient_id):
    # MongoDB connection
    password = quote_plus('Smrft@2024')

        # MongoDB connection with TLS certificate
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))

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



@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_patient_test_details(request):
    patient_id = request.GET.get('patient_id')
    if not patient_id:
        return JsonResponse({'error': 'Patient ID is required'}, status=400)
    try:
        test_values = TestValue.objects.filter(patient_id=patient_id)
        sample_status = SampleStatus.objects.filter(patient_id=patient_id)
        barcode_details = BarcodeTestDetails.objects.filter(patient_id=patient_id).first()
        patient = Patient.objects.filter(patient_id=patient_id).first()
        if not test_values:
            return JsonResponse({'error': 'Test values not found for the given patient ID'}, status=404)
        barcodes = []
        if barcode_details:
            try:
                tests = json.loads(barcode_details.tests) if isinstance(barcode_details.tests, str) else barcode_details.tests
                barcodes = [test.get("barcode") for test in tests if test.get("barcode")]
            except json.JSONDecodeError:
                barcodes = []
        patient_details = {
            "patient_id": test_values[0].patient_id,
            "patientname": test_values[0].patientname,
            "age": test_values[0].age,
            "date": test_values[0].date,
            "barcodes": barcodes,
            "testdetails": [],
            "gender": patient.gender if patient else "N/A",
            "refby": patient.refby if patient else "N/A",
            "B2B": patient.B2B,
            "branch": patient.branch,
            "verified_by": test_values[0].verified_by,
        }
        for test in test_values[0].testdetails:
            testname = test.get("testname")
            department = test.get("department", "N/A")
            parameters = test.get("parameters", [])
            status = next(
                (status for status in sample_status[0].testdetails if status.get("testname") == testname), None)
            samplecollected_time = status.get("samplecollected_time") if status else None
            received_time = status.get("received_time") if status else None
            test_detail = {
                "department": department,
                "testname": testname,
                "samplecollected_time": samplecollected_time,
                "received_time": received_time
            }
            if parameters:
                test_detail["parameters"] = parameters
            else:
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
  
@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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
from pymongo import MongoClient
from datetime import datetime, timedelta
import os, json, traceback
from django.utils.timezone import make_aware
from .models import SampleStatus, TestValue

@api_view(['GET','PATCH'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def overall_report(request):
    try:
        # MongoDB setup
        client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
        db = client.Lab
        patients_collection = db["labbackend_patient"]

        # Date filters
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")
        patient_id = request.GET.get("patient_id")

        try:
            if from_date:
                from_date = datetime.strptime(from_date, "%Y-%m-%d")
            if to_date:
                to_date = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        # Build MongoDB query
        query = {}
        if patient_id:
            query["patient_id"] = patient_id
        if from_date and to_date:
            query["date"] = {"$gte": from_date, "$lt": to_date}

        patients = list(patients_collection.find(query))
        if not patients:
            return JsonResponse([], safe=False)

        patient_ids = [p.get("patient_id") for p in patients if p.get("patient_id")]

        # Status data: bulk fetch from SQL DBs
        from_datetime = make_aware(from_date or datetime.now())
        to_datetime = make_aware((to_date - timedelta(days=1)) if to_date else datetime.now().replace(hour=23, minute=59, second=59))

        sample_status_records = SampleStatus.objects.filter(
            patient_id__in=patient_ids,
            date__range=(from_datetime, to_datetime)
        ).values("patient_id", "testdetails")

        test_value_records = TestValue.objects.filter(
            patient_id__in=patient_ids,
            date__range=(from_datetime, to_datetime)
        ).values("patient_id", "barcode", "testdetails")

        # Organize status data
        sample_status_map = {}
        for record in sample_status_records:
            sample_status_map.setdefault(record["patient_id"], []).extend(record["testdetails"])

        test_value_map = {}
        for record in test_value_records:
            pid = record["patient_id"]
            test_value_map.setdefault(pid, {"barcode": record["barcode"], "testdetails": []})
            test_value_map[pid]["testdetails"].extend(record["testdetails"])

        # Final result
        formatted_data = []

        for patient in patients:
            pid = patient.get("patient_id", "N/A")

            # Payment method parsing - UPDATED TO RETURN COMPLETE DETAILS
            payment_details = {}
            raw = patient.get("payment_method", "")
            
            if raw:
                if isinstance(raw, dict):
                    payment_details = raw
                elif isinstance(raw, str):
                    try:
                        cleaned = raw.strip('"')
                        payment_data = json.loads(cleaned) if cleaned else {}
                        if isinstance(payment_data, dict):
                            payment_details = payment_data
                        else:
                            payment_details = {"paymentmethod": str(payment_data)}
                    except:
                        payment_details = {"paymentmethod": raw}
            else:
                payment_details = {"paymentmethod": "N/A"}

            # Partial payment handling - UPDATED
            if payment_details.get("paymentmethod") == "PartialPayment":
                partial_data = patient.get("PartialPayment", "")
                try:
                    if isinstance(partial_data, str):
                        partial_data = json.loads(partial_data.strip('"')) if partial_data.strip('"') else {}
                    if isinstance(partial_data, dict):
                        # Merge partial payment details with existing payment details
                        payment_details.update(partial_data)
                        payment_details["paymentmethod"] = "PartialPayment"
                except:
                    pass

            # Test list
            test_list = []
            test_field = patient.get("testname", [])
            if isinstance(test_field, str):
                try:
                    test_list = json.loads(test_field)
                except:
                    test_list = []
            elif isinstance(test_field, list):
                test_list = test_field
            testnames = ", ".join([test.get("testname", "") for test in test_list])
            no_of_tests = len(test_list)

            # Age
            age = f"{patient.get('age', 'N/A')} {patient.get('age_type', '')}"
            discount = int(patient.get('discount', 0) or 0)

            # Amounts
            try:
                total_amount = int(float(patient.get("totalAmount", 0) or 0))
            except:
                total_amount = 0
            try:
                credit_amount = int(float(patient.get("credit_amount", 0) or 0))
            except:
                credit_amount = 0

            credit_details = []
            if isinstance(patient.get("credit_details"), str):
                try:
                    credit_details = json.loads(patient["credit_details"])
                except:
                    pass
            elif isinstance(patient.get("credit_details"), list):
                credit_details = patient["credit_details"]

            # Status determination
            barcode = None
            status = "Registered"
            sample_tests = sample_status_map.get(pid, [])
            test_values = test_value_map.get(pid, {}).get("testdetails", [])
            barcode = test_value_map.get(pid, {}).get("barcode")

            all_collected = all(t.get("samplestatus") == "Sample Collected" for t in sample_tests) if sample_tests else False
            partially_collected = any(t.get("samplestatus") == "Sample Collected" for t in sample_tests)
            all_received = all(t.get("samplestatus") == "Received" for t in sample_tests) if sample_tests else False
            partially_received = any(t.get("samplestatus") == "Received" for t in sample_tests)

            if all_collected:
                status = "Collected"
            elif partially_collected:
                status = "Partially Collected"
            if all_received:
                status = "Received"
            elif partially_received:
                status = "Partially Received"

            if test_values:
                all_tested = all(t.get("value") is not None for t in test_values)
                partially_tested = any(t.get("value") is not None for t in test_values)
                approve_all = all(t.get("approve") for t in test_values)
                approve_partial = any(t.get("approve") for t in test_values)
                dispatch_all = all(t.get("dispatch") for t in test_values)

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

            # Final patient object - UPDATED TO INCLUDE COMPLETE PAYMENT DETAILS
            formatted_data.append({
                "date": patient.get("date").strftime("%Y-%m-%d") if "date" in patient else "N/A",
                "patient_id": pid,
                "patient_name": patient.get("patientname", "N/A"),
                "gender": patient.get("gender", "N/A"),
                "refby": patient.get("refby", "N/A"),
                "age": age,
                "segment": patient.get("segment", "N/A"),
                "b2b": patient.get("B2B", "N/A"),
                "branch": patient.get("branch", "N/A"),
                "sample_collector": patient.get("sample_collector", "N/A"),
                "salesMapping": patient.get("salesMapping", "N/A"),
                "total_amount": total_amount,
                "credit_amount": credit_amount,
                "credit_details": credit_details,
                "discount": discount,
                "payment_method": payment_details,  # CHANGED: Now returns complete payment details object
                "test_names": testnames,
                "no_of_tests": no_of_tests,
                "bill_no": patient.get("bill_no", "N/A"),
                "registeredby": patient.get("registeredby", "N/A"),
                "barcode": barcode,
                "status": status,
            })

        return JsonResponse(formatted_data, safe=False)
    except Exception as e:
        print("Critical Error:", str(e))
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)
    
@api_view(['GET'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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
   


# Define the timezone for India Standard Time (IST)
IST = pytz.timezone('Asia/Kolkata')
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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

