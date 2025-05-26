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
        date = request.query_params.get('date')
        month = request.query_params.get('month')
        week = request.query_params.get('week')
        salesPerson = request.query_params.get('salesPerson')

        logs = SalesVisitLog.objects.all()
        print("Initial count:", logs.count())

        # Date filter
        if date:
            try:
                parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
                logs = logs.filter(date=parsed_date)
                print("Count after date filter:", logs.count())
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        # Month filter
        if month:
            try:
                year, month_num = map(int, month.split('-'))
                start_date = datetime(year, month_num, 1).date()
                if month_num == 12:
                    end_date = datetime(year + 1, 1, 1).date()
                else:
                    end_date = datetime(year, month_num + 1, 1).date()
                logs = logs.filter(date__gte=start_date, date__lt=end_date)
                print("Count after month filter:", logs.count())
            except (ValueError, IndexError):
                return Response({"error": "Invalid month format. Use YYYY-MM."}, status=status.HTTP_400_BAD_REQUEST)

        # Week filter - Fixed implementation
        if week:
            try:
                match = re.match(r"(\d{4})-W(\d{1,2})", week)
                if not match:
                    return Response({"error": "Invalid week format. Use YYYY-Wxx."}, status=status.HTTP_400_BAD_REQUEST)
                
                year, week_number = map(int, match.groups())
                
                # Calculate the start of the week using ISO 8601 standard
                # January 1st of the given year
                jan_1 = datetime(year, 1, 1).date()
                
                # Find the first Monday of the year (ISO week starts on Monday)
                # If Jan 1 is Monday (weekday=0), then it's week 1
                # If Jan 1 is Tuesday-Sunday (weekday=1-6), then we need to find the next Monday
                jan_1_weekday = jan_1.weekday()  # Monday=0, Sunday=6
                
                if jan_1_weekday == 0:  # Jan 1 is Monday
                    first_monday = jan_1
                else:
                    days_until_monday = 7 - jan_1_weekday
                    first_monday = jan_1 + timedelta(days=days_until_monday)
                
                # Calculate the start date of the requested week
                # Week 1 starts on the first Monday
                start_date = first_monday + timedelta(weeks=week_number - 1)
                end_date = start_date + timedelta(days=6)  # Sunday of the same week
                
                logs = logs.filter(date__range=(start_date, end_date))
                print(f"Week filter: {week}, Start: {start_date}, End: {end_date}")
                print("Count after week filter:", logs.count())
                
            except Exception as e:
                print(f"Week filter error: {e}")
                return Response({"error": "Invalid week value. Use format YYYY-Wxx."}, status=status.HTTP_400_BAD_REQUEST)

        # Salesperson filter
        if salesPerson:
            logs = logs.filter(salesMapping__icontains=salesPerson)
            print("Count after salesperson filter:", logs.count())

        # Serialize and return
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