# External Services & Notification Channels

**Document Reference:** `docs/13_EXTERNAL_SERVICES.md`
**System Title:** IoT-Based Power Monitoring & Fault Identification System
**Current Phase:** Version 1.0 (Audit, Hardening & Verification)

---

## 1. Executive Summary: External Services Inventory

An exhaustive audit of the codebase confirms:
- **No external third-party communication services are integrated into the current repository.**
- The system operates strictly as a **self-contained on-premises / private cloud application**.
- All notifications, alerting, maintenance tracking, and audit logging are handled **internally** via database tables.

---

## 2. In-App Notification System (`/notifications`)

### 2.1 Mechanism & Architecture
Rather than relying on third-party cloud push notification services (such as Firebase Cloud Messaging, Twilio SMS, or SendGrid email), alerting is performed in-app:

```
[ New Fault Detected ]
        │
        ▼
notify_new_faults() in backend/app/services/notifications.py
        │
        ▼
Insert into 'notifications' table:
  ├── title: e.g. "OVERCURRENT on phase Y"
  ├── message: e.g. "Phase Y current 38.2 A exceeds limit 32.0 A."
  ├── severity: "fault" / "warning"
  └── is_read: FALSE
        │
        ▼
Frontend Header Notification Bell (Polled via GET /notifications/unread-count)
```

### 2.2 Implemented Endpoints
- `GET /notifications/`: Returns paginated list of alerts (supports filtering by `is_read` and `severity`).
- `GET /notifications/unread-count`: Returns integer count of unread alerts for UI badge counter.
- `PUT /notifications/{id}/read`: Marks a single notification as read.
- `PUT /notifications/read-all`: Bulk updates all unread notifications to read.

---

## 3. Absence of Third-Party External Channels

| Channel | Implemented? | Notes / Rationale |
|---|:---:|---|
| **SMS Gateway (e.g. Twilio)** | **NO** | No cellular modem hardware or external SMS API keys configured. |
| **Email Service (e.g. SendGrid / SMTP)**| **NO** | No SMTP server or mailer service configured in `requirements.txt`. |
| **Push Notifications (e.g. FCM / APNs)** | **NO** | Application is currently an in-browser SPA, not a mobile PWA/native wrapper. |
| **External Cloud IoT Brokers** | **NO** | Xiao ESP32-S3 communicates directly via HTTP REST to the private FastAPI server. |
| **Weather / External Grid Feeds** | **NO** | Not required for local institutional sub-station monitoring. |

---

## 4. Recommendations for Future Phases

If external notifications are formally approved in future phases:
1. **SMTP Email Integration (Priority: Post-V1):** Integrate Python standard library `smtplib` or `fastapi-mail` to send daily summary reports and critical fault escalation emails to facility managers.
2. **Webhooks / Slack Integration:** Provide outbound webhook dispatch on high-severity faults (`severity="fault"`) to alert departmental response teams.
3. **Secret Safety:** All third-party API credentials must be stored strictly in environment variables and never committed to Git.
