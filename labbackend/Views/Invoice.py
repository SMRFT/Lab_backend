from rest_framework.response import Response
from django.http import JsonResponse
import json
from urllib.parse import quote_plus
from pymongo import MongoClient
import certifi
from ..models import Patient, ClinicalName
from ..serializers import PatientSerializer, ClinicalNameSerializer
from django.http import HttpResponse
from datetime import datetime, timedelta
from collections import defaultdict
from rest_framework import status
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
import pytz
import os
from ..auth.permissions import SkipPermissionsIfDisabled
#auth

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from pyauth.auth import HasRoleAndDataPermission
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt

load_dotenv()
def get_mongo_collection():
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
    db = client["Lab"]
    return db["labbackend_invoice"]



@api_view(['GET'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_all_patients(request):
    segment = request.GET.get('segment', 'B2B')
    clinical_name = request.GET.get('clinical_name', '')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    min_credit = request.GET.get('min_credit', '0')

    patients = Patient.objects.filter(segment=segment)

    # Clinical name filter (only if valid credit clinical)
    if clinical_name:
        carry_credit_clinicals = ClinicalName.objects.filter(
            clinicalname=clinical_name,
            b2bType="Credit"
        )
        if carry_credit_clinicals.exists():
            patients = patients.filter(B2B=clinical_name)
        else:
            patients = Patient.objects.none()

    # Date range filter
    if from_date:
        try:
            from_date_parsed = parse_date(from_date)
            if from_date_parsed:
                patients = patients.filter(date__gte=from_date_parsed)
        except Exception:
            pass

    if to_date:
        try:
            to_date_parsed = parse_date(to_date)
            if to_date_parsed:
                # Add +1 day and use __lt so we include full "to_date"
                next_day = to_date_parsed + timedelta(days=1)
                patients = patients.filter(date__lt=next_day)
        except Exception:
            pass

    # Credit amount filter
    if min_credit:
        try:
            min_credit_value = float(min_credit)
            patients = patients.filter(credit_amount__gte=min_credit_value)
        except ValueError:
            pass

    # Exclude already invoiced patients
    collection = get_mongo_collection()
    invoices = list(collection.find({}, {"patients": 1}))

    invoiced_patient_ids = set()
    for invoice in invoices:
        if 'patients' in invoice and invoice['patients']:
            for patient in invoice['patients']:
                if 'patient_id' in patient:
                    invoiced_patient_ids.add(patient['patient_id'])

    if invoiced_patient_ids:
        patients = patients.exclude(patient_id__in=list(invoiced_patient_ids))

    # Final ordering
    patients = patients.order_by('-date')

    serializer = PatientSerializer(patients, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)



@api_view(['GET'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_clinicalname_invoice(request):
    if request.method == 'GET':
        # Filter clinical names with b2bType "Carry Credit"
        clinicalname = ClinicalName.objects.filter(b2bType="Credit")
        serializer = ClinicalNameSerializer(clinicalname, many=True)
        return Response(serializer.data)

# Function to get MongoDB collection

def get_mongo_collection():
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
    db = client["Lab"]
    return db["labbackend_invoice"]


@api_view(["POST"])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def generate_invoice(request):
    collection = get_mongo_collection()
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            # Extract patient IDs from the request
            patient_ids = [patient["patient_id"] for patient in data.get("patients", [])]
            
            # Validate that the clinical name has "Carry Credit" type
            clinical_name = data.get("clinicalName")
            if clinical_name:
                carry_credit_clinical = ClinicalName.objects.filter(
                    clinicalname=clinical_name, 
                    b2bType="Credit"
                ).first()
                
                if not carry_credit_clinical:
                    return JsonResponse(
                        {"error": "Selected clinical name does not have 'Carry Credit' type"}, 
                        status=400
                    )

            # Add metadata for invoice generation tracking
            data["generatedAt"] = datetime.now().isoformat()
            data["status"] = "Generated"
            data["isRegeneratable"] = True

            # Insert invoice data into MongoDB
            result = collection.insert_one(data)

            return JsonResponse(
                {
                    "message": "Credit Invoice stored successfully", 
                    "id": str(result.inserted_id),
                    "invoiceNumber": data.get("invoiceNumber"),
                    "status": "success"
                },
                status=201,
            )
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@api_view(["GET"])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_invoices(request):
    collection = get_mongo_collection()
    # Sort by generation date descending to show latest invoices first
    invoices = list(collection.find({}, {"_id": 0}).sort("generatedAt", -1))
    return JsonResponse(invoices, safe=False)

@api_view(['PUT'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def update_invoice(request, invoice_number):
    """Update the invoice with total, paid, and pending amounts, and track payment history."""
    collection = get_mongo_collection()

    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            new_credit_amount = data.get("totalCreditAmount")
            paid_amount = data.get("paidAmount", "0.00")
            pending_amount = data.get("pendingAmount", "0.00")
            new_payment_details = data.get("paymentDetails", "{}")
            new_payment_history = data.get("paymentHistory", "[]")
            proportional_credits = data.get("proportionalCredits", "[]")

            if new_credit_amount is None:
                return JsonResponse({"error": "Missing totalCreditAmount field"}, status=400)

            # Fetch existing document to merge existing paymentDetails list
# Fetch existing document to merge paymentDetails
            existing_invoice = collection.find_one({"invoiceNumber": invoice_number})

            existing_payment_details = existing_invoice.get("paymentDetails", [])

            # Normalize to list
            if isinstance(existing_payment_details, dict):
                existing_payment_details = [existing_payment_details]
            elif isinstance(existing_payment_details, str):
                try:
                    parsed = json.loads(existing_payment_details)
                    if isinstance(parsed, dict):
                        existing_payment_details = [parsed]
                    elif isinstance(parsed, list):
                        existing_payment_details = parsed
                except Exception:
                    existing_payment_details = []

            # Add the new payment entry
            new_payment_detail_entry = json.loads(new_payment_details) if isinstance(new_payment_details, str) else new_payment_details
            updated_payment_details = existing_payment_details + [new_payment_detail_entry]


            update_data = {
                "totalCreditAmount": new_credit_amount,
                "paidAmount": paid_amount,
                "pendingAmount": pending_amount,
                "paymentDetails": updated_payment_details,
                "paymentHistory": json.loads(new_payment_history) if isinstance(new_payment_history, str) else new_payment_history,
                "proportionalCredits": json.loads(proportional_credits) if isinstance(proportional_credits, str) else proportional_credits,
                "lastUpdatedAt": datetime.now().isoformat(),
                "status": "Updated" if float(paid_amount) > 0 else "Generated"
            }

            result = collection.update_one(
                {"invoiceNumber": invoice_number},
                {"$set": update_data},
            )

            if result.matched_count == 0:
                return JsonResponse({"error": "Invoice not found"}, status=404)

            try:
                proportional_data = json.loads(proportional_credits) if isinstance(proportional_credits, str) else proportional_credits

                for patient_credit in proportional_data:
                    patient_id = patient_credit.get("patient_id")
                    new_credit = patient_credit.get("proportionalCredit", "0.00")

                    Patient.objects.filter(patient_id=patient_id).update(
                        credit_amount=new_credit
                    )

            except Exception as e:
                print(f"Error updating patient credits: {e}")

            return JsonResponse({
                "message": "Invoice and patient credits updated successfully",
                "pendingAmount": pending_amount,
                "paidAmount": paid_amount,
                "paymentDetails": updated_payment_details,
                "paymentHistory": update_data["paymentHistory"],
                "proportionalCredits": update_data["proportionalCredits"],
                "status": update_data["status"]
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        

@api_view(['DELETE'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def delete_invoice(request, invoice_id):
    """Delete an invoice based on invoice_id"""
    collection = get_mongo_collection()

    if request.method == "DELETE":
        try:
            result = collection.delete_one({"invoiceNumber": invoice_id})

            if result.deleted_count == 0:
                return JsonResponse({"error": "Invoice not found"}, status=404)

            return JsonResponse({
                "message": "Invoice deleted successfully",
                "invoiceNumber": invoice_id
            }, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)

# New endpoint for regenerating invoices
@api_view(['POST'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def regenerate_invoice(request, invoice_number):
    """Create a new invoice based on existing invoice data"""
    collection = get_mongo_collection()
    
    if request.method == "POST":
        try:
            # Find the existing invoice
            existing_invoice = collection.find_one({"invoiceNumber": invoice_number})
            
            if not existing_invoice:
                return JsonResponse({"error": "Original invoice not found"}, status=404)
            
            # Create new invoice data based on existing one
            new_invoice_data = {
                "clinicalName": existing_invoice.get("clinicalName"),
                "generateDate": datetime.now().strftime("%Y-%m-%d"),
                "fromDate": existing_invoice.get("fromDate"),
                "toDate": existing_invoice.get("toDate"),
                "invoiceNumber": "INV-" + str(int(time.time()))[-6:],  # Generate new invoice number
                "totalCreditAmount": existing_invoice.get("totalCreditAmount"),
                "paidAmount": "0.00",
                "pendingAmount": existing_invoice.get("totalCreditAmount"),
                "patients": existing_invoice.get("patients", []),
                "paymentDetails": {},
                "proportionalCredits": [],
                "paymentHistory": [],
                "generatedAt": datetime.now().isoformat(),
                "status": "Regenerated",
                "originalInvoice": invoice_number
            }
            
            # Insert the new invoice
            result = collection.insert_one(new_invoice_data)
            
            return JsonResponse({
                "message": "Invoice regenerated successfully",
                "newInvoiceNumber": new_invoice_data["invoiceNumber"],
                "originalInvoice": invoice_number,
                "id": str(result.inserted_id)
            }, status=201)
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({"error": "Invalid request method"}, status=400)

@api_view(['GET'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_invoice_patients(request, invoice_number):
    """Get patients for a specific invoice"""
    collection = get_mongo_collection()
    
    try:
        invoice = collection.find_one({"invoiceNumber": invoice_number})
        
        if not invoice:
            return JsonResponse({"error": "Invoice not found"}, status=404)
        
        patients = invoice.get("patients", [])
        return JsonResponse({"patients": patients}, status=200)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)




def convert_to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def patient_report(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    if not start_date_str or not end_date_str:
        return JsonResponse({"error": "Start date and end date are required"}, status=400)
    
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
    except ValueError:
        return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    # MongoDB Connection
    client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
    db = client.Lab
    patients_collection = db["labbackend_patient"]
    invoice_collection = db["labbackend_invoice"]

    report_by_date = defaultdict(lambda: {
        'gross_amount': 0,
        'discount': 0,
        'due_amount': 0,
        'net_amount': 0,
        'pending_amount': 0,
        'total_collection': 0,
        'credit_payment_received': 0,
        'refund_amount': 0,
        'payment_totals': {'Cash': 0, 'UPI': 0, 'Neft': 0, 'Cheque': 0, 'Credit': 0, 'PartialPayment': 0, 'Credit Card': 0}
    })

    patients = patients_collection.find()

    for patient in patients:
        patient_date = patient.get('date')
        if not patient_date:
            continue

        patient_in_range = start_date <= patient_date < end_date
        if patient_in_range:
            date_key = patient_date.strftime("%Y-%m-%d")
            gross_amount = convert_to_float(patient.get('totalAmount', 0))
            discount = convert_to_float(patient.get('discount', 0))
            due_amount = convert_to_float(patient.get('credit_amount', 0))

            report_by_date[date_key]['gross_amount'] += gross_amount
            report_by_date[date_key]['discount'] += discount
            report_by_date[date_key]['due_amount'] += due_amount

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
                    if method != 'Credit':
                        report_by_date[date_key]['payment_totals'][method] += gross_amount
                    else:
                        report_by_date[date_key]['payment_totals']['Credit'] += gross_amount

        # Refund handling from testname
        test_list = []
        testname_data = patient.get('testname', '')
        if isinstance(testname_data, str) and testname_data.strip():
            try:
                test_list = json.loads(testname_data)
            except json.JSONDecodeError:
                test_list = []
        elif isinstance(testname_data, list):
            test_list = testname_data

        for test in test_list:
            if isinstance(test, dict) and test.get('refund') is True:
                refunded_date_str = test.get('refunded_date')
                if refunded_date_str:
                    try:
                        if 'T' in refunded_date_str:
                            refund_date = datetime.fromisoformat(refunded_date_str).date()
                        else:
                            refund_date = datetime.strptime(refunded_date_str, "%Y-%m-%d").date()

                        if start_date.date() <= refund_date < end_date.date():
                            refund_date_key = refund_date.strftime("%Y-%m-%d")
                            test_amount = convert_to_float(test.get('amount', 0))
                            report_by_date[refund_date_key]['refund_amount'] += test_amount
                    except (ValueError, TypeError):
                        continue

    # 🔁 Process Invoices for paymentDetails
    invoices = invoice_collection.find()
    for invoice in invoices:
        payment_details = invoice.get('paymentDetails', [])
        if isinstance(payment_details, str):
            try:
                payment_details = json.loads(payment_details)
            except json.JSONDecodeError:
                payment_details = []

        for payment in payment_details:
            payment_date_str = payment.get('paymentDate')
            if not payment_date_str:
                continue
            try:
                payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()
                if start_date.date() <= payment_date < end_date.date():
                    payment_date_key = payment_date.strftime("%Y-%m-%d")
                    amount_paid = convert_to_float(payment.get('paymentAmount', 0))
                    method = payment.get('paymentMethod', '')

                    report_by_date[payment_date_key]['credit_payment_received'] += amount_paid
                    if method in report_by_date[payment_date_key]['payment_totals']:
                        report_by_date[payment_date_key]['payment_totals'][method] += amount_paid
                    else:
                        report_by_date[payment_date_key]['payment_totals'][method] = amount_paid
            except ValueError:
                continue

    # 📊 Prepare final report list
    report_list = []
    for date, data in sorted(report_by_date.items()):
        net_amount = data['gross_amount'] - (data['discount'] + data['due_amount'])
        total_collection = net_amount + data['credit_payment_received'] - data['refund_amount']
        report_list.append({
            'date': date,
            'gross_amount': round(data['gross_amount'], 2),
            'discount': round(data['discount'], 2),
            'due_amount': round(data['due_amount'], 2),
            'credit_payment_received': round(data['credit_payment_received'], 2),
            'refund_amount': round(data['refund_amount'], 2),
            'net_amount': round(net_amount, 2),
            'total_collection': round(total_collection, 2),
            'payment_totals': {key: round(value, 2) for key, value in data['payment_totals'].items()},
        })

    client.close()
    return Response({'report': report_list})
