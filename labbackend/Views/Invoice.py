
from rest_framework.response import Response
from django.http import JsonResponse
import json
from urllib.parse import quote_plus
from pymongo import MongoClient
import certifi
from ..models import Patient
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
import pytz
import os
from dotenv import load_dotenv

load_dotenv()

# Function to get MongoDB collection

def get_mongo_collection():
    password = quote_plus("Smrft@2024")
    client = MongoClient(os.getenv('DB_HOST'))
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
    """Update the invoice with total, paid, and pending amounts, payment date and method."""
    collection = get_mongo_collection()

    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            new_credit_amount = data.get("totalCreditAmount")
            paid_amount = data.get("paidAmount", "0.00")
            pending_amount = data.get("pendingAmount", "0.00")
            payment_details = data.get("paymentDetails", "{}")
            payment_history = data.get("paymentHistory", "[]")

            if new_credit_amount is None:
                return JsonResponse({"error": "Missing totalCreditAmount field"}, status=400)
            
            # Update the invoice with all values
            result = collection.update_one(
                {"invoiceNumber": invoice_number},
                {"$set": {
                    "totalCreditAmount": new_credit_amount,
                    "paidAmount": paid_amount,
                    "pendingAmount": pending_amount,
                    "paymentDetails": payment_details,
                    "paymentHistory": payment_history
                }},
            )

            if result.matched_count == 0:
                return JsonResponse({"error": "Invoice not found"}, status=404)

            return JsonResponse({
                "message": "Invoice updated successfully",
                "pendingAmount": pending_amount,
                "paidAmount": paid_amount,
                "paymentDetails": payment_details,
                "paymentHistory": payment_history
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