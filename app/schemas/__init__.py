from app.schemas.auth           import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.schemas.patient        import PatientCreate, PatientUpdate, PatientResponse
from app.schemas.doctor         import DoctorCreate, DoctorUpdate, DoctorResponse
from app.schemas.appointment    import AppointmentCreate, AppointmentUpdate, AppointmentResponse
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordUpdate, MedicalRecordResponse, PrescriptionItem
from app.schemas.reminder       import ReminderResponse