#urls.py
from django.urls import path
from . import views
from .views import generate_invoice, get_invoices,update_invoice,delete_invoice
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import whatsapp
urlpatterns = [
    path('_b_a_c_k_e_n_d_/Diagnostics/registration/', views.registration, name='registration'),
    path('_b_a_c_k_e_n_d_/Diagnostics/login/', views.login, name='login'),
    path('_b_a_c_k_e_n_d_/Diagnostics/patient/create/', views.create_patient, name='create_patient'),
    path('_b_a_c_k_e_n_d_/Diagnostics/latest-patient-id/', views.get_latest_patient_id, name='get_latest_patient_id'),
    path("_b_a_c_k_e_n_d_/Diagnostics/patient/update/<str:patient_id>/", views.update_patient, name="update_patient"),
    path('_b_a_c_k_e_n_d_/Diagnostics/patients_get_barcode/', views.get_barcode_by_date, name='get_barcode_by_date'),
    path('_b_a_c_k_e_n_d_/Diagnostics/get-max-barcode/', views.get_max_barcode, name='get_max_barcode'),
    path('_b_a_c_k_e_n_d_/Diagnostics/save-barcodes/', views.save_barcodes, name='save_barcodes'),
    path('_b_a_c_k_e_n_d_/Diagnostics/latest-bill-no/', views.get_latest_bill_no, name='get_latest_bill_no'),
    path('_b_a_c_k_e_n_d_/Diagnostics/get-existing-barcode/', views.get_existing_barcode, name='get_latest_bill_no'),
    path('_b_a_c_k_e_n_d_/Diagnostics/patient-get/', views.get_patient_details, name='sample_status'),
    path('_b_a_c_k_e_n_d_/Diagnostics/patients/', views.get_patients_by_date, name='get_patients_by_date'),
    path('_b_a_c_k_e_n_d_/Diagnostics/patients/<str:patient_id>/', views.get_patients_by_date, name='get_patients_by_date'),
    path('_b_a_c_k_e_n_d_/Diagnostics/get_received_samples/', views.get_received_samples, name='get_received_samples'),
    path('_b_a_c_k_e_n_d_/Diagnostics/patient_report/', views.patient_report, name='patient_report'),
    path('_b_a_c_k_e_n_d_/Diagnostics/test_details/', views.get_test_details, name='get_test_details'),
    path('_b_a_c_k_e_n_d_/Diagnostics/test_details_test/', views.handle_patch_request, name='get_test_details'),
    path('_b_a_c_k_e_n_d_/Diagnostics/test_parameters/<str:test_name>/', views.get_test_parameters, name='get_test_parameters'),
    path('_b_a_c_k_e_n_d_/Diagnostics/compare_test_details/', views.compare_test_details, name='compare_test_details'),
    path('_b_a_c_k_e_n_d_/Diagnostics/get_patient_test_details/', views.get_patient_test_details, name='get_patient_test_details'),
    path('_b_a_c_k_e_n_d_/Diagnostics/test-value/save/', views.save_test_value, name='save_test_value'),
    path('_b_a_c_k_e_n_d_/Diagnostics/test-value/update/', views.update_test_value, name='update_test_value'),
    path('_b_a_c_k_e_n_d_/Diagnostics/update_dispatch_status/<str:patient_id>/', views.update_dispatch_status, name='update_dispatch_status'),
    path('_b_a_c_k_e_n_d_/Diagnostics/sample-collector/', views.sample_collector, name='create_sample_collector'),
    path('_b_a_c_k_e_n_d_/Diagnostics/refby/', views.refby, name='refby'),
    path('_b_a_c_k_e_n_d_/Diagnostics/clinical_name/', views.clinical_name, name='create_organisation'),
    path('_b_a_c_k_e_n_d_/Diagnostics/clinical_name/last/', views.get_last_referrer_code, name='get_last_referrer_code'),
    path('_b_a_c_k_e_n_d_/Diagnostics/test-report/', views.get_test_report, name='get_test_report'),
    path('_b_a_c_k_e_n_d_/Diagnostics/test-values/', views.get_test_values, name='get_test_values'),
    path('_b_a_c_k_e_n_d_/Diagnostics/test-values/<str:patient_id>/<int:test_index>/approve/', views.approve_test_detail, name='approve_test_detail'),
    path('_b_a_c_k_e_n_d_/Diagnostics/test-values/<str:patient_id>/<int:test_index>/rerun/', views.rerun_test_detail, name='rerun_test_detail'),
    path('_b_a_c_k_e_n_d_/Diagnostics/update-test-detail/<str:patient_id>/', views.update_test_detail, name='update_test_detail'),
    path("_b_a_c_k_e_n_d_/Diagnostics/get_sample_collected/", views.get_sample_collected, name="get_sample_collected"),
    path("_b_a_c_k_e_n_d_/Diagnostics/update_sample_collected/<str:patient_id>/", views.update_sample_collected, name="update_sample_collected"),
    path('_b_a_c_k_e_n_d_/Diagnostics/sample_patient/', views.get_samplepatients_by_date, name='get_samplepatients_by_date'),
    path('_b_a_c_k_e_n_d_/Diagnostics/sample_status/', views.sample_status, name='sample_status'),
    path('_b_a_c_k_e_n_d_/Diagnostics/testvalue/', views.test_values, name='get_test_values'),
    path('_b_a_c_k_e_n_d_/Diagnostics/update_sample_status/<str:patient_id>/', views.update_sample_status, name='update_sample_status'),
    path('_b_a_c_k_e_n_d_/Diagnostics/samplestatus-testvalue/', views.get_samplestatus_testvalue, name='sample-status-list'),
    path('_b_a_c_k_e_n_d_/Diagnostics/patient_overview/', views.patient_overview, name='patient_overview'),
    path('_b_a_c_k_e_n_d_/Diagnostics/patient_test_status/', views.patient_test_status, name='patient_test_status'),
    path('_b_a_c_k_e_n_d_/Diagnostics/all-patients/', views.get_all_patients, name='get_all_patients'),
    path('_b_a_c_k_e_n_d_/Diagnostics/overall_report/', views.overall_report, name='overall_report'),
    path('_b_a_c_k_e_n_d_/Diagnostics/patient_test_sorting/', views.patient_test_sorting, name='patient_test_sorting'),
    path('_b_a_c_k_e_n_d_/Diagnostics/credit_amount/<str:patient_id>/', views.credit_amount_update, name='credit_amount_update'),
    path('_b_a_c_k_e_n_d_/Diagnostics/update-credit/<str:patient_id>/', views.update_credit_amount, name='update_credit_amount'),
    path('_b_a_c_k_e_n_d_/Diagnostics/send-email/', views.send_email, name='send_email'),
    path('_b_a_c_k_e_n_d_/Diagnostics/SalesVisitLog/', views.salesvisitlog, name='salesvisitlog'),
    path('_b_a_c_k_e_n_d_/Diagnostics/SalesVisitLogReport/', views.get_sales_log, name='sales-visit-log-report'),
    path('_b_a_c_k_e_n_d_/Diagnostics/hospitallabform/', views.hospitallabform, name='hospitallabform'),
    path('_b_a_c_k_e_n_d_/Diagnostics/save-logistic-data/', views.save_logistic_data, name='save-logistic-data'),
    path('_b_a_c_k_e_n_d_/Diagnostics/get_logistic_data/', views.get_logistic_data, name='get_logistic_data'),
    path('_b_a_c_k_e_n_d_/Diagnostics/patient/get/<str:patient_id>/', views.get_patient_by_id, name='get_patient_by_id'),
    path('_b_a_c_k_e_n_d_/Diagnostics/getlogisticdata/', views.getlogisticdatabydate, name='getlogisticdatabydate'),
    path('_b_a_c_k_e_n_d_/Diagnostics/check-barcode/', views.check_barcode, name='check-barcode'),
    path('_b_a_c_k_e_n_d_/Diagnostics/savesamplecollector/', views.savesamplecollectordetails, name='savesamplecollectordetails'),
    path('_b_a_c_k_e_n_d_/Diagnostics/updatesamplecollectordetails/', views.update_sample_collector_details, name='update_sample_collector_details'),
    path('_b_a_c_k_e_n_d_/Diagnostics/patient/get/<str:patient_id>/', views.get_patient_by_id, name='get_patient_by_id'),
    path('_b_a_c_k_e_n_d_/Diagnostics/consolidated-data/', views.ConsolidatedDataView.as_view(), name='consolidated_data'),
    path("_b_a_c_k_e_n_d_/Diagnostics/generate-invoice/", generate_invoice, name="generate-invoice"),
    path("_b_a_c_k_e_n_d_/Diagnostics/get-invoices/", get_invoices, name="get-invoices"),
    path("_b_a_c_k_e_n_d_/Diagnostics/update-invoice/<str:invoice_number>/", update_invoice, name="update-invoice"),
    path("_b_a_c_k_e_n_d_/Diagnostics/delete-invoice/<str:invoice_id>/", delete_invoice, name="delete-invoice"),
    path('_b_a_c_k_e_n_d_/Diagnostics/salesdashboard/', views.salesdashboard, name='salesdashboard'),
    path('_b_a_c_k_e_n_d_/Diagnostics/getsalesmapping/',views.getsalesmapping, name='getsalesmapping'),
    path('_b_a_c_k_e_n_d_/Diagnostics/logisticdashboard/', views.logisticdashboard, name='logisticdashboard'),
    path('_b_a_c_k_e_n_d_/Diagnostics/search_refund/', views.search_refund, name='search_refund'),
    path('_b_a_c_k_e_n_d_/Diagnostics/verify_and_process_refund/', views.verify_and_process_refund, name='verify_and_process_refund'),
    path('_b_a_c_k_e_n_d_/Diagnostics/search_cancellation/', views.search_cancellation, name='search_cancellation'),
    path("_b_a_c_k_e_n_d_/Diagnostics/upload-pdf/", whatsapp.upload_pdf_to_gridfs, name="upload_pdf"),
    path("_b_a_c_k_e_n_d_/Diagnostics/get-file/<str:file_id>/", whatsapp.get_pdf_from_gridfs, name="get_pdf"),
    path("_b_a_c_k_e_n_d_/Diagnostics/send-whatsapp/", whatsapp.send_whatsapp_message, name="send_whatsapp"),
    path('_b_a_c_k_e_n_d_/Diagnostics/get_patients/', views.get_patients, name='get_patients'),
    path('_b_a_c_k_e_n_d_/Diagnostics/patient/update_billing/<str:patient_id>/', views.update_billing, name='update_billing'),
    path('_b_a_c_k_e_n_d_/Diagnostics/patient/tests/<str:patient_id>/<str:date>/', views.get_patient_tests, name='get_patient_tests'),
    path('_b_a_c_k_e_n_d_/Diagnostics/clinical_name/', views.clinical_name, name='create_organisation'),
    path('_b_a_c_k_e_n_d_/Diagnostics/clinical_name/last/', views.get_last_referrer_code, name='get_last_referrer_code'),
    path('_b_a_c_k_e_n_d_/Diagnostics/clinical-names/', views.ClinicalNameViewSet.as_view({'get': 'list'}), name='clinical-names-list'),
    path('_b_a_c_k_e_n_d_/Diagnostics/clinical-names/<str:referrerCode>/', views.ClinicalNameViewSet.as_view({'get': 'retrieve'}), name='clinical-name-detail'),
    path('_b_a_c_k_e_n_d_/Diagnostics/clinical-names/<str:referrerCode>/first_approve/', views.ClinicalNameViewSet.as_view({'patch': 'first_approve'}), name='clinical-name-first-approve'),
    path('_b_a_c_k_e_n_d_/Diagnostics/clinical-names/<str:referrerCode>/final_approve/', views.ClinicalNameViewSet.as_view({'patch': 'final_approve'}), name='clinical-name-final-approve'),
    path('_b_a_c_k_e_n_d_/Diagnostics/search_refund/', views.search_refund, name='search_refund'),
    path('_b_a_c_k_e_n_d_/Diagnostics/verify_and_process_refund/', views.verify_and_process_refund, name='verify_and_process_refund'),
    path('_b_a_c_k_e_n_d_/Diagnostics/generate_otp_refund/', views.generate_otp_refund, name='generate_otp_refund'),
    path('_b_a_c_k_e_n_d_/Diagnostics/generate_otp_cancellation/', views.generate_otp_cancellation, name='generate_otp_cancellation'),
    path('_b_a_c_k_e_n_d_/Diagnostics/search_cancellation/', views.search_cancellation, name='search_cancellation'),
    path('_b_a_c_k_e_n_d_/Diagnostics/verify_and_process_cancellation/', views.verify_and_process_cancellation, name='verify_and_process_cancellation'),
    path('_b_a_c_k_e_n_d_/Diagnostics/refund_cancellation_logs/', views.logs_api, name='refund_cancellation_logs'),
    path('_b_a_c_k_e_n_d_/Diagnostics/mou-preview/<str:file_id>/',views.preview_mou_file, name='preview_mou_file'),
    path('_b_a_c_k_e_n_d_/Diagnostics/dashboard-data/', views.dashboard_data, name='dashboard_data'),

]