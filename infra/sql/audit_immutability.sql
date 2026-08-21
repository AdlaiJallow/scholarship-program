-- Enforces audit-log immutability at the database grant level (system
-- specification §15). The application-layer guards in
-- apps.audit.models.AuditLog.save()/delete() are a second line of
-- defense, not the primary control — a control that lives only in
-- application code is bypassed by anyone with direct database access,
-- which defeats the point of an audit trail for a system holding
-- national ID data.
--
-- Run once against production/staging as a superuser, after the Django
-- migrations have created the audit_logs table and the application's own
-- database role (replace scholarship_portal_app below with that role's
-- actual name).

REVOKE UPDATE, DELETE ON audit_logs FROM scholarship_portal_app;
GRANT INSERT, SELECT ON audit_logs TO scholarship_portal_app;

-- Belt-and-braces: a trigger that rejects any UPDATE/DELETE regardless of
-- which role attempts it, including a future superuser role added to the
-- application's connection.
CREATE OR REPLACE FUNCTION reject_audit_log_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only: % is not permitted', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_logs_no_update ON audit_logs;
CREATE TRIGGER audit_logs_no_update
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION reject_audit_log_mutation();
