"""
Admin routes for managing tenants, users, and system settings
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from flask_babel import _

from app import db
from app.models import Tenant, User, Library, Book
from app.forms import TenantForm
from app.utils.decorators import role_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    """Require super-admin access (only user with role='admin' and tenant_id=NULL)"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Super-admin must have role='admin' and no tenant_id assigned
        if not current_user.is_authenticated or not current_user.is_super_admin:
            flash(_("You do not have access to the super-admin panel."), "danger")
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


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
            subdomain=form.subdomain.data.lower()
        )
        db.session.add(tenant)
        db.session.commit()
        
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
        db.session.commit()
        
        flash(_("Tenant updated successfully!"), 'success')
        return redirect(url_for('admin.tenant_detail', tenant_id=tenant.id))
    
    elif request.method == 'GET':
        form.name.data = tenant.name
        form.subdomain.data = tenant.subdomain
    
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
    db.session.delete(tenant)
    db.session.commit()
    
    flash(_("Tenant '%(name)s' deleted successfully!", name=name), 'success')
    return redirect(url_for('admin.tenants_list'))


# ============================================================
# DASHBOARD
# ============================================================

@bp.route('/', methods=['GET'])
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
