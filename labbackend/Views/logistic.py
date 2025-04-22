
from ..models import LogisticTask ,LogisticData,Patient,SalesVisitLog
from ..serializers import LogisticDataSerializer,LogisticTaskSerializer,SalesVisitLogSerializer,PatientSerializer
from ..serializers import LogisticTaskSerializer
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework import  status
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import quote_plus
from pymongo import MongoClient
from datetime import datetime, timedelta
import certifi



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
   


@api_view(['GET'])
def getsalesmapping(request):
    if request.method == 'GET':
        data = SalesVisitLog.objects.all()
        serializer = SalesVisitLogSerializer(data, many=True)
        return Response(serializer.data)
    

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