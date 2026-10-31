# Testing and Limitations

## 1. Testing Environment

- Operating System: Windows
- Programming Language: Python
- Framework: Streamlit
- Database: SQLite

## 2. Testing Performed

The following application features were tested:

| Feature | Testing |
|---|---|
| Dashboard | Verified dashboard loading |
| Employee Management | Tested employee registration and viewing |
| Employee Update | Tested updating employee details |
| Onboarding | Tested onboarding case and task management |
| Task Dependencies | Verified prerequisite task validation |
| Offboarding | Tested offboarding case management |
| Asset Recovery | Tested asset recovery functionality |
| Access Revocation | Tested system access revocation |
| Audit Logs | Verified audit log display |

## 3. Validation

- Tested required task dependency validation.
- Checked employee and workflow database operations.
- Verified application startup using Streamlit.
- Tested workflow status updates.

## 4. Limitations

- The application currently uses a local SQLite database.
- Authentication and role-based access controls may need further enhancement.
- Email notifications and external HR integrations are not implemented unless configured separately.
- Production deployment and multi-user concurrency require additional testing.

## 5. Future Improvements

- Add secure user authentication.
- Implement email notifications.
- Add advanced reporting.
- Improve role-based permissions.
- Support production database deployment.

## 6. Verification Summary

The application was launched successfully in the local Windows environment, and the listed features were tested. Further testing is required before production deployment.