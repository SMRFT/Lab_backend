from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework import  status
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Max
from datetime import datetime, date
import json
import re
from ..models import SalesVisitLog ,HospitalLab,Patient
from ..serializers import SalesVisitLogSerializer
from datetime import datetime, timedelta
from ..serializers import HospitalLabSerializer

from ..auth.permissions import SkipPermissionsIfDisabled
#auth
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from pyauth.auth import HasRoleAndDataPermission

@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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


@api_view(['GET'])
@csrf_exempt
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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





@api_view(['GET', 'POST'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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
    
@api_view(['GET'])
@permission_classes([SkipPermissionsIfDisabled, HasRoleAndDataPermission])
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