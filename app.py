
import streamlit as st
import pandas as pd

from database import get_connection

from workflow import (
    create_offboarding,
    get_offboarding_cases,
    get_employee_assets,
    get_employee_access,
    recover_employee_asset,
    revoke_employee_access,
    complete_offboarding
)


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="HR Management System",
    page_icon="👥",
    layout="wide"
)

st.title("HR Onboarding & Offboarding System")
st.caption("Employee Management Portal")


# ==================================================
# DATABASE FUNCTIONS
# ==================================================

def get_employees():
    conn = get_connection()

    try:
        return pd.read_sql_query("""
            SELECT
                e.employee_id,
                e.employee_name,
                e.email,
                d.department_name,
                r.role_name,
                e.manager_id,
                e.employment_type,
                e.work_location,
                e.employment_status,
                e.hire_date
            FROM Employee e
            LEFT JOIN Department d
                ON e.department_id = d.department_id
            LEFT JOIN Role r
                ON e.role_id = r.role_id
            ORDER BY e.employee_id
        """, conn)

    finally:
        conn.close()


def get_options(table, id_col, name_col):

    allowed = {
        "Department": ("department_id", "department_name"),
        "Role": ("role_id", "role_name"),
        "Manager": ("manager_id", "manager_name")
    }

    if table not in allowed or allowed[table] != (id_col, name_col):
        raise ValueError("Invalid database table or column.")

    conn = get_connection()

    try:
        rows = conn.execute(
            f"SELECT {id_col}, {name_col} FROM {table} ORDER BY {name_col}"
        ).fetchall()

        return {row[1]: row[0] for row in rows}

    finally:
        conn.close()


# ==================================================
# SIDEBAR NAVIGATION
# ==================================================

menu = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "View Employees",
        "Add Employee",
        "Update Employee",
        "Onboarding",
        "Offboarding",
        "Audit Logs"
    ]
)

employees = get_employees()


# ==================================================
# DASHBOARD
# ==================================================

if menu == "Dashboard":

    st.header("Executive Overview")

    col1, col2, col3, col4 = st.columns(4)

    total = len(employees)

    active = employees["employment_status"].eq("Active").sum()
    terminated = employees["employment_status"].eq("Terminated").sum()
    department_count = employees["department_name"].nunique()

    col1.metric("Total Employees", total)
    col2.metric("Active Employees", int(active))
    col3.metric("Terminated", int(terminated))
    col4.metric("Departments", int(department_count))

    st.divider()

    st.subheader("Department Distribution")

    if not employees.empty:

        st.bar_chart(
            employees["department_name"].value_counts()
        )

        st.subheader("Latest Employees")

        st.dataframe(
            employees.head(10),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No employee records available.")


# ==================================================
# VIEW EMPLOYEES
# ==================================================

elif menu == "View Employees":

    st.header("Employee Directory")

    search = st.text_input(
        "Search by employee ID, name or email"
    )

    filtered = employees.copy()

    if search:

        mask = (
            filtered["employee_id"].str.contains(
                search, case=False, na=False
            )
            |
            filtered["employee_name"].str.contains(
                search, case=False, na=False
            )
            |
            filtered["email"].str.contains(
                search, case=False, na=False
            )
        )

        filtered = filtered[mask]

    department_filter = st.selectbox(
        "Filter by Department",
        ["All"] + sorted(
            employees["department_name"].dropna().unique().tolist()
        )
    )

    if department_filter != "All":

        filtered = filtered[
            filtered["department_name"] == department_filter
        ]

    st.write(f"Employees found: {len(filtered)}")

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True
    )


# ==================================================
# ADD EMPLOYEE
# ==================================================

