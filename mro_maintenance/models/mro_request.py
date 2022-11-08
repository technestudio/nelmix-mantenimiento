# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, date, time, timedelta
from odoo.exceptions import UserError


class MroRequest(models.Model):
    _name = 'mro.request'
    _description = 'Maintenance Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'maintenance_priority desc, requested_date asc,id'

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('claim', 'Confirmed'),
        ('run', 'Execution'),
        ('done', 'Done'),
        ('reject', 'Rejected'),
        ('cancel', 'Canceled')
    ]

    PRIORITY_SELECTION = [
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Breakdown')
    ]

    REQ_MAINTENANCE_TYPE_SELECTION = [
        ('bm', 'Corrective'),
        ('in', 'Inspection'),
        ('rf', 'Retrofit'),
    ]


    def _group_requested_by_domain(self):
        group = self.env.ref('mro_maintenance.group_maintenance_administrator', raise_if_not_found=False)
        return [('groups_id', 'in', group.ids)] if group else []


    name = fields.Char('Request Name', required=True, copy=False, readonly=True, default='New')
    state = fields.Selection(STATE_SELECTION, 'Status', readonly=True, tracking=True, default='draft')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    equipment_id = fields.Many2one('mro.equipment', 'Equipment', domain="[('company_id','=', company_id)]",
        required=True, readonly=True, states={'draft': [('readonly', False)]})
    maintenance_type = fields.Selection(REQ_MAINTENANCE_TYPE_SELECTION, 'Maintenance Type', required=True, readonly=True,
        states={'draft': [('readonly', False)]}, default='bm')
    cause = fields.Text('Cause', required=True, readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Text('Description', readonly=True, states={'draft': [('readonly', False)]})
    reject_reason = fields.Text('Reject Reason', readonly=True)
    requested_date = fields.Datetime('Requested Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    active = fields.Boolean('Active', default=True)
    order_id = fields.Many2one('mro.order', 'Maintenance Order', readonly=True)
    requested_by = fields.Many2one('res.users', 'Requested by', domain=_group_requested_by_domain, required=True, tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    maintenance_priority = fields.Selection(PRIORITY_SELECTION, 'Maintenance Priority', default='1', required=True, readonly=True, states={'draft': [('readonly', False)]})
    doc_count = fields.Integer("Number of attached documents", compute='_compute_attached_docs_count')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Maintenance Costs Analytic Account", readonly=True, states={'draft': [('readonly', False)]})


    @api.constrains('maintenance_priority', 'maintenance_type')
    def _check_maintenance_type(self):
        for order in self:
            if order.maintenance_priority == '3' and not order.maintenance_type == 'bm':
                raise UserError(_('corrective maintenance type has to be chosen for Equipment in breakdown'))
        return True

    @api.onchange('maintenance_priority','state')
    def onchange_maintenance_priority(self):
        if self.state == 'draft' and self.maintenance_priority == '3':
            self.requested_date = datetime.today()

    @api.constrains('equipment_id')
    def _check_scrap(self):
        for request in self:
            if request.equipment_id.state == 'sc':
                raise UserError(_('equipment has been scrapped'))
        return True

    def action_send(self):
        for request in self:
            request.write({'state': 'claim'})
            if request.maintenance_priority == '3':
                request.requested_date = datetime.today()
            request.sudo().request_for_approval_mail_send()

    def request_for_approval_mail_send(self):
        mail_obj = self.env['mail.mail']
        for request in self:
            subject = 'Request for Approval: '+ str(request.name)
            mail_data = {
                        'subject': subject,
                        'body_html': request.cause,
                        'email_from': request.create_uid.partner_id.email,
                        'email_to': request.requested_by.partner_id.email,
                        }
        mail_id = mail_obj.sudo().create(mail_data)
        mail_id.sudo().send()
        return True

    def action_confirm(self):
        for request in self:
            order_id = self.env['mro.order'].create({
                'date_planned':request.requested_date,
                'date_scheduled':request.requested_date,
                'maintenance_priority':request.maintenance_priority,
                'state': 'draft',
                'maintenance_type': request.maintenance_type,
                'equipment_id': request.equipment_id.id,
                'maintenance_team_id': request.equipment_id.maintenance_team_id.id,
                'cause': request.cause,
                'description': request.description,
                'request_id' : request.id,
            })
        self.write({'state': 'run'})
        self.write({'order_id': order_id.id})
        return order_id.id

    def action_done(self):
        self.write({'state': 'done'})
        return True

    def action_reject(self):
        self.write({'state': 'reject'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    @api.model
    def _create_sequence(self, vals):
        if not vals.get('name') or vals.get('name') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('mro.request') or 'New'
        return vals

    @api.model
    def create(self, vals):
        vals = self._create_sequence(vals)
        res = super().create(vals)
        return res

    def _compute_attached_docs_count(self):
        attachment = self.env['ir.attachment']
        for request in self:
            request.doc_count = attachment.search_count(['&',('res_model', '=', 'mro.request'), ('res_id', '=', request.id)])

    def attachment_tree_view(self):
        self.ensure_one()
        domain = ['&', ('res_model', '=', 'mro.request'), ('res_id', 'in', self.ids)]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }