import gridfs
from django.http import JsonResponse
from django.core.files.storage import default_storage
from pymongo import MongoClient
from bson.objectid import ObjectId
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
#auth
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from pyauth.auth import HasRoleAndDataPermission
from ..auth.permissions import SkipPermissionsIfDisabled

import os
from dotenv import load_dotenv
load_dotenv()
# MongoDB Connection
client = MongoClient(os.getenv('GLOBAL_DB_HOST'))
db = client["Lab"]
fs = gridfs.GridFS(db)

@api_view(['POST'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def upload_pdf_to_gridfs(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]

        # 1. Validate type
        if file.content_type != "application/pdf":
            return JsonResponse({"error": "Only PDF files are allowed."}, status=400)

        # 2. Limit size (5MB)
        if file.size > 5 * 1024 * 1024:
            return JsonResponse({"error": "File too large (max 5 MB)."}, status=400)

        # 3. Sanitize filename
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9_\.\-]', '_', file.name)

        # 4. Upload to GridFS
        file_id = fs.put(file, filename=safe_name)

        # 5. Generate access URL
        file_url = f"https://shinova.in/_b_a_c_k_e_n_d/Diagnostics/get-file/{str(file_id)}"

        return JsonResponse({"file_id": str(file_id), "file_url": file_url})

    return JsonResponse({"error": "No file uploaded"}, status=400)

from django.http import HttpResponse
from bson import ObjectId

@api_view(['GET'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
def get_pdf_from_gridfs(request, file_id):
    try:
        file = fs.get(ObjectId(file_id))
        response = HttpResponse(file.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{file.filename}"'  # ← forces download
        return response
    except:
        return JsonResponse({"error": "File not found"}, status=404)




import requests
import urllib.parse
from django.http import JsonResponse
from rest_framework.decorators import api_view

@api_view(['POST'])
def send_whatsapp_template(request):

    data = request.data

    license_number = "23638212604"
    api_key = "gENpYneQRuS7Vzq3dHoaB40lk"
    template_id = "diagnostics_report"

    # Get parameters from request
    param1 = str(data.get("patient_name", "")).strip()
    param2 = str(data.get("collection_time", "")).strip()
    param3 = str(data.get("collection_date", "")).strip()
    param4 = str(data.get("file_url", "")).strip()
    phone = str(data.get("phone_number", "")).strip()
    pdf_name = str(data.get("pdf_name", "report.pdf")).strip()

    # ✅ Validate inputs
    if not all([param1, param2, param3, param4, phone]):
        return JsonResponse({"error": "Missing one or more required parameters"}, status=400)

    # ✅ Encode individual parameters
    param_list = [param1, param2, param3, param4]
    encoded_params = ",".join(urllib.parse.quote(p) for p in param_list)
    encoded_fileurl = urllib.parse.quote(param4, safe='')
    encoded_pdfname = urllib.parse.quote(pdf_name)

    # ✅ Construct Botify API URL
    api_url = (
        f"https://admin.botify.in/api/sendtemplate.php"
        f"?LicenseNumber={license_number}"
        f"&APIKey={api_key}"
        f"&Contact={phone}"
        f"&Template={template_id}"
        f"&Param={encoded_params}"
        f"&Fileurl={encoded_fileurl}"
        f"&PDFName={encoded_pdfname}"
    )

    print("🟢 Final Botify Template URL:", api_url)

    try:
        response = requests.get(api_url)
        return JsonResponse(response.json())
    except Exception as e:
        return JsonResponse({"error": "Botify API call failed", "details": str(e)}, status=500)
