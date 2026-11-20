import java.util.*;
import java.util.stream.*;

/*
We are building the back-end for a clinic appointment management system.
The system tracks doctors, appointments, and patient visits.

Definitions:
* A "doctor" has: doctorId, name.
* An "appointment" has: appointmentId, doctorId, patientId,
  durationMinutes, status.
* AppointmentStatus is one of: SCHEDULED, COMPLETED, CANCELLED, NO_SHOW.
* ClinicManager manages doctors, appointments, and provides statistics.
* DoctorVisitSummary represents totalVisits, totalMinutes, and busiestVisitType.

1-1) Read through and understand the code below.
1-2) The test for ClinicManager is not passing due to a bug in the code.
     Make the necessary changes to ClinicManager to fix the bug.

We are extending the platform to track patient visits to doctors.
Each PatientVisit represents one patient's visit to a doctor:
- visitId: unique identifier for the visit
- patientId: the patient who visited
- doctorId: the doctor the patient visited
- startTime: start time of the visit, minutes from start of day
- durationMinutes: how long the visit lasted, in minutes
- visitType: CONSULTATION, FOLLOWUP, EMERGENCY

2.1) addPatientVisit stores a visit. Ignore visits for unknown doctors.
2.2) getAverageVisitDurationByType returns a map from visit types to the
     doctor's average visit duration in minutes. Include only types with visits;
     return an empty map for doctors with no visits.

3) getDoctorVisitSummary returns a map of each doctorId to a DoctorVisitSummary.
   Include all doctors, even those with no visits (0, 0, null).
   The busiest visit type is the type with the most visits; ties are resolved
   alphabetically by visit type name.
*/

enum AppointmentStatus {
    SCHEDULED, COMPLETED, CANCELLED, NO_SHOW
}

class Doctor {
    public int doctorId;
    public String name;

    public Doctor(int doctorId, String name) {
        this.doctorId = doctorId;
        this.name = name;
    }
}

class DoctorVisitSummary {
    Integer totalVisits;
    Integer totalMinutes;
    VisitType busiestVisitType;

    DoctorVisitSummary(Integer totalVisits, Integer totalMinutes, VisitType busiestVisitType) {
        this.totalVisits = totalVisits;
        this.totalMinutes = totalMinutes;
        this.busiestVisitType = busiestVisitType;
    }
}

enum VisitType {
    CONSULTATION, FOLLOWUP, EMERGENCY
}

class PatientVisit {
    int visitId;
    int patientId;
    int doctorId;
    int startTime;
    int durationMinutes;
    VisitType visitType;

    PatientVisit(int visitId, int patientId, int doctorId,
                 int startTime, int durationMinutes, VisitType visitType) {
        this.visitId = visitId;
        this.patientId = patientId;
        this.doctorId = doctorId;
        this.startTime = startTime;
        this.durationMinutes = durationMinutes;
        this.visitType = visitType;
    }
}

class Appointment {
    public int appointmentId;
    public int doctorId;
    public int patientId;
    public int durationMinutes;
    public AppointmentStatus status;

    public Appointment(int appointmentId, int doctorId, int patientId,
                       int durationMinutes, AppointmentStatus status) {
        this.appointmentId = appointmentId;
        this.doctorId = doctorId;
        this.patientId = patientId;
        this.durationMinutes = durationMinutes;
        this.status = status;
    }
}

class AppointmentStats {
    public int totalAppointments;
    public int completedAppointments;
    public double noShowRate;

    public AppointmentStats(int totalAppointments, int completedAppointments, double noShowRate) {
        this.totalAppointments = totalAppointments;
        this.completedAppointments = completedAppointments;
        this.noShowRate = noShowRate;
    }
}

class ClinicManager {
    public Map<Integer, Doctor> doctors;
    public List<Appointment> appointments;

    public ClinicManager() {
        doctors = new HashMap<>();
        appointments = new ArrayList<>();
    }

    public void addDoctor(Doctor doctor) {
        doctors.put(doctor.doctorId, doctor);
    }

    public void addAppointment(Appointment appointment) {
        appointments.add(appointment);
    }

