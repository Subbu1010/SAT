package Alert;

import java.util.ArrayList;
import java.util.Objects;
import org.junit.Test;
import org.junit.runner.JUnitCore;
import org.junit.runner.Result;
import org.junit.runner.notification.Failure;
import static org.junit.Assert.*;

/*
We are building the backend for an incident alerting service. Each Alert represents a problem
raised against a monitored service. Times are measured in minutes since the start of the current
on-call window.

Definitions:
- An "Alert" is one reported problem for a service. It has an ID, a service name, a severity, a
  created_at time, and a resolved_at time.
- If an alert is "open" its resolved_at time is None.
- Once alert gets resolved, its resolved_at gets set to the time it was resolved.
- Severity is ranked: LOW is the lowest, then MEDIUM, then HIGH, then CRITICAL.
- An "AlertRouter" is the class used to manage all alerts for the on-call window.

To begin with, two tasks:
1) Read through and understand the code below. Take as much time as you need, and
   feel free to run the code.
2) The test for AlertRouter is not passing due to a bug in the code. Make the
   necessary changes to AlertRouter to fix the bug.
*/

/*
We are currently updating our system to track delivery attempts for alerts. As part of this
update, we have introduced the DeliveryAttempt class, which represents one try to notify an on-
call responder about an alert. Each DeliveryAttempt has a responder and a timestamp (in minutes
since the start of the on-call window).

To implement these changes, we need to add two methods to AlertRouter:

2.1) The recordAttempt method takes an alert ID and a DeliveryAttempt as inputs and associates
that attempt with the alert. If the attempt is recorded successfully, the method should return
true. If there is no alert with the given ID, the attempt should be ignored and the method
should return false.

2.2) The getAttemptCounts method returns a Map mapping each alert ID to the number of delivery
attempts recorded for it. Only include alerts that have at least one attempt. Omit alerts that
have none.

Example:
Input (alerts 42 and 77 already exist):
  recordAttempt(42, new DeliveryAttempt("alice", 5))  -> true
  recordAttempt(42, new DeliveryAttempt("bob", 30))   -> true
  recordAttempt(77, new DeliveryAttempt("alice", 10)) -> true
  recordAttempt(500, new DeliveryAttempt("carol", 0)) -> false (no alert with ID 500)
Output (returned by getAttemptCounts()):
  {42: 2, 77: 1}

Explanation:
Alert 42 received two delivery attempts and alert 77 received one, so the map reports 2 and 1.
The attempt for alert 500 was ignored because no such alert exists, and an alert with no
attempts does not appear at all.

To assist you in testing these new methods, we have provided the testRecordAttempt and
testGetAttemptCounts methods.
*/

/*
We are adding a check to catch on-call responders being paged too frequently for the same alert.
Our retry policy says that any two delivery attempts for the same alert must be at least
cooldown minutes apart. We want to find the alerts that break this policy.

3.1) Implement getBackoffViolations(cooldown). It returns the IDs of every alert for which at
least one pair of consecutive attempts, taken in time order, is spaced fewer than cooldown
minutes apart. The returned IDs must be sorted in ascending order.

Two attempts spaced exactly cooldown minutes apart are allowed: only a gap strictly less than
cooldown is a violation. An alert with fewer than two attempts can never break the policy.

Example:
Input:
  alert 1 has attempts recorded at minutes 0, 20, 10
  alert 2 has attempts recorded at minutes 0, 3
  cooldown = 5
Output (returned by getBackoffViolations(5)):
  [2]
Explanation:
Taken in time order, alert 1's attempts are 0, 10, 20, with gaps of 10 and 10 - both at
least 5, so alert 1 is compliant. Alert 2's two attempts are 3 minutes apart, which is
less than 5, so alert 2 breaks the policy.

The testGetBackoffViolations method is provided.
*/

public class Solution {
    enum Severity {
        LOW(1),
        MEDIUM(2),
        HIGH(3),
        CRITICAL(4);

        private final int rank;

        Severity(int rank) {
            this.rank = rank;
        }

        int getRank() {
            return rank;
        }
    }

    /** Data about a single reported problem for a service. */
    static class Alert {
        final int alertId;
        final String service;
        final Severity severity;
        final int createdAt;      // minutes since the start of the window
        Integer resolvedAt;       // minutes, or null while the alert is open

        Alert(int alertId, String service, Severity severity, int createdAt) {
            this(alertId, service, severity, createdAt, null);
        }

