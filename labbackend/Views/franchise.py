from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt
import json
from pymongo import MongoClient
from ..auth.permissions import SkipPermissionsIfDisabled
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from pyauth.auth import HasRoleAndDataPermission
from dotenv import load_dotenv
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from pymongo import MongoClient
from datetime import datetime
import json
import logging
from django.http import JsonResponse
from pymongo import MongoClient
from datetime import datetime, timedelta
import os, json, traceback
from django.utils.timezone import make_aware
from ..models import SampleStatus, TestValue

load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

@api_view(['GET'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_franchise_sample(request):
    if request.method == "GET":
        # MongoDB connection details
        mongo_url = "mongodb://admin:YSEgnm42789@103.205.141.245:27017/"
        db_name = "franchise"
        
        client = None
        try:
            # Connect to MongoDB
            client = MongoClient(mongo_url)
            db = client[db_name]
            
            # Get collections
            samples_collection = db["franchise_sample"]         
            patient_collection = db["franchise_patient"]
            
            # Fetch all documents from the collections
            samples = list(samples_collection.find())            
            patients = list(patient_collection.find())
            
            # Create lookup dictionaries for faster access          
            patient_lookup = {pat.get('patientId','barcode'): pat for pat in patients}
            
            patient_data = {}
            
            # Helper function to handle null values
            def safe_get(obj, key, default=""):
                value = obj.get(key) if obj else None
                return value if value is not None else default
            
            # Prepare the data grouped by patient
            for sample in samples:
                # Handle testdetails field
                test_details = sample.get('testdetails', [])
                
                # If testdetails is a string, try to parse it as JSON
                if isinstance(test_details, str):
                    try:
                        test_details = json.loads(test_details)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse testdetails for sample {sample.get('_id')}")
                        test_details = []
                
                # Ensure test_details is a list
                if not isinstance(test_details, list):
                    test_details = []
                
                # Get patient_id from sample               
                patient_id = sample.get('patient_id')              
                barcode = sample.get('barcode')              
                
                # Get patient data using patient_id
                patient_data_obj = patient_lookup.get(patient_id, {})                
           
                # Extract patient name and age from patient collection
                patient_name = safe_get(patient_data_obj, 'Patientname')
                patient_age = safe_get(patient_data_obj, 'age')
                
                # Filter test details based on samplestatus only
                for detail in test_details:
                    if detail.get("samplestatus") == "Transferred":
                        
                        # If patient is not already in the dictionary, add them
                        if patient_id not in patient_data:
                            patient_data[patient_id] = {
                                "date": safe_get(sample, 'created_date'),
                                "patient_id": patient_id,
                                "patientname": patient_name,
                                "barcode": barcode,
                                "age": str(patient_age) if patient_age else "",                               
                                "locationId": safe_get(sample, 'franchise_id'),                               
                                "testdetails": []
                            }
                        
                        # Append the test details
                        patient_data[patient_id]["testdetails"].append({
                            "testname": safe_get(detail, "testname", "N/A"),
                            "container": safe_get(detail, "container", "N/A"),
                            "department": safe_get(detail, "department", "N/A"),
                            "samplecollector": safe_get(detail, "collected_by", "N/A"),
                            "samplestatus": safe_get(detail, "samplestatus", "N/A"),
                            "samplecollected_time": safe_get(detail, "samplecollected_time", "N/A"),
                        })
            
            # Convert the dictionary to a list
            data = list(patient_data.values())
            
            # Return the filtered data as a response
            return JsonResponse({"data": data}, safe=False)
            
        except Exception as e:
            logger.error(f"Error fetching data from MongoDB: {str(e)}")
            return JsonResponse({"error": f"Database connection error: {str(e)}"}, status=500)
        
        finally:
            # Close the MongoDB connection
            if client:
                client.close()

@api_view(['PUT'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def update_franchise_sample(request, patient_id):    
    client = MongoClient("mongodb://admin:YSEgnm42789@103.205.141.245:27017/")
    db = client.franchise  # Database name
    collection = db.franchise_sample  # Collection name
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


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from pymongo import MongoClient
from bson import ObjectId
import json
import logging
from dotenv import load_dotenv
from ..auth.permissions import SkipPermissionsIfDisabled
from pyauth.auth import HasRoleAndDataPermission

load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)



@api_view(['GET'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_batch_generation_data(request):
     # Connect to MongoDB
    client = MongoClient("mongodb://admin:YSEgnm42789@103.205.141.245:27017/")
    db = client.franchise  # Database name
    collection = db.franchise_batchgeneration  # Collection name

    """
    Get all batch generation data where received=false with optional date filtering
    """
    if request.method == "GET":
        client = None
        try:
           
            
            # Build query with date filtering
            query = {"received": False}
            
            # Get date parameters from request
            from_date = request.GET.get('from_date')
            to_date = request.GET.get('to_date')
            
            # Add date filtering if provided
            if from_date or to_date:
                date_query = {}
                
                if from_date:
                    # Parse from_date and set time to start of day (00:00:00)
                    from_datetime = datetime.strptime(from_date, '%Y-%m-%d')
                    date_query['$gte'] = from_datetime
                
                if to_date:
                    # Parse to_date and set time to end of day (23:59:59)
                    to_datetime = datetime.strptime(to_date, '%Y-%m-%d')
                    to_datetime = to_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
                    date_query['$lte'] = to_datetime
                
                # Add date filter to query
                if date_query:
                    query['createdDate'] = date_query
            
            # Log the query for debugging
            logger.info(f"MongoDB query: {query}")
            
            # Fetch documents with the built query
            batches = list(collection.find(query))
            
            # Process the data
            processed_data = []
            for batch in batches:
                # Convert ObjectId to string for JSON serialization
                batch['_id'] = str(batch['_id'])
                
                # Parse JSON strings if they exist
                if 'patientDetails' in batch and isinstance(batch['patientDetails'], str):
                    try:
                        batch['patientDetails'] = json.loads(batch['patientDetails'])
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse patientDetails for batch {batch['_id']}")
                        batch['patientDetails'] = {}
                
                if 'testDetails' in batch and isinstance(batch['testDetails'], str):
                    try:
                        batch['testDetails'] = json.loads(batch['testDetails'])
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse testDetails for batch {batch['_id']}")
                        batch['testDetails'] = []
                
                # Convert datetime objects to ISO format strings
                if 'createdDate' in batch:
                    batch['createdDate'] = batch['createdDate'].isoformat() if batch['createdDate'] else None
                if 'modifiedDate' in batch:
                    batch['modifiedDate'] = batch['modifiedDate'].isoformat() if batch['modifiedDate'] else None
                
                processed_data.append(batch)
            
            return JsonResponse({
                "status": "success",
                "data": processed_data,
                "count": len(processed_data),
                "filters": {
                    "from_date": from_date,
                    "to_date": to_date
                }
            }, safe=False)
            
        except ValueError as e:
            logger.error(f"Date parsing error: {str(e)}")
            return JsonResponse({
                "status": "error",
                "message": f"Invalid date format. Use YYYY-MM-DD format: {str(e)}"
            }, status=400)
            
        except Exception as e:
            logger.error(f"Error fetching batch generation data: {str(e)}")
            return JsonResponse({
                "status": "error",
                "message": f"Database connection error: {str(e)}"
            }, status=500)
        
        finally:
            if client:
                client.close()

@api_view(['PATCH'])
@csrf_exempt  
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def update_batch_received_status(request, batch_no):
    """
    Update the received status to true for a specific batch using batchNo
    """
    # MongoDB connection details
    client = MongoClient("mongodb://admin:YSEgnm42789@103.205.141.245:27017/")
    db = client.franchise  # Database name
    collection = db.franchise_batchgeneration  # Collection name
    
    client = None
    try:
        # Parse request body
        try:
            body = json.loads(request.body)
            received_status = body.get('received', True)
        except json.JSONDecodeError:
            received_status = True  # Default to True if no body provided        
       
        # Get current user info
        current_user = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else "System"
        
        # Update the document using batchNo
        update_data = {
            "$set": {
                "received": received_status,
                "modifiedDate": datetime.now(),  # Use actual datetime object
                "modifiedBy": current_user
            }
        }
        
        result = collection.update_one(
            {"batchNo": str(batch_no)},  # Ensure batchNo is treated as string
            update_data
        )
        
        logger.info(f"Update attempt for batch {batch_no}: matched={result.matched_count}, modified={result.modified_count}")
        
        if result.matched_count == 0:
            return JsonResponse({
                "status": "error",
                "message": f"Batch with batchNo '{batch_no}' not found"
            }, status=404)
        
        if result.modified_count == 0:
            return JsonResponse({
                "status": "info",
                "message": "Batch was already marked as received",
                "batch_no": batch_no
            }, status=200)
        
        return JsonResponse({
            "status": "success",
            "message": "Batch received status updated successfully",
            "batch_no": batch_no,
            "received": received_status
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error updating batch received status for batch {batch_no}: {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": f"Database update error: {str(e)}"
        }, status=500)
    
    finally:
        if client:
            client.close()

@api_view(['GET','PATCH'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def franchise_overall_report(request):
    try:
        # MongoDB setup
        client = MongoClient("mongodb://admin:YSEgnm42789@103.205.141.245:27017/")
        db = client.franchise  # Database name
        patients_collection = db.franchise_register  # Collection name
        sample_status_colletion = db.franchise_sample # Collection name for sample 
        franchise_patient_collection = db.franchise_patient  # Collection for patient details

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
        
        # Build MongoDB query - using created_date for consistency
        query = {}
        if patient_id:
            query["patient_id"] = patient_id
        if from_date and to_date:
            query["created_date"] = {"$gte": from_date, "$lt": to_date}
        elif from_date:
            query["created_date"] = {"$gte": from_date}
        elif to_date:
            query["created_date"] = {"$lt": to_date}
        
        patients = list(patients_collection.find(query))
        if not patients:
            return JsonResponse([], safe=False)
        
        patient_ids = [p.get("patient_id") for p in patients if p.get("patient_id")]
        
        # Get patient details from franchise_patient collection
        patient_details_map = {}
        if patient_ids:
            patient_details = franchise_patient_collection.find({"patient_id": {"$in": patient_ids}})
            for patient_detail in patient_details:
                patient_details_map[patient_detail.get("patient_id")] = patient_detail
        
        # Status data: bulk fetch from MongoDB - use created_date consistently
        sample_status_records = sample_status_colletion.find({
            "patient_id": {"$in": patient_ids}
        })

        # Convert to list and extract only needed fields - ADD NULL CHECKS
        sample_status_records = [
            {"patient_id": record.get("patient_id"), "testdetails": record.get("testdetails")}
            for record in sample_status_records
            if record and isinstance(record, dict)  # Ensure record is a dict
        ]
        
        # For TestValue objects, convert dates to datetime objects for comparison
        if from_date and to_date:
            from_datetime = make_aware(from_date)
            to_datetime = make_aware(to_date - timedelta(days=1))
            test_value_records = TestValue.objects.filter(
                patient_id__in=patient_ids,
                date__range=(from_datetime, to_datetime)
            ).values("patient_id", "barcode", "testdetails")
        else:
            test_value_records = TestValue.objects.filter(
                patient_id__in=patient_ids
            ).values("patient_id", "barcode", "testdetails")
        
        # Organize status data - ADD SAFETY CHECKS
        sample_status_map = {}
        for record in sample_status_records:
            if record and isinstance(record, dict) and record.get("testdetails"):
                patient_id_key = record.get("patient_id")
                if patient_id_key:
                    sample_status_map.setdefault(patient_id_key, []).extend(record["testdetails"])
        
        test_value_map = {}
        for record in test_value_records:
            if record and isinstance(record, dict):
                pid = record.get("patient_id")
                if pid:
                    test_value_map.setdefault(pid, {"barcode": record.get("barcode"), "testdetails": []})
                    if record.get("testdetails"):
                        test_value_map[pid]["testdetails"].extend(record["testdetails"])
        
        # Final result
        formatted_data = []
        for patient in patients:
            # SAFETY CHECK: Ensure patient is a dict
            if not isinstance(patient, dict):
                print(f"Warning: Patient record is not a dict: {type(patient)}")
                continue
                
            pid = patient.get("patient_id", "N/A")
            
            # Get patient details from franchise_patient collection
            patient_detail = patient_details_map.get(pid, {})
            # SAFETY CHECK: Ensure patient_detail is a dict
            if not isinstance(patient_detail, dict):
                patient_detail = {}
            
            # Payment method parsing - UPDATED TO RETURN COMPLETE DETAILS
            payment_details = {}
            raw = patient.get("paymentMode", "")  # Changed from payment_method to paymentMode
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
            
            # Partial payment handling - similar to first document
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
            
            # Test list - ADD SAFETY CHECKS
            test_list = []
            test_field = patient.get("testdetails", [])
            if isinstance(test_field, str):
                try:
                    test_list = json.loads(test_field)
                    if not isinstance(test_list, list):
                        test_list = []
                except:
                    test_list = []
            elif isinstance(test_field, list):
                test_list = test_field
            
            # SAFETY CHECK: Ensure test_list items are dicts
            testnames = ", ".join([
                test.get("testname", "") if isinstance(test, dict) else str(test)
                for test in test_list
            ])
            no_of_tests = len(test_list)
            
            # Age handling - similar to first document
            age_value = patient_detail.get("age", "N/A")
            age_type = patient_detail.get("age_type", "")
            age = f"{age_value} {age_type}" if age_type else str(age_value)
            
            discount = int(patient.get('discount', 0) or 0)
            
            # Amounts
            try:
                total_amount = int(float(patient.get("netAmount", 0) or 0))
            except:
                total_amount = 0
            
            try:
                credit_amount = int(float(patient.get("credit_amount", 0) or 0))
            except:
                credit_amount = 0
            
            credit_details = []
            credit_details_raw = patient.get("credit_details")
            if isinstance(credit_details_raw, str):
                try:
                    credit_details = json.loads(credit_details_raw)
                    if not isinstance(credit_details, list):
                        credit_details = []
                except:
                    credit_details = []
            elif isinstance(credit_details_raw, list):
                credit_details = credit_details_raw
            
            # Status determination
            barcode = patient.get("barcode")
            status = "Registered"
            sample_tests = sample_status_map.get(pid, [])
            test_values = test_value_map.get(pid, {}).get("testdetails", [])
            
            # Use barcode from test_value_map if available, similar to first document
            if not barcode and test_value_map.get(pid, {}).get("barcode"):
                barcode = test_value_map.get(pid, {}).get("barcode")
            
            # SAFETY CHECKS for sample_tests
            all_collected = all(
                t.get("samplestatus") == "Sample Collected" if isinstance(t, dict) else False
                for t in sample_tests
            ) if sample_tests else False
            
            partially_collected = any(
                t.get("samplestatus") == "Sample Collected" if isinstance(t, dict) else False
                for t in sample_tests
            )
            
            all_received = all(
                t.get("samplestatus") == "Received" if isinstance(t, dict) else False
                for t in sample_tests
            ) if sample_tests else False
            
            partially_received = any(
                t.get("samplestatus") == "Received" if isinstance(t, dict) else False
                for t in sample_tests
            )
            
            if all_collected:
                status = "Collected"
            elif partially_collected:
                status = "Partially Collected"
            
            if all_received:
                status = "Received"
            elif partially_received:
                status = "Partially Received"
            
            # SAFETY CHECKS for test_values
            if test_values:
                all_tested = all(
                    t.get("value") is not None if isinstance(t, dict) else False
                    for t in test_values
                )
                partially_tested = any(
                    t.get("value") is not None if isinstance(t, dict) else False
                    for t in test_values
                )
                approve_all = all(
                    t.get("approve") if isinstance(t, dict) else False
                    for t in test_values
                )
                approve_partial = any(
                    t.get("approve") if isinstance(t, dict) else False
                    for t in test_values
                )
                dispatch_all = all(
                    t.get("dispatch") if isinstance(t, dict) else False
                    for t in test_values
                )
                
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
            
            # Handle date formatting - use created_date consistently
            created_date = patient.get("created_date")
            if created_date:
                if isinstance(created_date, datetime):
                    formatted_date = created_date.strftime("%Y-%m-%d")
                else:
                    # Handle string dates
                    try:
                        parsed_date = datetime.strptime(str(created_date), "%Y-%m-%d")
                        formatted_date = parsed_date.strftime("%Y-%m-%d")
                    except:
                        formatted_date = str(created_date)
            else:
                formatted_date = "N/A"
            
            # Final patient object - matching structure with first document
            formatted_data.append({
                "date": formatted_date,
                "patient_id": pid,
                "patient_name": patient_detail.get("patientname", "N/A"),  # From franchise_patient
                "gender": patient_detail.get("gender", "N/A"),  # From franchise_patient
                "refby": patient.get("referredDoctor", "N/A"),
                "age": age,
                "email": patient_detail.get("email", "N/A"),  # From franchise_patient             
                "branch": patient.get("franchise_id", "N/A"),  # Use locationId as branch               
                "total_amount": total_amount,
                "credit_amount": credit_amount,
                "credit_details": credit_details,
                "discount": discount,
                "payment_method": payment_details,
                "test_names": testnames,
                "no_of_tests": no_of_tests,
                "bill_no": patient.get("bill_no", "N/A"),
                "registeredby": patient.get("registeredBy", "N/A"),
                "barcode": barcode,
                "status": status,
            })
        
        return JsonResponse(formatted_data, safe=False)
    
    except Exception as e:
        print("Critical Error:", str(e))
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)
    


@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def franchise_patient_test_details(request):
    patient_id = request.GET.get('patient_id')
    if not patient_id:
        return JsonResponse({'error': 'Patient ID is required'}, status=400)
    
    try:
        # MongoDB connection
        client = MongoClient("mongodb://admin:YSEgnm42789@103.205.141.245:27017/")
        db = client.franchise
        franchise_register_collection = db.franchise_register
        franchise_sample_collection = db.franchise_sample
        franchise_patient_collection = db.franchise_patient
        
        # Get franchise register data
        franchise_register = franchise_register_collection.find_one({"patient_id": patient_id})
        if not franchise_register:
            return JsonResponse({'error': 'Franchise register not found for the given patient ID'}, status=404)
        
        # Get franchise patient data
        franchise_patient = franchise_patient_collection.find_one({"patient_id": patient_id})
        if not franchise_patient:
            return JsonResponse({'error': 'Franchise patient not found for the given patient ID'}, status=404)
        
        # Get franchise sample data
        franchise_sample = franchise_sample_collection.find_one({"patient_id": patient_id})
        
        # Get test values from Django model for additional details
        test_values = TestValue.objects.filter(patient_id=patient_id)
        
        # Parse testdetails from franchise_register
        try:
            register_testdetails = json.loads(franchise_register.get('testdetails', '[]'))
        except json.JSONDecodeError:
            register_testdetails = []
        
        # Parse testdetails from franchise_sample
        sample_testdetails = []
        if franchise_sample:
            try:
                sample_testdetails = json.loads(franchise_sample.get('testdetails', '[]'))
            except json.JSONDecodeError:
                sample_testdetails = []
        
        # Build patient details response
        patient_details = {
            "patient_id": patient_id,
            "patientname": franchise_patient.get("patientname", "N/A"),
            "age": franchise_patient.get("age", "N/A"),
            "gender": franchise_patient.get("gender", "N/A"),
            "date": franchise_register.get("created_date"),
            "barcode": franchise_register.get("barcode", "N/A"),
            "refby": franchise_register.get("referredDoctor", "N/A"),
            "branch": franchise_register.get("franchise_id", "N/A"),
            "testdetails": []
        }
        
        # Process test details
        for register_test in register_testdetails:
            testname = register_test.get("testname")
            
            # Find corresponding sample status
            sample_status = None
            for sample_test in sample_testdetails:
                if sample_test.get("testname") == testname:
                    sample_status = sample_test
                    break
            
            # Find corresponding test value details
            test_value_details = None
            if test_values:
                for test_value in test_values:
                    for test_detail in test_value.testdetails:
                        if test_detail.get("testname") == testname:
                            test_value_details = test_detail
                            break
                    if test_value_details:
                        break
            
            # Build test detail object
            test_detail = {
                "testname": testname,
                "container": register_test.get("container", "N/A"),                
                "department": sample_status.get("department", "N/A") if sample_status else "N/A",
                "samplestatus": sample_status.get("samplestatus", "N/A") if sample_status else "N/A",
                "samplecollected_time": sample_status.get("samplecollected_time") if sample_status else None,
                "collected_by": sample_status.get("collected_by", "N/A") if sample_status else "N/A",
                "sampletransferred_time": sample_status.get("sampletransferred_time") if sample_status else None,
                "transferred_by": sample_status.get("transferred_by", "N/A") if sample_status else "N/A",
                "received_time": sample_status.get("received_time") if sample_status else None,
                "received_by": sample_status.get("received_by", "N/A") if sample_status else "N/A",
                "remarks": sample_status.get("remarks") if sample_status else None
            }
            
            # Add test value details if available
            if test_value_details:
                test_detail.update({
                    "verified_by": test_value_details.get("verified_by", "N/A"),
                    "method": test_value_details.get("method", "N/A"),
                    "specimen_type": test_value_details.get("specimen_type", "N/A"),
                    "value": test_value_details.get("value", "N/A"),
                    "unit": test_value_details.get("unit", "N/A"),
                    "reference_range": test_value_details.get("reference_range", "N/A"),
                    "parameters": test_value_details.get("parameters", [])
                })
            
            patient_details["testdetails"].append(test_detail)
        
        # Close MongoDB connection
        client.close()
        
        return JsonResponse(patient_details, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_test_value_for_franchise(request):
    patient_id = request.GET.get('patient_id')
    locationId = request.GET.get('franchise_id')

    if not patient_id or not locationId:
        return JsonResponse({'error': 'patient_id and locationId are required'}, status=400)

    try:
        test_values = TestValue.objects.filter(patient_id=patient_id, locationId=locationId)

        if not test_values.exists():
            return JsonResponse({'message': 'No test values found'}, status=404)

        result = []
        for test_value in test_values:
            result.append({
                'patient_id': test_value.patient_id,
                'locationId': test_value.locationId,
                'testdetails': test_value.testdetails  # Ensure this is JSON serializable
            })

        return JsonResponse({'data': result}, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
