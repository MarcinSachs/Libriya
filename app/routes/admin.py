"""
Admin routes for managing tenants, users, and system settings
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from flask_babel import _
import logging
import os

from app import db
from app.models import Tenant, User, Library, Book, AuditLogFile
from app.forms import TenantForm
from app.utils.decorators import role_required
from app.utils.audit_log import log_action
from flask import current_app
from app.utils.scheduler import cleanup_old_audit_logs

logger = logging.getLogger(__name__)

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    """Require super-admin access (only user with role='superadmin')"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Super-admin must have role='superadmin'
        if not current_user.is_authenticated or not current_user.is_super_admin:
            flash(_("You do not have access to the super-admin panel."), "danger")
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/debug-admin')
def debug_admin():
    """Debug current_user in admin context"""
    import json
    if not current_user.is_authenticated:
        return json.dumps({'error': 'Not authenticated'})

    return json.dumps({
        'is_authenticated': current_user.is_authenticated,
        'username': current_user.username,
        'role': current_user.role,
        'tenant_id': current_user.tenant_id,
        'is_admin': current_user.is_admin,
        'is_super_admin': current_user.is_super_admin,
        'is_tenant_admin': current_user.is_tenant_admin,
    }, indent=2)


@bp.route('/')
@login_required
@admin_required
def admin_index():
    """Redirect admin panel to tenants"""
    # Default admin landing -> dashboard (system overview)
    return redirect(url_for('admin.dashboard'))


# ============================================================
# TENANTS MANAGEMENT
# ============================================================

@bp.route('/tenants', methods=['GET'])
@login_required
@admin_required
def tenants_list():
    """List all tenants"""
    page = request.args.get('page', 1, type=int)
    tenants = Tenant.query.paginate(page=page, per_page=20)
    return render_template(
        'admin/tenants_list.html',
        tenants=tenants,
        title=_('Manage Tenants'),
        active_page='admin-tenants',
        parent_page='admin'
    )


@bp.route('/tenants/add', methods=['GET', 'POST'])
@login_required
@admin_required
def tenant_add():
    """Create new tenant"""
    form = TenantForm()

    if form.validate_on_submit():
        tenant = Tenant(
            name=form.name.data,
            subdomain=form.subdomain.data.lower(),
            max_libraries=form.max_libraries.data if form.max_libraries.data not in (None, -1, "") else -1,
            max_books=form.max_books.data if form.max_books.data not in (None, -1, "") else -1
        )
        db.session.add(tenant)
        db.session.commit()

        # Audit: tenant created
        try:
            log_action('TENANT_CREATED', f"Tenant {tenant.name} created by {current_user.username}", subject=tenant, additional_info={
                       'tenant_id': tenant.id})
        except Exception:
            pass

        flash(_("Tenant '%(name)s' created successfully!", name=tenant.name), 'success')
        return redirect(url_for('admin.tenant_detail', tenant_id=tenant.id))

    return render_template(
        'admin/tenant_form.html',
        form=form,
        title=_('Add Tenant'),
        active_page='admin-tenants',
        parent_page='admin'
    )


@bp.route('/tenants/<int:tenant_id>', methods=['GET'])
@login_required
@admin_required
def tenant_detail(tenant_id):
    """View tenant details"""
    tenant = Tenant.query.get_or_404(tenant_id)

    # Get tenant stats
    users_count = User.query.filter_by(tenant_id=tenant_id).count()
    libraries_count = Library.query.filter_by(tenant_id=tenant_id).count()
    books_count = Book.query.filter_by(tenant_id=tenant_id).count()

    return render_template(
        'admin/tenant_detail.html',
        tenant=tenant,
        users_count=users_count,
        libraries_count=libraries_count,
        books_count=books_count,
        title=_('Tenant Details'),
        active_page='admin-tenants',
        parent_page='admin'
    )


