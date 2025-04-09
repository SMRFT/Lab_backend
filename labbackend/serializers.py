from rest_framework import serializers
from bson import ObjectId
from django.core.validators import FileExtensionValidator

class ObjectIdField(serializers.Field):
    def to_representation(self, value):
        return str(value)
    def to_internal_value(self, data):
        return ObjectId(data)


from rest_framework import serializers
from .models import Register

class RegisterSerializer(serializers.ModelSerializer):
    confirmPassword = serializers.CharField(write_only=True)

    class Meta:
        model = Register
        fields = ['name', 'role', 'password', 'confirmPassword']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data.get('password') != data.get('confirmPassword'):
            raise serializers.ValidationError({"confirmPassword": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('confirmPassword')  # Remove confirmPassword before saving
        return Register.objects.create(**validated_data)


from .models import Patient
class PatientSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = Patient
        fields = '__all__'


from .models import SampleCollector
class SampleCollectorSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = SampleCollector
        fields = '__all__'

        
from .models import ClinicalName
class ClinicalNameSerializer(serializers.ModelSerializer):
    mouCopy = serializers.FileField(
        required=False, 
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'jpg', 'png', 'csv'])],
        write_only=True
    )

    class Meta:
        model = ClinicalName
        fields = '__all__'
        extra_kwargs = {
            'mou_file_id': {'read_only': True},
            'first_approved': {'read_only': True},
            'final_approved': {'read_only': True},
            'first_approved_timestamp': {'read_only': True},
            'final_approved_timestamp': {'read_only': True},
            'status': {'read_only': True}
        }


from .models import RefBy
class RefBySerializer(serializers.ModelSerializer):
    # Convert ObjectId to string if using MongoDB
    id = ObjectIdField(read_only=True)
    class Meta:
        model = RefBy
        fields = '__all__'


class PatientReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['patient_id', 'totalAmount', 'discount', 'credit_amount', 'date']


from .models import TestValue
class TestValueSerializer(serializers.ModelSerializer):
    testdetails = serializers.JSONField()  # Store multiple test details as JSON
    class Meta:
        model = TestValue  # Replace with your model name
        fields = ['patient_id', 'patientname', 'age', 'date', 'testdetails']


from rest_framework import serializers
from .models import SampleStatus
class SampleStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleStatus
        fields = '__all__'  # Include all fields from the model


from .models import SalesVisitLog
class SalesVisitLogSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = SalesVisitLog
        fields = "__all__"


from .models import HospitalLab
class HospitalLabSerializer(serializers.ModelSerializer):
    class Meta:
        model = HospitalLab
        fields = '__all__'


from .models import LogisticData
class LogisticDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogisticData
        fields = '__all__'


from .models import LogisticTask
class LogisticTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogisticTask
        fields = '__all__'