from django.db import models
from datetime import datetime

class Register(models.Model):
    name = models.CharField(max_length=500)
    role = models.CharField(max_length=500)
    password = models.CharField(max_length=500)
    confirmPassword = models.CharField(max_length=500)
#new registration
class Patient(models.Model):
    patient_id = models.CharField(max_length=10)
    patientname = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    gender = models.CharField(max_length=10)
    email = models.EmailField(blank=True)
    address = models.JSONField(blank=True, null=True) 
    age = models.IntegerField()
    age_type = models.CharField(max_length=10, blank=True)  # Adjusted field name for consistency
    sample_collector = models.CharField(max_length=100, blank=True)
    salesMapping = models.CharField(max_length=100, blank=True)
    date = models.DateTimeField()
    discount= models.CharField(max_length=100, blank=True)
    lab_id = models.CharField(max_length=50, blank=True)
    refby = models.CharField(max_length=100, blank=True)  # Referring doctor or reference
    branch = models.CharField(max_length=100, blank=True)
    B2B = models.CharField(max_length=100, blank=True, null=True)
    segment= models.CharField(max_length=100, blank=True)
    testname = models.JSONField(max_length=100)
    totalAmount = models.CharField(max_length=100, blank=True)
    payment_method = models.JSONField(blank=True)
    registeredby = models.CharField(max_length=50, blank=True)
    bill_no = models.CharField(max_length=20, unique=True, blank=True)  # New field for bill number
    PartialPayment= models.JSONField(max_length=150, blank=True)
    credit_amount = models.CharField(max_length=100, blank=True)
    def save(self, *args, **kwargs):
        # Generate the billno if not already set
        self.credit_amount = self.credit_amount if self.credit_amount else "0"
        if not self.bill_no:
            today = datetime.now().strftime('%Y%m%d')  # Current year, month, date
            last_bill = Patient.objects.filter(bill_no__startswith=today).order_by('-bill_no').first()
            if last_bill:
                # Increment the last bill number
                last_id = int(last_bill.bill_no[-4:])  # Extract the last 4 digits
                next_id = last_id + 1
            else:
                next_id = 1  # Start with 1 if no bills exist for the day
            self.bill_no = f"{today}{next_id:04d}"  # Generate billno in YYYYMMDD0001 format
        super().save(*args, **kwargs)  # Call the parent save method
    def __str__(self):
        return self.patientname
    

class ClinicalName(models.Model):
    # Using referrerCode as primary key instead of id
    referrerCode = models.CharField(max_length=10, primary_key=True)
    clinicalname = models.CharField(max_length=255)
    type = models.CharField(max_length=50, blank=True, null=True)
    salesMapping = models.CharField(max_length=100, blank=True, null=True)
    reportDelivery = models.CharField(max_length=100, blank=True, null=True)
    report = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    alternateNumber = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    b2bType = models.CharField(max_length=50, blank=True, null=True)
    creditType = models.CharField(max_length=50, blank=True, null=True)
    mou_file_id = models.CharField(max_length=255, blank=True, null=True)
    creditLimit = models.CharField(max_length=10, blank=True, null=True)
    invoicePeriod = models.CharField(max_length=50, blank=True, null=True)
    # Approval fields
    created_at = models.DateTimeField(auto_now_add=True)
    first_approved = models.BooleanField(default=False)
    final_approved = models.BooleanField(default=False)
    first_approved_timestamp = models.DateTimeField(null=True, blank=True)
    final_approved_timestamp = models.DateTimeField(null=True, blank=True)
    APPROVAL_STAGES = (
        ('PENDING_APPROVAL', 'Pending Approval'),
        ('PENDING_FINAL', 'Pending Final Approval'),
        ('APPROVED', 'Fully Approved'),
    )
    status = models.CharField(
        max_length=50,
        choices=APPROVAL_STAGES,
        default='PENDING_APPROVAL'
    )
    def __str__(self):
        return f"{self.clinicalname} ({self.referrerCode})"

    
