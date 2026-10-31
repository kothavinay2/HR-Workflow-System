
import random
from datetime import date, timedelta

from database import get_connection
from models import DEPARTMENTS, ROLES, TASK_TEMPLATES

# Fixed seed for reproducibility
SEED = 20261022
random.seed(SEED)

TODAY = date(2026, 10, 30)


def random_date(start, end):
    days = (end - start).days
    return start + timedelta(days=random.randint(0, days))


def generate_data():
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Clear previous generated records in child-first order.
        tables = [
            "AuditEvent",
            "TaskDependency",
            "Approval",
            "AssetAssignment",
            "AccessRequest",
            "OffboardingCase",
            "TaskInstance",
            "OnboardingCase",
            "EmployeeDepartmentHistory",
            "Employee",
            "Manager",
            "Asset",
            "TaskTemplate",
            "Role",
            "Department"
        ]

        for table in tables:
            cur.execute(f"DELETE FROM {table}")

        # 1. Departments
        department_ids = []

        for i, name in enumerate(DEPARTMENTS, 1):
            dept_id = f"DEPT-{i:03d}"
            department_ids.append(dept_id)

            cur.execute("""
                INSERT INTO Department
                (department_id, department_name, location)
                VALUES (?, ?, ?)
            """, (dept_id, name, random.choice(
                ["Hyderabad", "Bengaluru", "Chennai", "Remote"]
            )))

        # 2. Roles
        role_ids = []

        for i, name in enumerate(ROLES, 1):
            role_id = f"ROLE-{i:03d}"
            role_ids.append(role_id)

            cur.execute("""
                INSERT INTO Role
                (role_id, role_name, description)
                VALUES (?, ?, ?)
            """, (role_id, name, f"{name} position"))

        # 3. Managers
        manager_ids = []

        for i in range(1, 51):
            manager_id = f"MGR-{i:04d}"
            manager_ids.append(manager_id)
            dept_id = department_ids[(i - 1) % 8]

            cur.execute("""
                INSERT INTO Manager
                (manager_id, manager_name, email, department_id)
                VALUES (?, ?, ?, ?)
            """, (
                manager_id,
                f"Manager {i}",
                f"manager{i}@company.example",
                dept_id
            ))

        # 4. Task templates
        template_ids = []

        for i, (name, owner, sla) in enumerate(TASK_TEMPLATES, 1):
            template_id = f"TMPL-{i:03d}"
            template_ids.append(template_id)

            cur.execute("""
                INSERT INTO TaskTemplate
                (template_id, task_name, department_owner, required, sla_days)
                VALUES (?, ?, ?, ?, ?)
            """, (template_id, name, owner, 1, sla))

        # 5. Employees and onboarding cases
        employee_ids = []
        onboarding_ids = []
        employee_info = {}

        for i in range(1, 501):
            employee_id = f"EMP-{i:06d}"
            onboarding_id = f"ONB-2026-{i:06d}"

            dept_id = random.choice(department_ids)
            role_id = random.choice(role_ids)

            # Deliberate missing-manager exception for employee 2.
            manager_id = None if i == 2 else random.choice(manager_ids)

            employment_type = random.choice(
                ["Permanent", "Permanent", "Contractor"]
            )
            work_location = random.choice(["Remote", "On-site"])

            # Thirty terminated employees for offboarding coverage.
            terminated = i <= 30
            employment_status = "Terminated" if terminated else "Active"

            hire_date = random_date(
                date(2026, 1, 1), date(2026, 10, 15)
            )

            termination_date = None
            if terminated:
                termination_date = (
                    hire_date + timedelta(days=random.randint(30, 180))
                )
                termination_date = min(termination_date, TODAY)

            cur.execute("""
                INSERT INTO Employee (
                    employee_id, employee_name, email,
                    department_id, role_id, manager_id,
                    employment_type, work_location,
                    employment_status, hire_date, termination_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                employee_id,
                f"Employee {i}",
                f"employee{i}@company.example",
                dept_id,
                role_id,
                manager_id,
                employment_type,
                work_location,
                employment_status,
                hire_date.isoformat(),
                termination_date.isoformat() if termination_date else None
            ))

            cur.execute("""
                INSERT INTO OnboardingCase
                (onboarding_id, employee_id, start_date, case_status)
                VALUES (?, ?, ?, ?)
            """, (
                onboarding_id,
                employee_id,
                hire_date.isoformat(),
                "Completed" if i % 5 != 0 else "In Progress"
            ))

            cur.execute("""
                INSERT INTO EmployeeDepartmentHistory
                (history_id, employee_id, department_id, effective_from, effective_to)
                VALUES (?, ?, ?, ?, NULL)
            """, (
                f"DEPHIST-{i:06d}",
                employee_id,
                dept_id,
                hire_date.isoformat()
            ))

            employee_ids.append(employee_id)
            onboarding_ids.append(onboarding_id)
            employee_info[employee_id] = {
                "onboarding_id": onboarding_id,
                "manager_id": manager_id,
                "hire_date": hire_date,
                "department_id": dept_id,
                "terminated": terminated,
                "termination_date": termination_date
            }

        # 6. Generate 4,000 tasks: 8 tasks per employee.
        task_ids = {}

        for employee_number, employee_id in enumerate(employee_ids, 1):
            info = employee_info[employee_id]
            onboarding_id = info["onboarding_id"]

            for j, (task_name, owner, sla) in enumerate(TASK_TEMPLATES, 1):
                task_id = f"TASK-ONB-{onboarding_id}-{j:03d}"
                due_date = info["hire_date"] + timedelta(days=sla)

                # Most tasks are completed; others remain open.
                completed = random.random() < 0.82
                status = "Completed" if completed else random.choice(
                    ["Pending", "In Progress"]
                )

                completed_at = None
                if completed:
                    completion_date = due_date - timedelta(
                        days=random.randint(0, 2)
                    )
                    completed_at = completion_date.isoformat()

                # Labelled anomaly: task 4 completed before task 2.
                if employee_number == 1 and j == 4:
                    status = "Completed"
                    completed_at = (
                        info["hire_date"] - timedelta(days=1)
                    ).isoformat()

                assigned_to = info["manager_id"] or random.choice(manager_ids)

                cur.execute("""
                    INSERT INTO TaskInstance (
                        task_id, onboarding_id, employee_id,
                        template_id, task_name, assigned_to,
                        task_status, due_date, completed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id,
                    onboarding_id,
                    employee_id,
                    template_ids[j - 1],
                    task_name,
                    assigned_to,
                    status,
                    due_date.isoformat(),
                    completed_at
                ))

                task_ids[(employee_id, j)] = task_id

                # Audit record for generated task completion.
                if status == "Completed":
                    cur.execute("""
                        INSERT INTO AuditEvent (
                            audit_id, employee_id, event_type,
                            event_description, actor
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        f"AUD-{TODAY.strftime('%Y%m%d')}-{employee_number:06d}{j:02d}",
                        employee_id,
                        "TASK_COMPLETED",
                        f"{task_name} completed",
                        assigned_to
                    ))

        # 7. Task dependencies.
        # Account creation requires identity verification.
        for employee_id in employee_ids:
            identity_task = task_ids[(employee_id, 2)]
            account_task = task_ids[(employee_id, 4)]

            cur.execute("""
                INSERT INTO TaskDependency
                (task_id, prerequisite_task_id)
                VALUES (?, ?)
            """, (account_task, identity_task))

        # 8. Assets: 600 records.
        asset_ids = []

        for i in range(1, 601):
            asset_id = f"AST-LAP-{i:06d}"

            cur.execute("""
                INSERT INTO Asset
                (asset_id, asset_type, asset_name, serial_number, asset_status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                asset_id,
                random.choice(["Laptop", "Monitor", "Keyboard", "Phone"]),
                f"Company Asset {i}",
                f"SN-{i:08d}",
                "Assigned" if i <= 300 else "Available"
            ))

            asset_ids.append(asset_id)

        # Assign first 300 assets to employees.
        for i in range(300):
            employee_id = employee_ids[i]
            asset_id = asset_ids[i]

            assigned_date = employee_info[employee_id]["hire_date"]

            cur.execute("""
                INSERT INTO AssetAssignment
                (assignment_id, asset_id, employee_id, assigned_date)
                VALUES (?, ?, ?, ?)
            """, (
                f"ASG-{i + 1:06d}",
                asset_id,
                employee_id,
                assigned_date.isoformat()
            ))

        # Labelled duplicate asset assignment for employee 3.
        cur.execute("""
            INSERT INTO AssetAssignment
            (assignment_id, asset_id, employee_id, assigned_date)
            VALUES (?, ?, ?, ?)
        """, (
            "ASG-000301",
            asset_ids[0],
            employee_ids[2],
            TODAY.isoformat()
        ))

        # 9. Access requests: 300 records.
        for i in range(1, 301):
            employee_id = employee_ids[i - 1]
            access_id = f"ACCREQ-2026-{i:06d}"

            terminated = employee_info[employee_id]["terminated"]

            # Employee 1 is terminated but deliberately keeps active access.
            if i == 1:
                access_status = "Provisioned"
                revoked_at = None
            elif terminated:
                access_status = "Revoked"
                revoked_at = TODAY.isoformat()
            else:
                access_status = random.choice(
                    ["Provisioned", "Pending", "Revoked"]
                )
                revoked_at = (
                    TODAY.isoformat() if access_status == "Revoked" else None
                )

            cur.execute("""
                INSERT INTO AccessRequest (
                    access_request_id, employee_id, system_name,
                    requested_date, access_status, revoked_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                access_id,
                employee_id,
                random.choice(["Email", "ERP", "CRM", "HR Portal"]),
                TODAY.isoformat(),
                access_status,
                revoked_at
            ))

            # Approval is required before provisioning.
            decision = "Approved" if access_status == "Provisioned" else (
                "Rejected" if access_status == "Revoked" else "Pending"
            )

            cur.execute("""
                INSERT INTO Approval (
                    approval_id, access_request_id, employee_id,
                    approver_id, decision, decision_date
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                f"APR-2026-{i:06d}",
                access_id,
                employee_id,
                random.choice(manager_ids),
                decision,
                TODAY.isoformat() if decision != "Pending" else None
            ))

        # 10. Offboarding cases for 30 terminated employees.
        for i in range(1, 31):
            employee_id = employee_ids[i - 1]
            termination_date = employee_info[employee_id]["termination_date"]

            cur.execute("""
                INSERT INTO OffboardingCase (
                    offboarding_id, employee_id,
                    initiated_date, last_working_day, case_status
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                f"OFF-2026-{i:06d}",
                employee_id,
                (termination_date - timedelta(days=7)).isoformat(),
                termination_date.isoformat(),
                "In Progress" if i == 1 else "Completed"
            ))

        conn.commit()

        print("Synthetic data generated successfully!")
        print("Departments:", len(DEPARTMENTS))
        print("Roles:", len(ROLES))
        print("Managers: 50")
        print("Employees: 500")
        print("Onboarding cases: 500")
        print("Tasks: 4000")
        print("Assets: 600")
        print("Access requests: 300")
        print("Offboarding cases: 30")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    generate_data()
