from app.models.reminder import Reminder

# When a real WhatsApp Business account is connected, these must match
# the exact template names you get approved in Meta Business Manager.
TEMPLATE_NAMES = {
    "confirm": "appointment_confirmation",
    "24h": "appointment_reminder_24h",
    "2h": "appointment_reminder_2h",
}


def build_reminder_payload(reminder: Reminder) -> tuple[str, str, dict]:
    """
    Loads the appointment and its related patient/doctor (via the
    relationships already defined on your models) and builds everything
    a WhatsAppService implementation needs to send the message.

    Returns:
        (phone_number, template_name, params)

    NOTE: adjust the attribute names below (patient.user.name, doctor.name,
    etc.) if they differ from your actual model field names.
    """
    appointment = reminder.appointment  # via Appointment.reminders backref
    patient = appointment.patient
    doctor = appointment.doctor

    patient_name = "Patient"
    if hasattr(patient, "user") and patient.user is not None:
        patient_name = getattr(patient.user, "full_name", None) or getattr(patient.user, "email", "Patient")

    doctor_name = getattr(doctor, "name", None) or "your doctor"

    params = {
        "patient_name": patient_name,
        "doctor_name": doctor_name,
        "date": appointment.appointment_date.strftime("%d %b"),
        "time": appointment.slot_time.strftime("%I:%M %p"),
    }

    template_name = TEMPLATE_NAMES[reminder.type.value]
    phone = patient.whatsapp_no

    if not phone:
        raise ValueError(f"Patient {patient.id} has no whatsapp_no on file")

    return phone, template_name, params