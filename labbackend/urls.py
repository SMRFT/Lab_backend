#urls.py
from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .Views import whatsapp
from labbackend.Views.Security import registration ,login
from labbackend.Views.patients import create_patient,get_latest_bill_no,get_latest_patient_id,get_patient_details,get_patients_by_date,patient_overview,get_patient_by_id,get_patients,patients_by_date
from labbackend.Views.barcode import get_max_barcode,save_barcodes,get_existing_barcode,get_barcode_by_date,check_barcode
from labbackend.Views.location import sample_collector_location
from labbackend.Views.salesvisit import salesvisitlog ,get_sales_log,hospitallabform,salesdashboard
from labbackend.Views.addform import sample_collector ,refby
from labbackend.Views.Invoice import generate_invoice,get_invoices,delete_invoice,update_invoice,get_clinicalname_invoice,get_all_patients,patient_report
from labbackend.Views.updatebillingandpatient import update_patient,update_credit_amount,update_billing,get_patient_tests,credit_amount_update
from labbackend.Views.samplestatus import get_received_samples ,get_sample_collected,update_sample_collected,get_samplepatients_by_date,sample_status,update_sample_status
from labbackend.Views.logistic import save_logistic_data,get_logistic_data,getlogisticdatabydate,savesamplecollectordetails,update_sample_collector_details,getsalesmapping,logisticdashboard
from labbackend.Views.refundandcancellation import search_cancellation,verify_and_process_refund,search_refund,verify_and_process_cancellation,generate_otp_cancellation,generate_otp_refund,logs_api,dashboard_data
from labbackend.Views.clinicalname import clinical_name,get_last_referrer_code,get_clinicalname,ClinicalNameViewSet,preview_mou_file,update_clinicalname
from labbackend.Views.devicedata import create_device_data


