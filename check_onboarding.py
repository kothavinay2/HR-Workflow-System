
from database import get_connection

conn = get_connection()
cursor = conn.cursor()

employee_id = "EMP-000034"

try:
    # Check employee details
    cursor.execute("""
        SELECT employee_id, employee_name, employment_status
        FROM Employee
        WHERE employee_id = ?
    """, (employee_id,))

    employee = cursor.fetchone()

    print("\n========== EMPLOYEE DETAILS ==========")

    if employee:
        print("Employee ID:", employee["employee_id"])
        print("Employee Name:", employee["employee_name"])
        print("Employment Status:", employee["employment_status"])
    else:
        print("Employee not found.")

    # Check all offboarding cases
    cursor.execute("""
        SELECT offboarding_id, case_status, last_working_day
        FROM OffboardingCase
        WHERE employee_id = ?
    """, (employee_id,))

    cases = cursor.fetchall()

    print("\n========== OFFBOARDING DETAILS ==========")

    if cases:
        for case in cases:
            print("Offboarding ID:", case["offboarding_id"])
            print("Case Status:", case["case_status"])
            print("Last Working Day:", case["last_working_day"])
            print("-----------------------------------")
    else:
        print("No offboarding cases found.")

finally:
    conn.close()
