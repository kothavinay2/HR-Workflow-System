
import sqlite3
from pathlib import Path

# Database location
BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "hr_workflow.db"


def get_connection():
    DB_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_database():

    conn = get_connection()
    cursor = conn.cursor()

    # 1. Department
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Department (
        department_id TEXT PRIMARY KEY,
        department_name TEXT NOT NULL UNIQUE,
        location TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Role
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Role (
        role_id TEXT PRIMARY KEY,
        role_name TEXT NOT NULL UNIQUE,
        description TEXT
    )
    """)

    # 3. Manager
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Manager (
        manager_id TEXT PRIMARY KEY,
        manager_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        department_id TEXT NOT NULL,
        FOREIGN KEY (department_id)
        REFERENCES Department(department_id)
    )
    """)

    # 4. Employee
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Employee (
        employee_id TEXT PRIMARY KEY,
        employee_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        department_id TEXT NOT NULL,
        role_id TEXT NOT NULL,
        manager_id TEXT,
        employment_type TEXT NOT NULL
            CHECK(employment_type IN ('Permanent', 'Contractor')),
        work_location TEXT NOT NULL
            CHECK(work_location IN ('Remote', 'On-site')),
        employment_status TEXT NOT NULL DEFAULT 'Active'
            CHECK(employment_status IN ('Active', 'Terminated')),
        hire_date TEXT NOT NULL,
        termination_date TEXT,
        FOREIGN KEY (department_id)
        REFERENCES Department(department_id),
        FOREIGN KEY (role_id)
        REFERENCES Role(role_id),
        FOREIGN KEY (manager_id)
        REFERENCES Manager(manager_id)
    )
    """)

    # 5. Onboarding Case
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS OnboardingCase (
        onboarding_id TEXT PRIMARY KEY,
        employee_id TEXT NOT NULL UNIQUE,
        start_date TEXT NOT NULL,
        case_status TEXT NOT NULL DEFAULT 'Pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id)
        REFERENCES Employee(employee_id)
    )
    """)

    # 6. Task Template
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TaskTemplate (
        template_id TEXT PRIMARY KEY,
        task_name TEXT NOT NULL,
        department_owner TEXT NOT NULL,
        required INTEGER DEFAULT 1,
        sla_days INTEGER NOT NULL DEFAULT 3
    )
    """)

    # 7. Task Instance
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TaskInstance (
        task_id TEXT PRIMARY KEY,
        onboarding_id TEXT,
        employee_id TEXT NOT NULL,
        template_id TEXT NOT NULL,
        task_name TEXT NOT NULL,
        assigned_to TEXT,
        task_status TEXT NOT NULL DEFAULT 'Pending'
            CHECK(task_status IN
            ('Pending', 'In Progress', 'Completed', 'Cancelled')),
        due_date TEXT,
        completed_at TEXT,
        FOREIGN KEY (onboarding_id)
        REFERENCES OnboardingCase(onboarding_id),
        FOREIGN KEY (employee_id)
        REFERENCES Employee(employee_id),
        FOREIGN KEY (template_id)
        REFERENCES TaskTemplate(template_id),
        FOREIGN KEY (assigned_to)
        REFERENCES Manager(manager_id)
    )
    """)

    # 8. Task Dependency
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TaskDependency (
        task_id TEXT NOT NULL,
        prerequisite_task_id TEXT NOT NULL,
        PRIMARY KEY (task_id, prerequisite_task_id),
        CHECK(task_id <> prerequisite_task_id),
        FOREIGN KEY (task_id)
        REFERENCES TaskInstance(task_id),
        FOREIGN KEY (prerequisite_task_id)
        REFERENCES TaskInstance(task_id)
    )
    """)

    # 9. Asset
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Asset (
        asset_id TEXT PRIMARY KEY,
        asset_type TEXT NOT NULL,
        asset_name TEXT NOT NULL,
        serial_number TEXT UNIQUE,
        asset_status TEXT NOT NULL DEFAULT 'Available'
    )
    """)

    # 10. Asset Assignment
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS AssetAssignment (
        assignment_id TEXT PRIMARY KEY,
        asset_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        assigned_date TEXT NOT NULL,
        recovered_date TEXT,
        FOREIGN KEY (asset_id) REFERENCES Asset(asset_id),
        FOREIGN KEY (employee_id) REFERENCES Employee(employee_id)
    )
    """)

    # 11. Access Request
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS AccessRequest (
        access_request_id TEXT PRIMARY KEY,
        employee_id TEXT NOT NULL,
        system_name TEXT NOT NULL,
        requested_date TEXT NOT NULL,
        access_status TEXT NOT NULL DEFAULT 'Pending',
        revoked_at TEXT,
        FOREIGN KEY (employee_id)
        REFERENCES Employee(employee_id)
    )
    """)

    # 12. Approval
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Approval (
        approval_id TEXT PRIMARY KEY,
        access_request_id TEXT,
        employee_id TEXT NOT NULL,
        approver_id TEXT NOT NULL,
        decision TEXT NOT NULL DEFAULT 'Pending'
            CHECK(decision IN ('Pending', 'Approved', 'Rejected')),
        decision_date TEXT,
        FOREIGN KEY (access_request_id)
        REFERENCES AccessRequest(access_request_id),
        FOREIGN KEY (employee_id)
        REFERENCES Employee(employee_id),
        FOREIGN KEY (approver_id)
        REFERENCES Manager(manager_id)
    )
    """)

    # 13. Offboarding Case
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS OffboardingCase (
        offboarding_id TEXT PRIMARY KEY,
        employee_id TEXT NOT NULL,
        initiated_date TEXT NOT NULL,
        last_working_day TEXT NOT NULL,
        case_status TEXT NOT NULL DEFAULT 'Pending',
        FOREIGN KEY (employee_id)
        REFERENCES Employee(employee_id)
    )
    """)

    # 14. Audit Event
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS AuditEvent (
        audit_id TEXT PRIMARY KEY,
        employee_id TEXT,
        event_type TEXT NOT NULL,
        event_description TEXT,
        event_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        actor TEXT,
        FOREIGN KEY (employee_id)
        REFERENCES Employee(employee_id)
    )
    """)

    # 15. Employee Department History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS EmployeeDepartmentHistory (
        history_id TEXT PRIMARY KEY,
        employee_id TEXT NOT NULL,
        department_id TEXT NOT NULL,
        effective_from TEXT NOT NULL,
        effective_to TEXT,
        FOREIGN KEY (employee_id)
        REFERENCES Employee(employee_id),
        FOREIGN KEY (department_id)
        REFERENCES Department(department_id)
    )
    """)

    # Indexes
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_employee_department
    ON Employee(department_id)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_task_status
    ON TaskInstance(task_status)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_access_employee
    ON AccessRequest(employee_id)
    """)

    conn.commit()
    conn.close()

    print("HR database created successfully!")
    print(f"Database location: {DB_PATH}")


if __name__ == "__main__":
    create_database()
