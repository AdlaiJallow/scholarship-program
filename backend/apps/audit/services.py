def log_action(action, actor=None, target=None, metadata=None, request=None):
    """
    Single entry point for writing an audit log row, so every call site
    looks the same and nobody accidentally writes directly to the table.
    """
    from .models import AuditLog

    ip_address = None
    if request is not None:
        ip_address = getattr(request, "audit_ip", None) or request.META.get("REMOTE_ADDR")

    target_type = target.__class__.__name__ if target is not None else ""
    target_id = str(getattr(target, "pk", "")) if target is not None else ""

    return AuditLog.objects.create(
        actor=actor,
        actor_email_snapshot=getattr(actor, "email", ""),
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
        ip_address=ip_address,
    )