    public AppointmentStats getAppointmentStatistics() {
        int total = appointments.size();
        int completed = 0;

        for (Appointment a : appointments) {
            if (a.status == AppointmentStatus.COMPLETED || a.status == AppointmentStatus.SCHEDULED) {
                completed++;
            }
        }

        int noShows = 0;
        for (Appointment a : appointments) {
            if (a.status == AppointmentStatus.NO_SHOW) {
                noShows++;
            }
        }

        double noShowRate;
        if (total > 0) {
            noShowRate = (double) noShows / total;
        } else {
            noShowRate = 0.0;
        }
        return new AppointmentStats(total, completed, noShowRate);
    }

    // TODO 2.1: Add addPatientVisit(PatientVisit visit).
    // TODO 2.2: Add getAverageVisitDurationByType(int doctorId).
    // TODO 3: Add getDoctorVisitSummary().
}

public class ClinicSolution {
    public static void main(String[] args) {
        testGetAppointmentStatistics();
        testAddPatientVisit();
        testGetAverageVisitDurationByType();
        testGetDoctorVisitSummary();
        System.out.println("All tests pass!");
    }

    public static void testGetAppointmentStatistics() {
        System.out.println("Running testGetAppointmentStatistics");
        ClinicManager cm = new ClinicManager();
        cm.addAppointment(new Appointment(1, 10, 100, 30, AppointmentStatus.COMPLETED));
        cm.addAppointment(new Appointment(2, 10, 101, 45, AppointmentStatus.COMPLETED));
        cm.addAppointment(new Appointment(3, 10, 102, 30, AppointmentStatus.NO_SHOW));
        cm.addAppointment(new Appointment(4, 10, 103, 60, AppointmentStatus.CANCELLED));
        cm.addAppointment(new Appointment(5, 10, 104, 30, AppointmentStatus.SCHEDULED));

        AppointmentStats stats = cm.getAppointmentStatistics();
        assert stats.totalAppointments == 5 : "totalAppointments should be 5, was " + stats.totalAppointments;
        assert stats.completedAppointments == 2 : "completedAppointments should be 2, was " + stats.completedAppointments;
        assert Math.abs(stats.noShowRate - 0.2) < 1e-4 : "noShowRate should be 0.2, was " + stats.noShowRate;
    }

    static void testAddPatientVisit() {
        System.out.println("Running testAddPatientVisit");
        ClinicManager cm = new ClinicManager();
        cm.addDoctor(new Doctor(1, "dr_smith"));
        cm.addDoctor(new Doctor(2, "dr_jones"));
        cm.addPatientVisit(new PatientVisit(1, 100, 1, 540, 30, VisitType.CONSULTATION));
        cm.addPatientVisit(new PatientVisit(2, 101, 2, 600, 45, VisitType.FOLLOWUP));
        // unknown doctor ignored
        cm.addPatientVisit(new PatientVisit(3, 102, 99, 660, 30, VisitType.EMERGENCY));
    }

    static void testGetAverageVisitDurationByType() {
        System.out.println("Running testGetAverageVisitDurationByType");
        ClinicManager cm = new ClinicManager();
        cm.addDoctor(new Doctor(1, "dr_smith"));
        cm.addDoctor(new Doctor(2, "dr_jones"));
        cm.addPatientVisit(new PatientVisit(1, 100, 1, 540, 30, VisitType.CONSULTATION));
        cm.addPatientVisit(new PatientVisit(2, 101, 1, 600, 50, VisitType.CONSULTATION));
        cm.addPatientVisit(new PatientVisit(3, 102, 1, 660, 20, VisitType.FOLLOWUP));
        cm.addPatientVisit(new PatientVisit(4, 103, 2, 540, 40, VisitType.EMERGENCY));

        Map<VisitType, Double> avg1 = cm.getAverageVisitDurationByType(1);
        assert Math.abs(40.0 - avg1.get(VisitType.CONSULTATION)) < 1e-4 : "Expected 40.0 for CONSULTATION";
        assert Math.abs(20.0 - avg1.get(VisitType.FOLLOWUP)) < 1e-4 : "Expected 20.0 for FOLLOWUP";
        assert !avg1.containsKey(VisitType.EMERGENCY) : "EMERGENCY should not be in avg1";

        Map<VisitType, Double> avg2 = cm.getAverageVisitDurationByType(2);
        assert Math.abs(40.0 - avg2.get(VisitType.EMERGENCY)) < 1e-4 : "Expected 40.0 for EMERGENCY";
        assert !avg2.containsKey(VisitType.CONSULTATION) : "CONSULTATION should not be in avg2";
        assert !avg2.containsKey(VisitType.FOLLOWUP) : "FOLLOWUP should not be in avg2";

        // doctor with no visits
        cm.addDoctor(new Doctor(3, "dr_brown"));
        assert cm.getAverageVisitDurationByType(3).isEmpty() : "Expected empty map for doctor with no visits";
    }

