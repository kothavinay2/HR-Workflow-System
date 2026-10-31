# HR Onboarding and Offboarding Workflow Management System

## Project Overview

The HR Onboarding and Offboarding Workflow Management System is a web-based application developed using Python, Streamlit, and SQLite. It helps HR teams manage employee information, streamline onboarding activities, monitor offboarding processes, recover company assets, revoke system access, and maintain audit records.

## Features

- **Employee Management:** Add, view, search, filter, and update employee information.
- **Onboarding Management:** Create onboarding cases and manage employee onboarding tasks.
- **Task Dependency Validation:** Ensure prerequisite tasks are completed before dependent tasks.
- **HR Override:** Allow authorized HR users to override task dependency restrictions.
- **Offboarding Management:** Create and track employee offboarding cases.
- **Asset Recovery:** Track company assets and update their availability after recovery.
- **Access Revocation:** Track and revoke employee access to company systems.
- **Audit Logs:** Maintain records of important HR activities.
- **Interactive Dashboard:** Display employee statistics and department-wise information.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Application logic and backend functionality |
| Streamlit | Web application interface |
| SQLite | Database management |
| Pandas | Data processing and analysis |
| Plotly | Interactive charts and visualizations |

## Project Structure

```text
HR_Workflow_System/
│
├── app.py
├── database.py
├── models.py
├── workflow.py
├── validation.py
├── analytics.py
├── generate_data.py
├── check_onboarding.py
├── requirements.txt
├── PROMPT_HISTORY.md
├── .gitignore
│
├── database/
│   └── hr_workflow.db
│
└── pages/
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/kothavinay2/HR-Workflow-System.git
```

### 2. Navigate to the Project Folder

```bash
cd HR-Workflow-System
```

### 3. Create a Virtual Environment (Optional)

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Application

```bash
streamlit run app.py
```

### 6. Open in Browser

```text
http://localhost:8501
```

## Database

The application uses SQLite to store employee information and workflow records, including onboarding cases, offboarding cases, asset assignments, access requests, and audit events.

## AI Assistance

ChatGPT was used as a development assistant for project planning, database design, implementation guidance, debugging, and documentation.

Refer to [PROMPT_HISTORY.md](PROMPT_HISTORY.md) for the reconstructed AI prompt history.

## GitHub Repository

[HR Workflow System](https://github.com/kothavinay2/HR-Workflow-System)

## Author

Developed as an HR workflow management project using Python and Streamlit.