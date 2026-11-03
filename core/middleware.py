import io
import logging
import threading
from django.core.management import call_command
from django.db import DatabaseError, OperationalError, ProgrammingError
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)


class AutoMigrationMiddleware:
    """
    Lightweight middleware ensuring pending database migrations run seamlessly on production/serverless environments.
    
    1. Intercepts /run-migrations/ and /admin-dashboard/run-migrations/ directly to run migrations
       without querying any unmigrated models or requiring authentication first.
    2. Intercepts unhandled database schema errors (ProgrammingError / OperationalError) across views,
       automatically triggers pending migrations, and retries the request so users never experience a 500 Server Error.
    """
    _lock = threading.Lock()
    _migrated = False

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info.rstrip('/')

        # Direct migration runner path (GET or POST)
        if path in ['/run-migrations', '/admin-dashboard/run-migrations']:
            out = io.StringIO()
            success = False
            try:
                call_command('migrate', interactive=False, stdout=out)
                output = out.getvalue().strip() or "Database is already up to date."
                success = True
                with AutoMigrationMiddleware._lock:
                    AutoMigrationMiddleware._migrated = True
            except Exception as e:
                output = f"Migration execution error: {str(e)}"

            if request.headers.get('accept') == 'application/json' or request.GET.get('format') == 'json':
                return JsonResponse({
                    'success': success,
                    'output': output
                }, status=200 if success else 500)

            html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database Migrations | WorkEase</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body style="background: #f4f7fc; padding: 40px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <div style="max-width: 650px; margin: 40px auto; background: #fff; padding: 32px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
            <span style="font-size: 28px;">{'✅' if success else '❌'}</span>
            <div>
                <h2 style="font-size: 20px; font-weight: 700; color: #1e293b; margin: 0;">Database Migration Runner</h2>
                <p style="font-size: 13px; color: #64748b; margin: 0;">Automated schema synchronization for WorkEase PostgreSQL database.</p>
            </div>
        </div>
        <div class="alert {'alert-success' if success else 'alert-danger'}" role="alert">
            <strong>Status:</strong> {'Migrations successfully applied!' if success else 'Migration execution failed.'}
        </div>
        <pre style="background: #0f172a; color: #38bdf8; padding: 16px; border-radius: 8px; font-size: 12px; max-height: 250px; overflow-y: auto;">{output}</pre>
        <div style="margin-top: 24px; display: flex; gap: 12px;">
            <a href="/admin-dashboard/" class="btn btn-primary" style="padding: 8px 18px; font-weight: 600;">Go to Admin Dashboard</a>
            <a href="/dashboard/" class="btn btn-outline-secondary" style="padding: 8px 18px;">Employee Dashboard</a>
        </div>
    </div>
</body>
</html>"""
            return HttpResponse(html, status=200 if success else 500)

        # Standard request handling
        try:
            return self.get_response(request)
        except (ProgrammingError, OperationalError, DatabaseError) as exc:
            logger.warning(f"Database schema error intercepted ({exc}). Auto-triggering pending migrations...")
            with AutoMigrationMiddleware._lock:
                try:
                    call_command('migrate', interactive=False)
                    AutoMigrationMiddleware._migrated = True
                except Exception as m_err:
                    logger.error(f"Auto-migration attempt failed: {m_err}")
            # Retry the request once after migrations have been applied
            return self.get_response(request)

