
import sqlite3
from datetime import date, datetime

from database import get_connection


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def log_audit(employee_id, event_type, description, actor="HR Admin"):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO AuditEvent
        (employee_id, event_type, event_description,
         event_timestamp, actor)
        VALUES (?, ?, ?, datetime('now'), ?)
    """, (employee_id, event_type, description, actor))

    conn.commit()
    conn.close()


# =====================================================
# ONBOARDING
# =====================================================

def create_onboarding(employee_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT employment_status
            FROM Employee
            WHERE employee_id = ?
        """, (employee_id,))

        employee = cursor.fetchone()

        if not employee:
            raise ValueError("Employee not found.")

        if employee[0] != "Active":
            raise ValueError("Only active employees can be onboarded.")

        cursor.execute("""
            SELECT onboarding_id
            FROM OnboardingCase
            WHERE employee_id = ?
        """, (employee_id,))

        if cursor.fetchone():
            raise ValueError("An onboarding case already exists.")

        year = datetime.now().year

        cursor.execute("""
            SELECT COUNT(*)
            FROM OnboardingCase
            WHERE onboarding_id LIKE ?
        """, (f"ONB-{year}-%",))

        count = cursor.fetchone()[0] + 1
        onboarding_id = f"ONB-{year}-{count:06d}"

        cursor.execute("""
            INSERT INTO OnboardingCase
            (onboarding_id, employee_id, start_date, case_status)
            VALUES (?, ?, date('now'), 'In Progress')
        """, (onboarding_id, employee_id))

        cursor.execute("""
            SELECT template_id, task_name
            FROM TaskTemplate
            ORDER BY template_id
        """)

        templates = cursor.fetchall()

        for index, template in enumerate(templates, start=1):
            template_id = template[0]
            task_name = template[1]

            task_id = (
                f"TASK-ONB-{onboarding_id}-{index:03d}"
            )

            cursor.execute("""
                SELECT sla_days
                FROM TaskTemplate
                WHERE template_id = ?
            """, (template_id,))

            sla_days = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO TaskInstance
                (task_id, onboarding_id, employee_id,
                 template_id, task_name, task_status, due_date)
                VALUES (?, ?, ?, ?, ?, 'Pending',
                        date('now', '+' || ? || ' days'))
            """, (
                task_id,
                onboarding_id,
                employee_id,
                template_id,
                task_name,
                sla_days
            ))

        conn.commit()

        setup_task_dependencies(onboarding_id)

        log_audit(
            employee_id,
            "ONBOARDING_CREATED",
            f"Onboarding case {onboarding_id} created."
        )

        return onboarding_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def setup_task_dependencies(onboarding_id):
    conn = get_connection()
    cursor = conn.cursor()

    dependencies = [
        ("Background Verification", "Identity Verification"),
        ("Identity Verification", "Create Email Account"),
        ("Manager Approval", "Create System Access"),
        ("Employee ID Creation", "Create System Access"),
        ("Create Email Account", "Create System Access")
    ]

    try:
        for prerequisite_name, dependent_name in dependencies:

            cursor.execute("""
                SELECT task_id
                FROM TaskInstance
                WHERE onboarding_id = ?
                AND task_name = ?
            """, (onboarding_id, prerequisite_name))

            prerequisite = cursor.fetchone()

            cursor.execute("""
                SELECT task_id
                FROM TaskInstance
                WHERE onboarding_id = ?
                AND task_name = ?
            """, (onboarding_id, dependent_name))

            dependent = cursor.fetchone()

            if prerequisite and dependent:
                cursor.execute("""
                    INSERT OR IGNORE INTO TaskDependency
                    (task_id, prerequisite_task_id)
                    VALUES (?, ?)
                """, (dependent[0], prerequisite[0]))

        conn.commit()

    finally:
        conn.close()


def get_onboarding_cases():
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                o.onboarding_id,
                o.employee_id,
                e.employee_name,
                o.start_date,
                o.case_status
            FROM OnboardingCase o
            JOIN Employee e
                ON o.employee_id = e.employee_id
            ORDER BY o.start_date DESC
        """)

        return cursor.fetchall()

    finally:
        conn.close()


