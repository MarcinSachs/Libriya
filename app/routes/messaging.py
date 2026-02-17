"""
Routes for messaging between tenant admins and super-admin
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from flask_babel import _

from app import db
from app.models import AdminSuperAdminConversation, AdminSuperAdminMessage, Tenant, User

bp = Blueprint("messaging", __name__, url_prefix="/messaging")


# ============================================================
# TENANT ADMIN ROUTES
# ============================================================

@bp.route('/admin-support', methods=['GET', 'POST'])
@login_required
def admin_support():
    """List conversations between current admin and super-admin"""
    # Only tenant admins can access this
    if not current_user.is_tenant_admin:
        abort(403)
    
    conversations = AdminSuperAdminConversation.query.filter_by(
        admin_id=current_user.id
    ).order_by(AdminSuperAdminConversation.created_at.desc()).all()
    
    return render_template(
        'messaging/admin_support.html',
        conversations=conversations,
        title=_('Support - Contact Super Admin'),
        active_page='admin-support',
        parent_page='admin'
    )


@bp.route('/admin-support/new', methods=['GET', 'POST'])
@login_required
def admin_support_new():
    """Start new conversation with super-admin"""
    if not current_user.is_tenant_admin:
        abort(403)
    
    if request.method == 'POST':
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        if not subject or not message:
            flash(_('Subject and message are required'), 'danger')
            return redirect(url_for('messaging.admin_support_new'))
        
        # Create conversation
        conversation = AdminSuperAdminConversation(
            tenant_id=current_user.tenant_id,
            admin_id=current_user.id,
            subject=subject
        )
        db.session.add(conversation)
        db.session.flush()  # Get conversation.id
        
        # Add first message
        first_message = AdminSuperAdminMessage(
            conversation_id=conversation.id,
            sender_id=current_user.id,
            message=message
        )
        db.session.add(first_message)
        db.session.commit()
        
        flash(_('Message sent to super-admin'), 'success')
        return redirect(url_for('messaging.admin_support_conversation', conversation_id=conversation.id))
    
    return render_template(
        'messaging/admin_support_new.html',
        title=_('New Message to Super Admin'),
        active_page='admin-support',
        parent_page='admin'
    )


@bp.route('/admin-support/<int:conversation_id>', methods=['GET', 'POST'])
@login_required
def admin_support_conversation(conversation_id):
    """View conversation and add replies"""
    if not current_user.is_tenant_admin:
        abort(403)
    
    conversation = AdminSuperAdminConversation.query.get_or_404(conversation_id)
    
    # Check if current user is the admin who created this conversation
    if conversation.admin_id != current_user.id:
        abort(403)
    
    if request.method == 'POST':
        message_text = request.form.get('message')
        
        if not message_text:
            flash(_('Message cannot be empty'), 'danger')
            return redirect(url_for('messaging.admin_support_conversation', conversation_id=conversation_id))
        
        new_message = AdminSuperAdminMessage(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            message=message_text
        )
        db.session.add(new_message)
        db.session.commit()
        
        flash(_('Reply sent'), 'success')
        return redirect(url_for('messaging.admin_support_conversation', conversation_id=conversation_id))
    
    return render_template(
        'messaging/admin_support_conversation.html',
        conversation=conversation,
        messages=conversation.messages,
        title=_('Support Conversation'),
        active_page='admin-support',
        parent_page='admin'
    )


# ============================================================
# SUPER ADMIN ROUTES
# ============================================================

@bp.route('/admin/messages', methods=['GET'])
@login_required
def super_admin_messages():
    """Super-admin: View all conversations with tenant admins"""
    if not current_user.is_super_admin:
        abort(403)
    
    conversations = AdminSuperAdminConversation.query.order_by(
        AdminSuperAdminConversation.created_at.desc()
    ).all()
    
    # Count total unread
    total_unread = sum(conv.unread_count for conv in conversations)
    
    return render_template(
        'messaging/super_admin_messages.html',
        conversations=conversations,
        total_unread=total_unread,
        title=_('Messages from Tenant Admins'),
        active_page='admin-messages',
        parent_page='admin'
    )


@bp.route('/admin/messages/<int:conversation_id>', methods=['GET', 'POST'])
@login_required
def super_admin_conversation(conversation_id):
    """Super-admin: View conversation and reply"""
    if not current_user.is_super_admin:
        abort(403)
    
    conversation = AdminSuperAdminConversation.query.get_or_404(conversation_id)
    
    # Mark all messages as read
    for msg in conversation.messages:
        if not msg.read:
            msg.read = True
    db.session.commit()
    
    if request.method == 'POST':
        message_text = request.form.get('message')
        
        if not message_text:
            flash(_('Message cannot be empty'), 'danger')
            return redirect(url_for('messaging.super_admin_conversation', conversation_id=conversation_id))
        
        new_message = AdminSuperAdminMessage(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            message=message_text
        )
        db.session.add(new_message)
        db.session.commit()
        
        flash(_('Reply sent to admin'), 'success')
        return redirect(url_for('messaging.super_admin_conversation', conversation_id=conversation_id))
    
    return render_template(
        'messaging/super_admin_conversation.html',
        conversation=conversation,
        messages=conversation.messages,
        tenant=conversation.tenant,
        admin=conversation.admin,
        title=_('Message from %(admin)s - %(tenant)s', admin=conversation.admin.username, tenant=conversation.tenant.name),
        active_page='admin-messages',
        parent_page='admin'
    )