urlpatterns = [
    path('registration/', registration, name='registration'),
    path('login/', login, name='login'),
    path('patient/create/', create_patient, name='create_patient'),
    path('latest-patient-id/', get_latest_patient_id, name='get_latest_patient_id'),
    path("patient/update/<str:patient_id>/", update_patient, name="update_patient"),
    path('patients_get_barcode/', get_barcode_by_date, name='get_barcode_by_date'),
    path('get-max-barcode/', get_max_barcode, name='get_max_barcode'),
    path('save-barcodes/', save_barcodes, name='save_barcodes'),
    path('latest-bill-no/', get_latest_bill_no, name='get_latest_bill_no'),
    path('get-existing-barcode/',get_existing_barcode, name='get_latest_bill_no'),
    path('patient-get/',get_patient_details, name='sample_status'),
    path('patients/', get_patients_by_date, name='get_patients_by_date'),
    path('patients/<str:patient_id>/', get_patients_by_date, name='get_patients_by_date'),
    path('get_received_samples/', get_received_samples, name='get_received_samples'),
    path('patient_report/', patient_report, name='patient_report'),
    path('test_details/', views.get_test_details, name='get_test_details'),
    path('test_details_test/', views.handle_patch_request, name='get_test_details'),
    path('test_parameters/<str:test_name>/', views.get_test_parameters, name='get_test_parameters'),
    path('compare_test_details/', views.compare_test_details, name='compare_test_details'),
    path('get_patient_test_details/', views.get_patient_test_details, name='get_patient_test_details'),
    path('test-value/save/', views.save_test_value, name='save_test_value'),
    path('test-value/update/', views.update_test_value, name='update_test_value'),
    path('update_dispatch_status/<str:patient_id>/', views.update_dispatch_status, name='update_dispatch_status'),
    path('sample-collector/', sample_collector, name='create_sample_collector'),
    path('refby/', refby, name='refby'),
    path('clinical_name/', clinical_name, name='create_organisation'),
    path('clinical_name/last/', get_last_referrer_code, name='get_last_referrer_code'),
    path('test-report/', views.get_test_report, name='get_test_report'),
    path('test-values/', views.get_test_values, name='get_test_values'),
    path('test-values/<str:patient_id>/<int:test_index>/approve/', views.approve_test_detail, name='approve_test_detail'),
    path('test-values/<str:patient_id>/<int:test_index>/rerun/', views.rerun_test_detail, name='rerun_test_detail'),
    path('update-test-detail/<str:patient_id>/', views.update_test_detail, name='update_test_detail'),
    path("get_sample_collected/", get_sample_collected, name="get_sample_collected"),
    path("update_sample_collected/<str:patient_id>/", update_sample_collected, name="update_sample_collected"),
    path('sample_patient/', get_samplepatients_by_date, name='get_samplepatients_by_date'),
    path('sample_status/', sample_status, name='sample_status'),
    path('testvalue/', views.test_values, name='get_test_values'),
    path('update_sample_status/<str:patient_id>/', update_sample_status, name='update_sample_status'),
    path('samplestatus-testvalue/', views.get_samplestatus_testvalue, name='sample-status-list'),
    path('patient_overview/', patient_overview, name='patient_overview'),
    path('patient_test_status/', views.patient_test_status, name='patient_test_status'),
    path('all-patients/', get_all_patients, name='get_all_patients'),
    path('overall_report/', views.overall_report, name='overall_report'),
    path('patient_test_sorting/', views.patient_test_sorting, name='patient_test_sorting'),
    path('credit_amount/<str:patient_id>/', credit_amount_update, name='credit_amount_update'),
    path('update-credit/<str:patient_id>/', update_credit_amount, name='update_credit_amount'),
    path('send-email/', views.send_email, name='send_email'),
    path('SalesVisitLog/', salesvisitlog, name='salesvisitlog'),
    path('SalesVisitLogReport/', get_sales_log, name='sales-visit-log-report'),
    path('hospitallabform/', hospitallabform, name='hospitallabform'),
    path('save-logistic-data/', save_logistic_data, name='save-logistic-data'),
    path('get_logistic_data/', get_logistic_data, name='get_logistic_data'),
    path('patient/get/<str:patient_id>/', get_patient_by_id, name='get_patient_by_id'),
    path('getlogisticdata/', getlogisticdatabydate, name='getlogisticdatabydate'),
    path('check-barcode/',check_barcode, name='check-barcode'),
    path('device-data/', create_device_data, name='create-device-data'),#Devicedata(machineintreface)
    path('savesamplecollector/', savesamplecollectordetails, name='savesamplecollectordetails'),
    path('updatesamplecollectordetails/', update_sample_collector_details, name='update_sample_collector_details'),
    path('patient/get/<str:patient_id>/', get_patient_by_id, name='get_patient_by_id'),
    path('consolidated-data/', views.ConsolidatedDataView.as_view(), name='consolidated_data'),
    path("generate-invoice/", generate_invoice, name="generate-invoice"),
    path("get-invoices/", get_invoices, name="get-invoices"),
    path("update-invoice/<str:invoice_number>/", update_invoice, name="update-invoice"),
    path("delete-invoice/<str:invoice_id>/", delete_invoice, name="delete-invoice"),
    path('salesdashboard/',salesdashboard, name='salesdashboard'),
    path('getsalesmapping/',getsalesmapping, name='getsalesmapping'),
    path('logisticdashboard/',logisticdashboard, name='logisticdashboard'),
    path('search_refund/', search_refund, name='search_refund'),
    path('verify_and_process_refund/', verify_and_process_refund, name='verify_and_process_refund'),
    path('search_cancellation/', search_cancellation, name='search_cancellation'),
    path("upload-pdf/", whatsapp.upload_pdf_to_gridfs, name="upload_pdf"),
    path("get-file/<str:file_id>/", whatsapp.get_pdf_from_gridfs, name="get_pdf"),
    path("send-whatsapp/", whatsapp.send_whatsapp_message, name="send_whatsapp"),
    path('get_patients/', get_patients, name='get_patients'),
    path('patient/update_billing/<str:patient_id>/', update_billing, name='update_billing'),
    path('patient/tests/<str:patient_id>/<str:date>/', get_patient_tests, name='get_patient_tests'),
    path('clinical_name/', clinical_name, name='clinical_name'),
    path('clinical_name/last/', get_last_referrer_code, name='get_last_referrer_code'),
    path('clinical-names/', ClinicalNameViewSet.as_view({'get': 'list'}), name='clinical-names-list'),
    path('clinical-names/<str:referrerCode>/', ClinicalNameViewSet.as_view({'get': 'retrieve'}), name='clinical-name-detail'),
    path('clinical-names/<str:referrerCode>/first_approve/', ClinicalNameViewSet.as_view({'patch': 'first_approve'}), name='clinical-name-first-approve'),
    path('clinical-names/<str:referrerCode>/final_approve/', ClinicalNameViewSet.as_view({'patch': 'final_approve'}), name='clinical-name-final-approve'),
    path('search_refund/', search_refund, name='search_refund'),
    path('verify_and_process_refund/', verify_and_process_refund, name='verify_and_process_refund'),
    path('generate_otp_refund/', generate_otp_refund, name='generate_otp_refund'),
    path('generate_otp_cancellation/', generate_otp_cancellation, name='generate_otp_cancellation'),
    path('search_cancellation/', search_cancellation, name='search_cancellation'),
    path('verify_and_process_cancellation/',verify_and_process_cancellation, name='verify_and_process_cancellation'),
    path('refund_cancellation_logs/', logs_api, name='refund_cancellation_logs'),
    path('mou-preview/<str:file_id>/',preview_mou_file, name='preview_mou_file'),
    path('dashboard-data/', dashboard_data, name='dashboard_data'),
    path('sample_collector_location/', sample_collector_location, name='save_collector_location'),
    path('get_clinicalname/', get_clinicalname, name='get_clinicalname'),
    path('get_clinicalname_invoice/', get_clinicalname_invoice, name='get_clinicalname_by_referrer'),
    path('patients-by-date/', patients_by_date),
    path('send_approval_email/', views.send_approval_email, name='send_approval_email'),
    path('approve_test/', views.approve_test, name='approve_test'),
    path('clinicalname/update/', update_clinicalname, name='approve_test_by_index'),

]