@bp.route('/tenants/<int:tenant_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def tenant_edit(tenant_id):
    """Edit tenant"""
    tenant = Tenant.query.get_or_404(tenant_id)
    form = TenantForm()

    if form.validate_on_submit():
        tenant.name = form.name.data
        tenant.subdomain = form.subdomain.data.lower()
        tenant.max_libraries = form.max_libraries.data if form.max_libraries.data not in (None, -1, "") else -1
        tenant.max_books = form.max_books.data if form.max_books.data not in (None, -1, "") else -1
        db.session.commit()

        # Invalidate cache for this tenant
        from app.services.cache_service import invalidate_tenant_cache
        invalidate_tenant_cache(tenant_id=tenant.id, subdomain=tenant.subdomain)

        # Audit: tenant updated
        try:
            log_action('TENANT_UPDATED', f"Tenant {tenant.name} updated by {current_user.username}", subject=tenant, additional_info={
                       'tenant_id': tenant.id})
        except Exception:
            pass

        flash(_("Tenant updated successfully!"), 'success')
        return redirect(url_for('admin.tenant_detail', tenant_id=tenant.id))

    elif request.method == 'GET':
        form.name.data = tenant.name
        form.subdomain.data = tenant.subdomain
        form.max_libraries.data = tenant.max_libraries if tenant.max_libraries not in (None, -1) else None
        form.max_books.data = tenant.max_books if tenant.max_books not in (None, -1) else None

    return render_template(
        'admin/tenant_form.html',
        form=form,
        tenant=tenant,
        title=_('Edit Tenant'),
        active_page='admin-tenants',
        parent_page='admin'
    )


@bp.route('/tenants/<int:tenant_id>/delete', methods=['POST'])
@login_required
@admin_required
def tenant_delete(tenant_id):
    """Delete tenant"""
    tenant = Tenant.query.get_or_404(tenant_id)

    # Prevent deletion if tenant has users or libraries
    if tenant.users or tenant.libraries:
        flash(
            _("Cannot delete tenant with existing users or libraries."),
            'danger'
        )
        return redirect(url_for('admin.tenant_detail', tenant_id=tenant_id))

    name = tenant.name
    subdomain = tenant.subdomain
    db.session.delete(tenant)
    db.session.commit()

    # Invalidate cache for this tenant
    from app.services.cache_service import invalidate_tenant_cache
    invalidate_tenant_cache(tenant_id=tenant_id, subdomain=subdomain)

    # Audit: tenant deleted
    try:
        log_action('TENANT_DELETED', f"Tenant {name} deleted by {current_user.username}",
                   additional_info={'tenant_name': name, 'tenant_id': tenant_id})
    except Exception:
        pass

    flash(_("Tenant '%(name)s' deleted successfully!", name=name), 'success')
    return redirect(url_for('admin.tenants_list'))


# ============================================================
# DASHBOARD
# ============================================================

@bp.route('/dashboard', methods=['GET'])
@login_required
@admin_required
def dashboard():
    """Admin dashboard with system statistics"""
    total_tenants = Tenant.query.count()
    total_users = User.query.count()
    total_libraries = Library.query.count()

    # Recent tenants
    recent_tenants = Tenant.query.order_by(Tenant.created_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_tenants=total_tenants,
        total_users=total_users,
        total_libraries=total_libraries,
        recent_tenants=recent_tenants,
        title=_('Admin Dashboard'),
        active_page='admin-dashboard',
        parent_page='admin'
    )


# ============================================================
# PREMIUM FEATURES MANAGEMENT
# ============================================================

@bp.route('/tenants/<int:tenant_id>/premium', methods=['GET'])
@login_required
@admin_required
def manage_tenant_premium(tenant_id):
    """Manage premium features for a specific tenant"""
    tenant = Tenant.query.get_or_404(tenant_id)

    # Get available premium features from registry
    from app.services.premium.manager import PremiumManager
    available_features = PremiumManager.list_features()

    # Map to tenant's enabled features
    enabled_features = tenant.get_enabled_premium_features()

    features_with_status = []
    for feature_id, info in available_features.items():
        features_with_status.append({
            'feature_id': feature_id,
            'name': info['name'],
            'description': info['description'],
            'enabled': feature_id in enabled_features,
            'requires_config': info['requires_config'],
        })

    return render_template(
        'admin/tenant_premium.html',
        tenant=tenant,
        features=features_with_status,
        title=_('Manage Premium Features'),
        active_page='admin-tenants',
        parent_page='admin'
    )


@bp.route('/tenants/<int:tenant_id>/premium/<feature_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_tenant_premium_feature(tenant_id, feature_id):
    """Toggle a premium feature for a tenant (AJAX endpoint)"""
    tenant = Tenant.query.get_or_404(tenant_id)

    # Validate feature_id
    valid_features = {
        'bookcover_api': 'premium_bookcover_enabled',
        'biblioteka_narodowa': 'premium_biblioteka_narodowa_enabled',
    }

    if feature_id not in valid_features:
        return jsonify({'success': False, 'error': 'Invalid feature ID'}), 400

    field_name = valid_features[feature_id]
    current_value = getattr(tenant, field_name)
    new_value = not current_value
    setattr(tenant, field_name, new_value)

    db.session.commit()

    # Invalidate cache for this tenant's premium features
    from app.services.cache_service import invalidate_tenant_cache
    invalidate_tenant_cache(tenant_id=tenant.id, subdomain=tenant.subdomain)

    # Audit: premium toggled
    try:
        log_action('PREMIUM_TOGGLED', f'Premium feature {feature_id} toggled for tenant {tenant.id} by {current_user.username}', subject=tenant, additional_info={
                   'feature_id': feature_id, 'enabled': new_value, 'tenant_id': tenant.id})
    except Exception:
        pass

    return jsonify({
        'success': True,
        'feature_id': feature_id,
        'enabled': new_value,
        'message': _(f'Premium feature {feature_id} has been {"enabled" if new_value else "disabled"}')
    })


# ============================================================
# AUDIT LOG MANAGEMENT
# ============================================================

@bp.route('/audit-logs', methods=['GET'])
@login_required
@admin_required
def audit_logs_list():
    """List audit log files with basic metadata for super-admin."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    logs = AuditLogFile.query.order_by(AuditLogFile.created_at.desc()).paginate(page=page, per_page=per_page)

    # Compute a safe basename for display (avoid complex Jinja operations)
    for log in logs.items:
        try:
            log.basename = os.path.basename(log.filename)
        except Exception:
            log.basename = log.filename

    return render_template(
        'admin/audit_logs.html',
        logs=logs,
        title=_('Audit Logs'),
        active_page='admin-dashboard',
        parent_page='admin'
    )


@bp.route('/audit-logs/<int:log_id>/preview', methods=['GET'])
@login_required
@admin_required
def audit_log_preview(log_id):
    """Preview last N lines of the audit log file."""
    alf = AuditLogFile.query.get_or_404(log_id)

    # Ensure path is within logs directory
    logs_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    filepath = os.path.abspath(alf.filename)
    if not filepath.startswith(os.path.abspath(logs_root)) or not os.path.exists(filepath):
        flash(_('Log file not available'), 'danger')
        return redirect(url_for('admin.audit_logs_list'))

    # Read last 200 lines safely
    try:
        with open(filepath, 'rb') as f:
            f.seek(0, os.SEEK_END)
            filesize = f.tell()
            blocksize = 1024
            data = b''
            lines = []
            while len(lines) <= 200 and filesize > 0:
                read_size = min(blocksize, filesize)
                f.seek(filesize - read_size)
                chunk = f.read(read_size)
                data = chunk + data
                lines = data.splitlines()
                filesize -= read_size
            # decode only the last 200 lines
            text_lines = [ln.decode('utf-8', errors='replace') for ln in lines[-200:]]
    except Exception:
        flash(_('Failed to read log file'), 'danger')
        return redirect(url_for('admin.audit_logs_list'))

    # Log that super-admin previewed the file
    try:
        log_action('AUDIT_LOG_PREVIEW',
                   f'Super-admin previewed audit log file {alf.filename}', subject=None, additional_info={'audit_log_file_id': alf.id})
    except Exception:
        pass

    return render_template('admin/audit_log_preview.html', log=alf, lines=text_lines, title=_('Audit Log Preview'), parent_page='admin')


@bp.route('/audit-logs/<int:log_id>/delete', methods=['POST'])
@login_required
@admin_required
def audit_log_delete(log_id):
    """Delete (purge) audit log file from local storage and remove metadata.
    Restricted to super-admins. This action is audited.
    """
    alf = AuditLogFile.query.get_or_404(log_id)
    logs_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    filepath = os.path.abspath(alf.filename)
    if not filepath.startswith(os.path.abspath(logs_root)):
        flash(_('Not allowed to delete this file'), 'danger')
        return redirect(url_for('admin.audit_logs_list'))

    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        db.session.delete(alf)
        db.session.commit()

        # Audit the deletion
        try:
            log_action('AUDIT_LOG_DELETED',
                       f'Super-admin deleted audit log file {alf.filename}', subject=None, additional_info={'audit_log_file_id': alf.id})
        except Exception:
            pass

        flash(_('Audit log file deleted'), 'success')
    except Exception:
        db.session.rollback()
        flash(_('Failed to delete audit log file'), 'danger')

    return redirect(url_for('admin.audit_logs_list'))


@bp.route('/audit-logs/retention/run', methods=['POST'])
@login_required
@admin_required
def audit_logs_retention_run():
    """Manually trigger audit log retention job (deletes old files)."""
    try:
        # Call cleanup with app context
        cleanup_old_audit_logs(current_app)
        # Audit the manual run
        try:
            log_action('AUDIT_RETENTION_RUN', 'Super-admin manually triggered audit log retention', subject=None)
        except Exception:
            pass

        flash(_('Audit log retention executed'), 'success')
    except Exception as e:
        flash(_('Failed to run audit log retention: %(error)s', error=str(e)), 'danger')

    return redirect(url_for('admin.audit_logs_list'))


# ============================================================
# PREMIUM MODULES UPLOAD & MANAGEMENT (SUPERADMIN)
# ============================================================

@bp.route('/premium/modules', methods=['GET'])
@login_required
@role_required('superadmin')
def premium_modules_list():
    """List all installed premium modules and their status"""
    from app.services.premium.manager import PremiumManager

    modules = PremiumManager.list_features()

    modules_info = []
    for module_id, info in modules.items():
        modules_info.append({
            'module_id': module_id,
            'name': info.get('name', module_id),
            'enabled': info.get('enabled', False),
            'expiry_date': info.get('expiry_date', 'N/A'),
        })

    return render_template(
        'admin/premium_modules.html',
        modules=modules_info,
        title=_('Premium Modules'),
        active_page='premium-modules',
        parent_page='admin'
    )


@bp.route('/premium/upload', methods=['POST'])
@login_required
@role_required('superadmin')
def premium_modules_upload():
    """Upload and extract premium module ZIP"""
    import zipfile
    import shutil
    from app.services.premium.loader import PremiumModuleLoader

    logger.info(f"Premium upload request from {current_user.username}")
    logger.info(f"Files in request: {request.files.keys()}")

    try:
        # Check if file was provided
        if 'file' not in request.files:
            logger.error("No 'file' field in request")
            return jsonify({'error': _('No file provided')}), 400

        file = request.files['file']
        logger.info(f"File received: {file.filename}, size: {file.content_length}")

        if file.filename == '':
            logger.error("Empty filename")
            return jsonify({'error': _('No file selected')}), 400

        if not file.filename.endswith('.zip'):
            logger.error(f"Invalid file type: {file.filename}")
            return jsonify({'error': _('Only ZIP files are allowed')}), 400

        # Create backup of current premium modules
        premium_dir = PremiumModuleLoader.PREMIUM_DIR
        logger.info(f"Premium directory: {premium_dir}")
        backup_dir = os.path.join(premium_dir, '.backup')

        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)

        # Backup current state
        for folder in os.listdir(premium_dir):
            folder_path = os.path.join(premium_dir, folder)
            if os.path.isdir(folder_path) and not folder.startswith('_'):
                os.makedirs(backup_dir, exist_ok=True)
                shutil.copytree(folder_path, os.path.join(backup_dir, folder))

        # Save and extract ZIP
        temp_zip = os.path.join(premium_dir, f'.temp_{file.filename}')
        file.save(temp_zip)

        try:
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(premium_dir)

            os.remove(temp_zip)

            # Reload modules to validate licenses
            PremiumModuleLoader.reload_all()

            # Try to discover and validate
            modules = PremiumModuleLoader.discover_modules()

            if not modules:
                # Restore backup if nothing was loaded
                if os.path.exists(backup_dir):
                    for folder in os.listdir(backup_dir):
                        folder_path = os.path.join(backup_dir, folder)
                        target_path = os.path.join(premium_dir, folder)
                        if os.path.exists(target_path):
                            shutil.rmtree(target_path)
                        shutil.copytree(folder_path, target_path)
                    shutil.rmtree(backup_dir)

                return jsonify({'error': _('No valid premium modules found in ZIP')}), 400

            # Log the action
            log_action('PREMIUM_UPLOAD', f'Uploaded premium modules: {", ".join(modules.keys())}', subject=None)

            # Clean up backup
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)

            return jsonify({
                'success': _('Premium modules uploaded successfully'),
                'modules': list(modules.keys())
            }), 200

        except zipfile.BadZipFile:
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
            return jsonify({'error': _('Invalid ZIP file')}), 400
        except Exception as e:
            # Restore backup on error
            if os.path.exists(backup_dir):
                for folder in os.listdir(backup_dir):
                    folder_path = os.path.join(backup_dir, folder)
                    target_path = os.path.join(premium_dir, folder)
                    if os.path.exists(target_path):
                        shutil.rmtree(target_path)
                    shutil.copytree(folder_path, target_path)
                shutil.rmtree(backup_dir)

            if os.path.exists(temp_zip):
                os.remove(temp_zip)

            logger.error(f"Premium module upload error: {e}")
            return jsonify({'error': _('Failed to extract premium modules: %(error)s', error=str(e))}), 500

    except Exception as e:
        logger.error(f"Premium module upload error: {e}")
        return jsonify({'error': _('Server error during upload')}), 500


@bp.route('/premium/reload', methods=['POST'])
@login_required
@role_required('superadmin')
def premium_modules_reload():
    """Reload premium modules (clear cache and re-discover)"""
    try:
        from app.services.premium.manager import PremiumManager

        PremiumManager.reload()

        log_action('PREMIUM_RELOAD', 'Reloaded premium modules', subject=None)

        return jsonify({'success': _('Premium modules reloaded')}), 200

    except Exception as e:
        logger.error(f"Premium module reload error: {e}")
        return jsonify({'error': str(e)}), 500