    // Also, add a call to testGetDoctorVisitSummary() in the main method.
    static void testGetDoctorVisitSummary() {
        System.out.println("Running testGetDoctorVisitSummary");
        ClinicManager cm = new ClinicManager();
        for (int did : new int[]{1, 2, 3, 4}) {
            cm.addDoctor(new Doctor(did, "doctor" + did));
        }

        // doctor 1: 4 visits, 125 total minutes
        // CONSULTATION x2, FOLLOWUP x1, EMERGENCY x1
        // busiest = CONSULTATION (2 visits, clear winner)
        cm.addPatientVisit(new PatientVisit(1, 100, 1, 540, 30, VisitType.CONSULTATION));
        cm.addPatientVisit(new PatientVisit(2, 101, 1, 600, 45, VisitType.CONSULTATION));
        cm.addPatientVisit(new PatientVisit(3, 102, 1, 660, 20, VisitType.FOLLOWUP));
        cm.addPatientVisit(new PatientVisit(4, 103, 1, 720, 30, VisitType.EMERGENCY));

        // doctor 2: 2 visits, 90 total minutes
        // FOLLOWUP x1, EMERGENCY x1 (tied)
        // tiebreak alphabetically -> EMERGENCY wins (E < F)
        cm.addPatientVisit(new PatientVisit(5, 104, 2, 540, 40, VisitType.FOLLOWUP));
        cm.addPatientVisit(new PatientVisit(6, 105, 2, 600, 50, VisitType.EMERGENCY));

        // doctor 3: no visits -> zeroed summary

        // doctor 4: 2 visits, CONSULTATION x1, FOLLOWUP x1 (tied)
        // tiebreak alphabetically -> CONSULTATION wins (C < F)
        cm.addPatientVisit(new PatientVisit(7, 106, 4, 540, 30, VisitType.CONSULTATION));
        cm.addPatientVisit(new PatientVisit(8, 107, 4, 600, 30, VisitType.FOLLOWUP));

        Map<Integer, DoctorVisitSummary> summary = cm.getDoctorVisitSummary();

        // doctor 1
        assert Integer.valueOf(4).equals(summary.get(1).totalVisits) : "doctor1 totalVisits";
        assert Integer.valueOf(125).equals(summary.get(1).totalMinutes) : "doctor1 totalMinutes";
        assert summary.get(1).busiestVisitType == VisitType.CONSULTATION : "doctor1 busiestVisitType";

        // doctor 2 - tiebreak by name -> EMERGENCY wins
        assert Integer.valueOf(2).equals(summary.get(2).totalVisits) : "doctor2 totalVisits";
        assert Integer.valueOf(90).equals(summary.get(2).totalMinutes) : "doctor2 totalMinutes";
        assert summary.get(2).busiestVisitType == VisitType.EMERGENCY : "doctor2 busiestVisitType";

        // doctor 3 - zero visits
        assert Integer.valueOf(0).equals(summary.get(3).totalVisits) : "doctor3 totalVisits";
        assert Integer.valueOf(0).equals(summary.get(3).totalMinutes) : "doctor3 totalMinutes";
        assert summary.get(3).busiestVisitType == null : "doctor3 busiestVisitType";

        // doctor 4 - tiebreak by name -> CONSULTATION wins
        assert Integer.valueOf(2).equals(summary.get(4).totalVisits) : "doctor4 totalVisits";
        assert Integer.valueOf(60).equals(summary.get(4).totalMinutes) : "doctor4 totalMinutes";
        assert summary.get(4).busiestVisitType == VisitType.CONSULTATION : "doctor4 busiestVisitType";
    }
}