        Alert(int alertId, String service, Severity severity, int createdAt, Integer resolvedAt) {
            this.alertId = alertId;
            this.service = service;
            this.severity = severity;
            this.createdAt = createdAt;
            this.resolvedAt = resolvedAt;
        }

        @Override
        public boolean equals(Object other) {
            if (!(other instanceof Alert a)) {
                return false;
            }
            return alertId == a.alertId
                    && service.equals(a.service)
                    && severity == a.severity
                    && createdAt == a.createdAt
                    && Objects.equals(resolvedAt, a.resolvedAt);
        }

        @Override
        public int hashCode() {
            return Objects.hash(alertId, service, severity, createdAt, resolvedAt);
        }

        @Override
        public String toString() {
            return "Alert " + alertId + " [" + service + "] " + severity
                    + " created=" + createdAt + " resolved=" + resolvedAt;
        }
    }

    /** Data about one try to deliver an alert to an on-call responder. */
    static class DeliveryAttempt {
        final String responder;
        final int timestamp;     // minutes since the start of the window

        DeliveryAttempt(String responder, int timestamp) {
            this.responder = responder;
            this.timestamp = timestamp;
        }

        @Override
        public boolean equals(Object other) {
            if (!(other instanceof DeliveryAttempt a)) {
                return false;
            }
            return responder.equals(a.responder) && timestamp == a.timestamp;
        }

        @Override
        public int hashCode() {
            return Objects.hash(responder, timestamp);
        }

        @Override
        public String toString() {
            return "DeliveryAttempt [" + responder + "] at=" + timestamp;
        }
    }

    /** Data for managing incident alerts, and methods on-call staff use to query them. */
    static class AlertRouter {
        private final ArrayList<Alert> alerts = new ArrayList<>();

        /** Registers an alert for the current on-call window. */
        void addAlert(Alert alert) {
            alerts.add(alert);
        }

        /** Returns the alert with the given ID, or null if there is no such alert. */
        Alert getAlert(int alertId) {
            for (Alert alert : alerts) {
                if (alert.alertId == alertId) {
                    return alert;
                }
            }
            return null;
        }

        /** Returns whether the given service currently has at least one open alert. */
        boolean hasOpenAlert(String service) {
            for (Alert alert : alerts) {
                if (alert.service.equals(service)) {
                    return alert.resolvedAt == null;
                }
            }
            return false;
        }

        // TODO (2.1): Implement recordAttempt(int alertId, DeliveryAttempt attempt).
        // TODO (2.2): Implement getAttemptCounts().
        // TODO (3.1): Implement getBackoffViolations(int cooldown).
    }

    public static class TestSuite {
        @Test
        public void testAlert() {
            Alert a = new Alert(1, "auth", Severity.HIGH, 100);
            assertEquals(1, a.alertId);
            assertEquals("auth", a.service);
            assertEquals(Severity.HIGH, a.severity);
            assertEquals(100, a.createdAt);
            assertNull(a.resolvedAt);
        }

        @Test
        public void testHasOpenAlert() {
            AlertRouter router = new AlertRouter();
            router.addAlert(new Alert(1, "auth", Severity.HIGH, 100, 150)); // resolved
            router.addAlert(new Alert(2, "auth", Severity.LOW, 200, null)); // open
            router.addAlert(new Alert(3, "billing", Severity.CRITICAL, 50, 90)); // resolved
            router.addAlert(new Alert(4, "search", Severity.MEDIUM, 10, null)); // open
            // Harder case: "payments" has two resolved alerts before its only open one,
            // with another service's alert mixed in - the open alert is last in the list.
            router.addAlert(new Alert(5, "payments", Severity.CRITICAL, 300, 320)); // resolved
            router.addAlert(new Alert(6, "cdn", Severity.LOW, 10, null)); // different service
            router.addAlert(new Alert(7, "payments", Severity.HIGH, 330, 360)); // resolved
            router.addAlert(new Alert(8, "payments", Severity.MEDIUM, 400, null)); // open

            // "auth" has one resolved and one open alert -> it has an open alert.
            assertTrue(router.hasOpenAlert("auth"));
            // "billing" has only a resolved alert.
            assertFalse(router.hasOpenAlert("billing"));
            assertTrue(router.hasOpenAlert("search"));
            // A service with no alerts at all never has an open alert.
            assertFalse(router.hasOpenAlert("unknown"));
            // "payments" is open only because of its last alert.
            assertTrue(router.hasOpenAlert("payments"));
        }