def get_onboarding_tasks(onboarding_id):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                task_id,
                task_name,
                task_status,
                due_date,
                completed_at
            FROM TaskInstance
            WHERE onboarding_id = ?
            ORDER BY task_id
        """, (onboarding_id,))

        return cursor.fetchall()

    finally:
        conn.close()


def update_task_status(
    task_id,
    new_status,
    allow_override=False,
    override_reason=None,
    actor="HR Admin"
):
    allowed_statuses = [
        "Pending",
        "In Progress",
        "Completed",
        "Cancelled"
    ]

    if new_status not in allowed_statuses:
        raise ValueError("Invalid task status.")

    if allow_override and not override_reason:
        raise ValueError("Please provide an override reason.")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT employee_id, onboarding_id, task_name, task_status
            FROM TaskInstance
            WHERE task_id = ?
        """, (task_id,))

        task = cursor.fetchone()

        if not task:
            raise ValueError("Task not found.")

        employee_id = task[0]
        onboarding_id = task[1]
        task_name = task[2]
        old_status = task[3]

        if new_status == "Completed" and not allow_override:

            cursor.execute("""
                SELECT d.prerequisite_task_id, t.task_name,
                       t.task_status
                FROM TaskDependency d
                JOIN TaskInstance t
                    ON d.prerequisite_task_id = t.task_id
                WHERE d.task_id = ?
            """, (task_id,))

            prerequisites = cursor.fetchall()

            incomplete = [
                item[1] for item in prerequisites
                if item[2] != "Completed"
            ]

            if incomplete:
                raise ValueError(
                    "Complete prerequisite tasks first: "
                    + ", ".join(incomplete)
                )

        if old_status == "Completed" and new_status != "Completed":
            if not allow_override:
                raise ValueError(
                    "Reopening a completed task requires HR override."
                )

        cursor.execute("""
            UPDATE TaskInstance
            SET task_status = ?,
                completed_at = CASE
                    WHEN ? = 'Completed' THEN datetime('now')
                    ELSE NULL
                END
            WHERE task_id = ?
        """, (new_status, new_status, task_id))

        if onboarding_id:
            cursor.execute("""
                SELECT COUNT(*),
                       SUM(CASE WHEN task_status = 'Completed'
                           THEN 1 ELSE 0 END)
                FROM TaskInstance
                WHERE onboarding_id = ?
            """, (onboarding_id,))

            total, completed = cursor.fetchone()
            completed = completed or 0

            if total > 0 and completed == total:
                case_status = "Completed"
            else:
                case_status = "In Progress"

            cursor.execute("""
                UPDATE OnboardingCase
                SET case_status = ?
                WHERE onboarding_id = ?
            """, (case_status, onboarding_id))

        if allow_override:
            cursor.execute("""
                INSERT INTO AuditEvent
                (employee_id, event_type, event_description,
                 event_timestamp, actor)
                VALUES (?, ?, ?, datetime('now'), ?)
            """, (
                employee_id,
                "HR_OVERRIDE",
                f"Task {task_id} changed from {old_status} "
                f"to {new_status}. Reason: {override_reason}",
                actor
            ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# OFFBOARDING
# =====================================================


def create_offboarding(employee_id, last_working_day):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        employee = cursor.execute("""
            SELECT employment_status
            FROM Employee
            WHERE employee_id = ?
        """, (employee_id,)).fetchone()

        if not employee:
            raise ValueError("Employee not found.")

        if employee[0] != "Active":
            raise ValueError("Employee is not active.")

        existing = cursor.execute("""
            SELECT offboarding_id
            FROM OffboardingCase
            WHERE employee_id = ?
            AND case_status NOT IN ('Completed', 'Cancelled')
        """, (employee_id,)).fetchone()

        if existing:
            raise ValueError("An active offboarding case already exists.")

        year = datetime.now().year
        prefix = f"OFF-{year}-"

        cursor.execute("""
            SELECT COUNT(*)
            FROM OffboardingCase
            WHERE offboarding_id LIKE ?
        """, (prefix + "%",))

        count = cursor.fetchone()[0] + 1
        offboarding_id = f"{prefix}{count:06d}"

        cursor.execute("""
            INSERT INTO OffboardingCase (
                offboarding_id,
                employee_id,
                initiated_date,
                last_working_day,
                case_status
            )
            VALUES (?, ?, date('now'), ?, 'In Progress')
        """, (
            offboarding_id,
            employee_id,
            last_working_day
        ))

        cursor.execute("""
            INSERT INTO AuditEvent (
                employee_id,
                event_type,
                event_description,
                event_timestamp,
                actor
            )
            VALUES (?, ?, ?, datetime('now'), ?)
        """, (
            employee_id,
            "OFFBOARDING_CREATED",
            f"Offboarding case {offboarding_id} created.",
            "HR Admin"
        ))

        conn.commit()
        return offboarding_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# COMPLETE OFFBOARDING
# =====================================================

def complete_offboarding(offboarding_id, actor="HR Admin"):

    conn = get_connection()
    cursor = conn.cursor()

    try:
        case = cursor.execute("""
            SELECT employee_id, last_working_day, case_status
            FROM OffboardingCase
            WHERE offboarding_id = ?
        """, (offboarding_id,)).fetchone()

        if not case:
            raise ValueError("Offboarding case not found.")

        employee_id, last_working_day, case_status = case

        if case_status in ("Completed", "Cancelled"):
            raise ValueError("This offboarding case is already closed.")

        # Check unrecovered assets
        pending_assets = cursor.execute("""
            SELECT COUNT(*)
            FROM AssetAssignment
            WHERE employee_id = ?
            AND recovered_date IS NULL
        """, (employee_id,)).fetchone()[0]

        if pending_assets > 0:
            raise ValueError(
                f"{pending_assets} company asset(s) are still pending recovery."
            )

        # Check active system access
        pending_access = cursor.execute("""
            SELECT COUNT(*)
            FROM AccessRequest
            WHERE employee_id = ?
            AND access_status != 'Revoked'
        """, (employee_id,)).fetchone()[0]

        if pending_access > 0:
            raise ValueError(
                f"{pending_access} system access request(s) "
                "are still not revoked."
            )

        # Update employee status
        cursor.execute("""
            UPDATE Employee
            SET employment_status = 'Terminated',
                termination_date = ?
            WHERE employee_id = ?
        """, (last_working_day, employee_id))

        # Complete offboarding case
        cursor.execute("""
            UPDATE OffboardingCase
            SET case_status = 'Completed'
            WHERE offboarding_id = ?
        """, (offboarding_id,))

        # Audit record
        cursor.execute("""
            INSERT INTO AuditEvent (
                employee_id,
                event_type,
                event_description,
                event_timestamp,
                actor
            )
            VALUES (?, ?, ?, datetime('now'), ?)
        """, (
            employee_id,
            "OFFBOARDING_COMPLETED",
            f"Offboarding case {offboarding_id} completed. "
            f"Employee terminated on {last_working_day}.",
            actor
        ))

        conn.commit()

        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()




def get_offboarding_cases():
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                o.offboarding_id,
                o.employee_id,
                e.employee_name,
                o.initiated_date,
                o.last_working_day,
                o.case_status
            FROM OffboardingCase o
            JOIN Employee e
                ON o.employee_id = e.employee_id
            ORDER BY o.initiated_date DESC
        """)

        return cursor.fetchall()

    finally:
        conn.close()


def get_employee_assets(employee_id):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                aa.assignment_id,
                a.asset_id,
                a.asset_type,
                a.asset_name,
                a.serial_number,
                aa.assigned_date,
                aa.recovered_date
            FROM AssetAssignment aa
            JOIN Asset a
                ON aa.asset_id = a.asset_id
            WHERE aa.employee_id = ?
            ORDER BY aa.assigned_date DESC
        """, (employee_id,))

        return cursor.fetchall()

    finally:
        conn.close()


def get_employee_access(employee_id):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                access_request_id,
                system_name,
                requested_date,
                access_status,
                revoked_at
            FROM AccessRequest
            WHERE employee_id = ?
            ORDER BY requested_date DESC
        """, (employee_id,))

        return cursor.fetchall()

    finally:
        conn.close()


def recover_employee_asset(assignment_id, actor="HR Admin"):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT employee_id, asset_id, recovered_date
            FROM AssetAssignment
            WHERE assignment_id = ?
        """, (assignment_id,))

        assignment = cursor.fetchone()

        if not assignment:
            raise ValueError("Asset assignment not found.")

        employee_id, asset_id, recovered_date = assignment

        if recovered_date:
            raise ValueError("This asset has already been recovered.")

        cursor.execute("""
            UPDATE AssetAssignment
            SET recovered_date = date('now')
            WHERE assignment_id = ?
        """, (assignment_id,))

        cursor.execute("""
            UPDATE Asset
            SET asset_status = 'Available'
            WHERE asset_id = ?
        """, (asset_id,))

        cursor.execute("""
            INSERT INTO AuditEvent
            (employee_id, event_type, event_description,
             event_timestamp, actor)
            VALUES (?, ?, ?, datetime('now'), ?)
        """, (
            employee_id,
            "ASSET_RECOVERED",
            f"Asset {asset_id} recovered.",
            actor
        ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def revoke_employee_access(access_request_id, actor="HR Admin"):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT employee_id, access_status
            FROM AccessRequest
            WHERE access_request_id = ?
        """, (access_request_id,))

        access = cursor.fetchone()

        if not access:
            raise ValueError("Access request not found.")

        employee_id, access_status = access

        if access_status == "Revoked":
            raise ValueError("Access has already been revoked.")

        cursor.execute("""
            UPDATE AccessRequest
            SET access_status = 'Revoked',
                revoked_at = datetime('now')
            WHERE access_request_id = ?
        """, (access_request_id,))

        cursor.execute("""
            INSERT INTO AuditEvent
            (employee_id, event_type, event_description,
             event_timestamp, actor)
            VALUES (?, ?, ?, datetime('now'), ?)
        """, (
            employee_id,
            "ACCESS_REVOKED",
            f"Access request {access_request_id} revoked.",
            actor
        ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
