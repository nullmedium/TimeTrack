"""
Company invitation routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from models import db, CompanyInvitation, User, Role
from routes.auth import login_required, admin_required
from flask_mail import Message
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

invitations_bp = Blueprint('invitations', __name__, url_prefix='/invitations')


@invitations_bp.route('/')
@login_required
@admin_required
def list_invitations():
    """List all invitations for the company"""
    invitations = CompanyInvitation.query.filter_by(
        company_id=g.user.company_id
    ).order_by(CompanyInvitation.created_at.desc()).all()
    
    # Separate into pending and accepted
    pending_invitations = [inv for inv in invitations if inv.is_valid()]
    accepted_invitations = [inv for inv in invitations if inv.accepted]
    expired_invitations = [inv for inv in invitations if not inv.accepted and inv.is_expired()]
    
    return render_template('invitations/list.html',
                         pending_invitations=pending_invitations,
                         accepted_invitations=accepted_invitations,
                         expired_invitations=expired_invitations,
                         title='Manage Invitations')


@invitations_bp.route('/send', methods=['GET', 'POST'])
@login_required
@admin_required
def send_invitation():
    """Send a new invitation"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        role = request.form.get('role', 'Team Member')
        custom_message = request.form.get('custom_message', '').strip()
        
        if not email:
            flash('Email address is required', 'error')
            return redirect(url_for('invitations.send_invitation'))
        
        # Check if user already exists in the company
        existing_user = User.query.filter_by(
            email=email,
            company_id=g.user.company_id
        ).first()
        
        if existing_user:
            flash(f'A user with email {email} already exists in your company', 'error')
            return redirect(url_for('invitations.send_invitation'))
        
        # Check for pending invitations
        pending_invitation = CompanyInvitation.query.filter_by(
            email=email,
            company_id=g.user.company_id,
            accepted=False
        ).filter(CompanyInvitation.expires_at > datetime.now()).first()
        
        if pending_invitation:
            flash(f'An invitation has already been sent to {email} and is still pending', 'warning')
            return redirect(url_for('invitations.list_invitations'))
        
        # Create new invitation
        invitation = CompanyInvitation(
            company_id=g.user.company_id,
            email=email,
            role=role,
            invited_by_id=g.user.id
        )
        
        db.session.add(invitation)
        db.session.commit()
        
        # Send invitation email
        try:
            from app import mail
            
            # Build invitation URL
            invitation_url = url_for('register_with_invitation', 
                                   token=invitation.token, 
                                   _external=True)
            
            msg = Message(
                f'Invitation to join {g.user.company.name} on {g.branding.app_name}',
                recipients=[email]
            )
            
            msg.html = render_template('emails/invitation.html',
                                     invitation=invitation,
                                     invitation_url=invitation_url,
                                     custom_message=custom_message,
                                     sender=g.user)
            
            msg.body = f"""
Hello,

{g.user.username} has invited you to join {g.user.company.name} on {g.branding.app_name}.

{custom_message if custom_message else ''}

Click the link below to accept the invitation and create your account:
{invitation_url}

This invitation will expire in 7 days.

Best regards,
The {g.branding.app_name} Team
"""
            
            mail.send(msg)
            logger.info(f"Invitation sent to {email} by {g.user.username}")
            flash(f'Invitation sent successfully to {email}', 'success')
            
        except Exception as e:
            logger.error(f"Error sending invitation email: {str(e)}")
            flash('Invitation created but failed to send email. The user can still use the invitation link.', 'warning')
        
        return redirect(url_for('invitations.list_invitations'))
    
    # GET request - show the form
    roles = ['Team Member', 'Team Leader', 'Administrator']
    return render_template('invitations/send.html', roles=roles, title='Send Invitation')


@invitations_bp.route('/revoke/<int:invitation_id>', methods=['POST'])
@login_required
@admin_required
def revoke_invitation(invitation_id):
    """Revoke a pending invitation"""
    invitation = CompanyInvitation.query.filter_by(
        id=invitation_id,
        company_id=g.user.company_id,
        accepted=False
    ).first()
    
    if not invitation:
        flash('Invitation not found or already accepted', 'error')
        return redirect(url_for('invitations.list_invitations'))
    
    # Instead of deleting, we'll expire it immediately
    invitation.expires_at = datetime.now()
    db.session.commit()
    
    flash(f'Invitation to {invitation.email} has been revoked', 'success')
    return redirect(url_for('invitations.list_invitations'))


@invitations_bp.route('/resend/<int:invitation_id>', methods=['POST'])
@login_required
@admin_required
def resend_invitation(invitation_id):
    """Resend an invitation email"""
    invitation = CompanyInvitation.query.filter_by(
        id=invitation_id,
        company_id=g.user.company_id,
        accepted=False
    ).first()
    
    if not invitation:
        flash('Invitation not found or already accepted', 'error')
        return redirect(url_for('invitations.list_invitations'))
    
    # Extend expiration if needed
    if invitation.is_expired():
        invitation.expires_at = datetime.now() + timedelta(days=7)
        db.session.commit()
    
    # Resend email
    try:
        from app import mail
        
        invitation_url = url_for('register_with_invitation', 
                               token=invitation.token, 
                               _external=True)
        
        msg = Message(
            f'Reminder: Invitation to join {g.user.company.name}',
            recipients=[invitation.email]
        )
        
        msg.html = render_template('emails/invitation_reminder.html',
                                 invitation=invitation,
                                 invitation_url=invitation_url,
                                 sender=g.user)
        
        msg.body = f"""
Hello,

This is a reminder that you have been invited to join {g.user.company.name} on {g.branding.app_name}.

Click the link below to accept the invitation and create your account:
{invitation_url}

This invitation will expire on {invitation.expires_at.strftime('%B %d, %Y')}.

Best regards,
The {g.branding.app_name} Team
"""
        
        mail.send(msg)
        flash(f'Invitation resent to {invitation.email}', 'success')
        
    except Exception as e:
        logger.error(f"Error resending invitation email: {str(e)}")
        flash('Failed to resend invitation email', 'error')
    
    return redirect(url_for('invitations.list_invitations'))