class RefBy(models.Model):
    name = models.CharField(max_length=255)
    qualification = models.CharField(max_length=255, blank=True, null=True)
    specialization = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    def __str__(self):
        return f"{self.name}"
    
    
class SampleCollector(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    gender  = models.CharField(max_length=255, blank=True, null=True)
    phone  = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField()
    def __str__(self):
        return f"{self.name}"
    
from bson import ObjectId  # Import ObjectId from bson
class TestValue(models.Model):
    _id = models.CharField(max_length=50, primary_key=True)
    patient_id = models.CharField(max_length=10)
    patientname = models.CharField(max_length=100)
    age = models.IntegerField()
    date = models.DateField()
    barcode= models.CharField(max_length=50)
    testdetails = models.JSONField()  # Store all test details in JSON format
    # approved_by = models.CharField(max_length=200, null=True, blank=True)
    def save(self, *args, **kwargs):
        if not self._id:
            self._id = str(ObjectId())  # Convert ObjectId to string
        super().save(*args, **kwargs)
    
    
class SampleStatus(models.Model):
    patient_id = models.CharField(max_length=100)
    patientname = models.CharField(max_length=100)
    barcode= models.CharField(max_length=50)
    age = models.IntegerField()
    segment = models.CharField(max_length=50, blank=True)
    date = models.DateTimeField(null=True, blank=True)  # Use DateTimeField to store both date and time
    testdetails = models.JSONField(default=list)  # Assuming you're using Django 3.1+ for JSONField
    def __str__(self):
        return self.patientname


class BarcodeTestDetails(models.Model):
    patient_id = models.CharField(max_length=50)
    patientname = models.CharField(max_length=255)
    segment= models.CharField(max_length=100, blank=True)
    sample_collector = models.CharField(max_length=100, blank=True)
    age = models.CharField(max_length=255)
    gender = models.CharField(max_length=50)
    date = models.DateField()
    bill_no= models.CharField(max_length=50, primary_key=True,unique=True)
    barcode= models.CharField(max_length=50)
    tests = models.JSONField()  # Store tests as a list of dictionaries
    def __str__(self):
        return f"{self.patientname} - {self.patient_id}"


class SalesVisitLog(models.Model):
    date = models.DateField()
    time = models.CharField(max_length=255)
    clinicalname = models.CharField(max_length=255,blank=True)
    salesMapping = models.CharField(max_length=100,blank=True)
    personMet = models.CharField(max_length=100,blank=True)
    designation = models.CharField(max_length=100,blank=True)
    location = models.CharField(max_length=100,blank=True)
    phoneNumber = models.CharField(max_length=15,blank=True)
    noOfVisits=  models.CharField(max_length=15,blank=True)
    comments = models.CharField(max_length=150,blank=True)
    type = models.CharField(max_length=100,blank=True)
    



from django.db import models
class HospitalLab(models.Model):
    TYPE_CHOICES = [
        ('StandAlone', 'StandAlone'),
        ('Lab', 'Lab'),
    ]
    hospitalName = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='StandAlone')
    contactPerson = models.CharField(max_length=255)
    contactNumber = models.CharField(max_length=20)
    emailId = models.EmailField()
    salesMapping = models.CharField(max_length=255)
    def __str__(self):
        return self.hospitalName


class LogisticData(models.Model):
    date = models.DateField()
    sampleordertime = models.CharField(max_length=255)
    labName= models.CharField(max_length=255)
    salesMapping = models.CharField(max_length=255, blank=True, null=True)
    sampleCollector = models.CharField(max_length=255)
    def __str__(self):
        return f"{self.labName} - {self.date}"
    

class LogisticTask(models.Model):
    sampleCollector = models.CharField(max_length=255)
    date = models.DateField()
    sampleordertime = models.CharField(max_length=255)
    sampleacceptedtime = models.CharField(max_length=255)
    lab_name = models.CharField(max_length=255)
    salesMapping = models.CharField(max_length=255)
    task = models.CharField(max_length=50, choices=[("Accepted", "Accepted"), ("Not Accepted", "Not Accepted")], blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    samplepickeduptime = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"{self.date} - {self.lab_name} - {self.salesMapping}"



    