        // Add these two methods inside the TestSuite class.
        @Test
        public void testRecordAttempt() {
            AlertRouter router = new AlertRouter();
            router.addAlert(new Alert(10, "auth", Severity.HIGH, 0, null));
            router.addAlert(new Alert(20, "billing", Severity.LOW, 0, null));

            assertTrue(router.recordAttempt(10, new DeliveryAttempt("alice", 5)));
            assertTrue(router.recordAttempt(10, new DeliveryAttempt("bob", 12)));
            assertTrue(router.recordAttempt(20, new DeliveryAttempt("alice", 8)));

            // No alert with this ID: the attempt should be ignored.
            assertFalse(router.recordAttempt(999, new DeliveryAttempt("alice", 9)));

            // Edge case: a resolved alert still exists, so recording an attempt against it
            // must still succeed - recordAttempt gates on existence, not on open/resolved.
            router.addAlert(new Alert(30, "search", Severity.CRITICAL, 100, 150)); // resolved
            assertTrue(router.recordAttempt(30, new DeliveryAttempt("dave", 200)));
            // Recording the same responder again is a separate attempt and still succeeds.
            assertTrue(router.recordAttempt(10, new DeliveryAttempt("alice", 40)));
        }

        @Test
        public void testGetAttemptCounts() {
            AlertRouter router = new AlertRouter();
            router.addAlert(new Alert(10, "auth", Severity.HIGH, 0, null));
            router.addAlert(new Alert(20, "billing", Severity.LOW, 0, null));
            router.addAlert(new Alert(30, "search", Severity.MEDIUM, 0, null)); // never attempted

            router.recordAttempt(10, new DeliveryAttempt("alice", 5));
            router.recordAttempt(10, new DeliveryAttempt("bob", 12));
            router.recordAttempt(10, new DeliveryAttempt("alice", 20));
            router.recordAttempt(20, new DeliveryAttempt("carol", 8));
            router.recordAttempt(999, new DeliveryAttempt("alice", 9)); // ignored: no such alert

            java.util.Map<Integer, Integer> expected = new java.util.HashMap<>();
            expected.put(10, 3);
            expected.put(20, 1);
            assertEquals(expected, router.getAttemptCounts());
        }

        // Add the test below inside the TestSuite class.
        @Test
        public void testGetBackoffViolations() {
            AlertRouter router = new AlertRouter();
            for (int aid : new int[] {1, 2, 3, 4, 5}) {
                router.addAlert(new Alert(aid, "svc" + aid, Severity.HIGH, 0, null));
            }

            // cooldown = 5
            // alert 1 -> recorded out of order; in time order 0, 10, 20 (gaps 10, 10) -> compliant
            router.recordAttempt(1, new DeliveryAttempt("a", 0));
            router.recordAttempt(1, new DeliveryAttempt("a", 20));
            router.recordAttempt(1, new DeliveryAttempt("a", 10));
            // alert 2 -> 0, 3 (gap 3 < 5) -> violation
            router.recordAttempt(2, new DeliveryAttempt("a", 0));
            router.recordAttempt(2, new DeliveryAttempt("a", 3));
            // alert 3 -> in time order 100, 105, 110 (gaps exactly 5) -> compliant (boundary)
            router.recordAttempt(3, new DeliveryAttempt("a", 100));
            router.recordAttempt(3, new DeliveryAttempt("a", 110));
            router.recordAttempt(3, new DeliveryAttempt("a", 105));
            // alert 4 -> a single attempt -> can never violate
            router.recordAttempt(4, new DeliveryAttempt("a", 50));
            // alert 5 -> recorded out of order; in time order 0, 4, 9 (gap 4 < 5) -> violation
            router.recordAttempt(5, new DeliveryAttempt("a", 0));
            router.recordAttempt(5, new DeliveryAttempt("a", 9));
            router.recordAttempt(5, new DeliveryAttempt("a", 4));

            java.util.List<Integer> expected = new java.util.ArrayList<>();
            expected.add(2);
            expected.add(5);
            assertEquals(expected, router.getBackoffViolations(5));
        }
    }

    public static void main(String[] args) {
        Result result = JUnitCore.runClasses(TestSuite.class);
        for (Failure failure : result.getFailures()) {
            System.out.println(failure.toString());
        }
        if (result.wasSuccessful()) {
            System.out.println("All tests passed successfully.");
        } else {
            System.err.println("Tests failed: " + result.getFailureCount() + " test(s) failed.");
            System.exit(1);
        }
    }
}