elif menu == "Add Employee":

    st.header("Add New Employee")

    departments = get_options(
        "Department", "department_id", "department_name"
    )

    roles = get_options(
        "Role", "role_id", "role_name"
    )

    managers = get_options(
        "Manager", "manager_id", "manager_name"
    )

    if not departments or not roles:

        st.warning("Department or role data is missing.")

    else:

        with st.form("employee_form"):

            name = st.text_input("Employee Name")
            email = st.text_input("Email")

            department = st.selectbox(
                "Department", list(departments.keys())
            )

            role = st.selectbox(
                "Role", list(roles.keys())
            )

            manager = st.selectbox(
                "Manager", ["None"] + list(managers.keys())
            )

            employment_type = st.selectbox(
                "Employment Type",
                ["Permanent", "Contractor"]
            )

            location = st.selectbox(
                "Work Location",
                ["On-site", "Remote"]
            )

            hire_date = st.date_input("Joining Date")

            submitted = st.form_submit_button("Add Employee")

            if submitted:

                if not name.strip() or not email.strip():

                    st.error("Name and email are required.")

                elif "@" not in email or "." not in email:

                    st.error("Enter a valid email address.")

                else:

                    conn = get_connection()

                    try:

                        existing = conn.execute("""
                            SELECT 1 FROM Employee
                            WHERE email = ?
                        """, (email.strip(),)).fetchone()

                        if existing:

                            st.error("Email already exists.")

                        else:

                            next_number = conn.execute("""
                                SELECT COALESCE(
                                    MAX(
                                        CAST(SUBSTR(employee_id, 5) AS INTEGER)
                                    ), 0
                                ) + 1
                                FROM Employee
                            """).fetchone()[0]

                            employee_id = f"EMP-{next_number:06d}"

                            conn.execute("""
                                INSERT INTO Employee (
                                    employee_id,
                                    employee_name,
                                    email,
                                    department_id,
                                    role_id,
                                    manager_id,
                                    employment_type,
                                    work_location,
                                    employment_status,
                                    hire_date
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                employee_id,
                                name.strip(),
                                email.strip(),
                                departments[department],
                                roles[role],
                                managers.get(manager),
                                employment_type,
                                location,
                                "Active",
                                hire_date.isoformat()
                            ))

                            conn.commit()

                            st.success(
                                f"Employee {employee_id} added successfully!"
                            )

                            st.rerun()

                    except Exception as error:

                        conn.rollback()
                        st.error(f"Unable to add employee: {error}")

                    finally:
                        conn.close()


# ==================================================
# UPDATE EMPLOYEE
# ==================================================

elif menu == "Update Employee":

    st.header("Update Employee Details")

    if employees.empty:

        st.info("No employees available.")

    else:

        selected = st.selectbox(
            "Select Employee",
            employees["employee_id"].tolist()
        )

        conn = get_connection()

        employee = conn.execute("""
            SELECT *
            FROM Employee
            WHERE employee_id = ?
        """, (selected,)).fetchone()

        conn.close()

        if employee:

            with st.form("update_employee"):

                new_name = st.text_input(
                    "Employee Name",
                    employee["employee_name"]
                )

                new_email = st.text_input(
                    "Email",
                    employee["email"]
                )

                new_status = st.selectbox(
                    "Employment Status",
                    ["Active", "Terminated"],
                    index=(
                        0 if employee["employment_status"] == "Active"
                        else 1
                    )
                )

                update = st.form_submit_button("Save Changes")

                if update:

                    if not new_name.strip() or not new_email.strip():

                        st.error("Name and email are required.")

                    elif "@" not in new_email or "." not in new_email:

                        st.error("Enter a valid email address.")

                    else:

                        conn = get_connection()

                        try:

                            duplicate = conn.execute("""
                                SELECT 1 FROM Employee
                                WHERE email = ?
                                AND employee_id <> ?
                            """, (
                                new_email.strip(),
                                selected
                            )).fetchone()

                            if duplicate:

                                st.error(
                                    "Email already belongs to another employee."
                                )

                            else:

                                conn.execute("""
                                    UPDATE Employee
                                    SET employee_name = ?,
                                        email = ?,
                                        employment_status = ?
                                    WHERE employee_id = ?
                                """, (
                                    new_name.strip(),
                                    new_email.strip(),
                                    new_status,
                                    selected
                                ))

                                conn.commit()

                                st.success(
                                    "Employee updated successfully!"
                                )

                                st.rerun()

                        except Exception as error:

                            conn.rollback()
                            st.error(f"Update failed: {error}")

                        finally:
                            conn.close()


# ==================================================
# ONBOARDING
# ==================================================

elif menu == "Onboarding":

    st.header("Employee Onboarding")

    st.write(
        "Create onboarding cases and automatically generate tasks."
    )

    active_employees = employees[
        employees["employment_status"] == "Active"
    ]

    if active_employees.empty:

        st.info("No active employees available.")

    else:

        employee_options = {
            f"{row['employee_id']} - {row['employee_name']}":
            row["employee_id"]
            for _, row in active_employees.iterrows()
        }

        selected_employee = st.selectbox(
            "Select Employee",
            list(employee_options.keys())
        )

        if st.button("Create Onboarding", type="primary"):

            try:
                onboarding_id = create_onboarding(
                    employee_options[selected_employee]
                )

                st.success(
                    f"Onboarding created successfully: {onboarding_id}"
                )

                st.rerun()

            except Exception as error:
                st.error(f"Unable to create onboarding: {error}")

    st.divider()

    st.subheader("Onboarding Cases")

    try:
        cases = get_onboarding_cases()

        if cases:

            cases_df = pd.DataFrame(
                cases,
                columns=[
                    "Onboarding ID",
                    "Employee ID",
                    "Employee Name",
                    "Start Date",
                    "Status"
                ]
            )

            st.dataframe(
                cases_df,
                use_container_width=True,
                hide_index=True
            )

            case_ids = [case[0] for case in cases]

            selected_case = st.selectbox(
                "Select Onboarding Case to View Tasks",
                case_ids
            )

            tasks = get_onboarding_tasks(selected_case)

            if tasks:

                st.divider()
                st.subheader("Onboarding Tasks")

                tasks_df = pd.DataFrame(
                    tasks,
                    columns=[
                        "Task ID",
                        "Task Name",
                        "Task Status",
                        "Due Date",
                        "Completed At"
                    ]
                )

                st.dataframe(
                    tasks_df,
                    use_container_width=True,
                    hide_index=True
                )

                completed = sum(
                    task[2] == "Completed" for task in tasks
                )

                total_tasks = len(tasks)

                progress = (
                    completed / total_tasks if total_tasks else 0
                )

                st.progress(progress)

                st.write(
                    f"Completed Tasks: {completed} / {total_tasks}"
                )

                st.divider()

                st.subheader("Update Task Status")

                task_options = {
                    f"{task[1]} ({task[0]})": task[0]
                    for task in tasks
                }

                selected_task = st.selectbox(
                    "Select Task",
                    list(task_options.keys())
                )

                selected_task_id = task_options[selected_task]

                current_task = next(
                    task for task in tasks
                    if task[0] == selected_task_id
                )

                st.write(
                    f"Current Status: **{current_task[2]}**"
                )

                statuses = [
                    "Pending",
                    "In Progress",
                    "Completed",
                    "Cancelled"
                ]

                new_status = st.selectbox(
                    "New Status",
                    statuses,
                    index=(
                        statuses.index(current_task[2])
                        if current_task[2] in statuses else 0
                    )
                )

                st.divider()

                st.subheader("HR Override")

                allow_override = st.checkbox(
                    "Enable HR Override",
                    help="Allows HR to bypass task dependency restrictions."
                )

                override_reason = ""

                if allow_override:

                    st.warning(
                        "Override actions are recorded in the audit log."
                    )

                    override_reason = st.text_area(
                        "Override Reason (Required)",
                        placeholder="Explain why this task needs an override."
                    )

                if st.button("Update Task", type="primary"):

                    if allow_override and not override_reason.strip():

                        st.error(
                            "Please enter a reason for the HR override."
                        )

                    else:

                        try:
                            update_task_status(
                                selected_task_id,
                                new_status,
                                allow_override=allow_override,
                                override_reason=override_reason,
                                actor="HR Admin"
                            )

                            st.success("Task status updated successfully!")
                            st.rerun()

                        except Exception as error:
                            st.error(f"Unable to update task: {error}")

            else:
                st.info("No tasks found for this onboarding case.")

        else:
            st.info("No onboarding cases created yet.")

    except Exception as error:
        st.error(f"Unable to load onboarding cases: {error}")


# ==================================================
# OFFBOARDING
# ==================================================

elif menu == "Offboarding":

    st.header("Employee Offboarding")

    st.write(
        "Manage employee exits, recover company assets, "
        "and revoke system access."
    )

    st.divider()

    # ----------------------------------------------
    # CREATE OFFBOARDING CASE
    # ----------------------------------------------

    st.subheader("Create Offboarding Case")

    active_employees = employees[
        employees["employment_status"] == "Active"
    ]

    if active_employees.empty:

        st.info("No active employees available for offboarding.")

    else:

        employee_options = {
            f"{row['employee_id']} - {row['employee_name']}":
            row["employee_id"]
            for _, row in active_employees.iterrows()
        }

        with st.form("offboarding_form"):

            selected_employee = st.selectbox(
                "Select Employee",
                list(employee_options.keys())
            )

            last_working_day = st.date_input(
                "Last Working Day"
            )

            submitted = st.form_submit_button(
                "Create Offboarding Case"
            )

            if submitted:

                try:
                    offboarding_id = create_offboarding(
                        employee_options[selected_employee],
                        last_working_day.isoformat()
                    )

                    st.success(
                        f"Offboarding case created successfully! "
                        f"Case ID: {offboarding_id}"
                    )

                    st.rerun()

                except Exception as error:
                    st.error(f"Unable to create offboarding: {error}")

    st.divider()

    # ----------------------------------------------
    # OFFBOARDING CASES
    # ----------------------------------------------

    st.subheader("Offboarding Cases")

    try:
        cases = get_offboarding_cases()

        if cases:

            cases_df = pd.DataFrame(
                cases,
                columns=[
                    "Offboarding ID",
                    "Employee ID",
                    "Employee Name",
                    "Initiated Date",
                    "Last Working Day",
                    "Status"
                ]
            )

            st.dataframe(
                cases_df,
                use_container_width=True,
                hide_index=True
            )

            st.divider()

            st.subheader("Manage Employee Exit")

            case_options = {
                (
                    f"{case[1]} - {case[2]} "
                    f"(Case: {case[0]})"
                ): (case[0], case[1], case[5])
                for case in cases
            }

            selected_case_label = st.selectbox(
                "Select Offboarding Employee",
                list(case_options.keys())
            )

            selected_offboarding_id, selected_employee_id, selected_case_status = (
                case_options[selected_case_label]
            )
            # --------------------------------------
            # ASSET RECOVERY
            # --------------------------------------

            st.divider()
            st.subheader("Company Asset Recovery")

            assets = get_employee_assets(selected_employee_id)

            if assets:

                asset_df = pd.DataFrame(
                    assets,
                    columns=[
                        "Assignment ID",
                        "Asset ID",
                        "Asset Type",
                        "Asset Name",
                        "Serial Number",
                        "Assigned Date",
                        "Recovered Date"
                    ]
                )

                st.dataframe(
                    asset_df,
                    use_container_width=True,
                    hide_index=True
                )

                pending_assets = [
                    asset for asset in assets
                    if not asset[6]
                ]

                if pending_assets:

                    asset_options = {
                        (
                            f"{asset[3]} - {asset[4]} "
                            f"(Assignment: {asset[0]})"
                        ): asset[0]
                        for asset in pending_assets
                    }

                    selected_asset = st.selectbox(
                        "Select Asset to Recover",
                        list(asset_options.keys())
                    )

                    if st.button("Recover Selected Asset"):

                        try:
                            recover_employee_asset(
                                asset_options[selected_asset],
                                actor="HR Admin"
                            )

                            st.success("Asset recovered successfully!")
                            st.rerun()

                        except Exception as error:
                            st.error(f"Asset recovery failed: {error}")

                else:
                    st.success("All assigned assets have been recovered.")

            else:
                st.info("No asset assignments found for this employee.")

            # --------------------------------------
            # ACCESS REVOCATION
            # --------------------------------------

            st.divider()
            st.subheader("System Access Revocation")

            access_records = get_employee_access(selected_employee_id)

            if access_records:

                access_df = pd.DataFrame(
                    access_records,
                    columns=[
                        "Access Request ID",
                        "System Name",
                        "Requested Date",
                        "Access Status",
                        "Revoked At"
                    ]
                )

                st.dataframe(
                    access_df,
                    use_container_width=True,
                    hide_index=True
                )

                active_access = [
                    access for access in access_records
                    if access[3] != "Revoked"
                ]

                if active_access:

                    access_options = {
                        (
                            f"{access[1]} "
                            f"(Request: {access[0]})"
                        ): access[0]
                        for access in active_access
                    }

                    selected_access = st.selectbox(
                        "Select System Access to Revoke",
                        list(access_options.keys())
                    )

                    if st.button("Revoke Selected Access"):

                        try:
                            revoke_employee_access(
                                access_options[selected_access],
                                actor="HR Admin"
                            )

                            st.success("System access revoked successfully!")
                            st.rerun()

                        except Exception as error:
                            st.error(f"Access revocation failed: {error}")

                else:
                    st.success("All recorded system access is revoked.")

            else:
                st.info("No system access records found for this employee.")

        else:
            st.info("No offboarding cases created yet.")

    except Exception as error:
        st.error(f"Unable to load offboarding information: {error}")


# ==================================================
# AUDIT LOGS
# ==================================================

elif menu == "Audit Logs":

    st.header("HR Audit Logs")

    st.write(
        "Track HR workflow activities, overrides, "
        "asset recovery, and access revocation."
    )

    conn = get_connection()

    try:

        audit_df = pd.read_sql_query("""
            SELECT
                a.audit_id,
                a.employee_id,
                e.employee_name,
                a.event_type,
                a.event_description,
                a.actor,
                a.event_timestamp
            FROM AuditEvent a
            LEFT JOIN Employee e
                ON a.employee_id = e.employee_id
            ORDER BY a.event_timestamp DESC
        """, conn)

    finally:
        conn.close()

    if not audit_df.empty:

        col1, col2 = st.columns(2)

        col1.metric(
            "Total Audit Events",
            len(audit_df)
        )

        override_count = audit_df["event_type"].isin(
            ["HR_OVERRIDE", "TASK_OVERRIDE"]
        ).sum()

        col2.metric(
            "Override Events",
            int(override_count)
        )

        st.divider()

        st.subheader("Audit History")

        event_types = sorted(
            audit_df["event_type"].dropna().unique().tolist()
        )

        event_filter = st.selectbox(
            "Filter by Event Type",
            ["All"] + event_types
        )

        filtered_audit = audit_df.copy()

        if event_filter != "All":

            filtered_audit = filtered_audit[
                filtered_audit["event_type"] == event_filter
            ]

        st.dataframe(
            filtered_audit,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Audit Logs CSV",
            data=filtered_audit.to_csv(index=False),
            file_name="hr_audit_logs.csv",
            mime="text/csv"
        )

    else:

        st.info("No audit records available yet.")


# ==================================================
# FOOTER
# ==================================================

st.sidebar.divider()

st.sidebar.caption(
    "HR Workflow Management System"
)
