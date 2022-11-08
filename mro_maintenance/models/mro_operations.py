# -*- coding: utf-8 -*-


from odoo import api, fields, models, _


class MroCheckList(models.Model):
    _name = 'mro.check.list'
    _description = 'Maintenance Check List'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Check List', required=True)
    activity_lines = fields.One2many('mro.activity', 'check_list_id', 'Activity')
    active = fields.Boolean('Active', default=True)
    doc_count = fields.Integer('Number of attached documents', compute='_compute_attached_docs_count')
    note = fields.Text('Internal Notes')


    def _compute_attached_docs_count(self):
        attachment = self.env['ir.attachment']
        for check in self:
            check.doc_count = attachment.search_count(['&',('res_model', '=', 'mro.check.list'), ('res_id', '=', check.id)])

    def attachment_tree_view(self):
        self.ensure_one()
        domain = ['&', ('res_model', '=', 'mro.check.list'), ('res_id', 'in', self.ids)]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,tree,form',
            'type': 'ir.actions.act_window',
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }


class MroActivity(models.Model):
    _name = 'mro.activity'
    _description = 'Maintenance Activity'
    _order = 'sequence'

    name = fields.Char(_('Activity'), required=True)
    sequence = fields.Integer(_('Sequence'), required=True)
    check_list_id = fields.Many2one('mro.check.list', _('Check List'))

