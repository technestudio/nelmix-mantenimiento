# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MroTask(models.Model):
    _name = 'mro.task'
    _description = 'Maintenance Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char('Task', required=True)
    category_id = fields.Many2one('mro.equipment.category', 'Equipment Category', ondelete='restrict', required=True)
    parts_lines = fields.One2many('mro.task.parts.line', 'task_id', 'Parts')
    tool_ids = fields.One2many('mro.task.tool', 'task_id', 'Tools')
    check_list_id = fields.Many2one('mro.check.list', 'Check List', required=True)
    activity = fields.Many2many('mro.activity', string='Operations', domain="[('check_list_id','=', check_list_id)]", readonly=True)
    order_duration = fields.Float('Duration', default=1.0, required=True)
    active = fields.Boolean('Active', default=True)
    note = fields.Text('Internal Notes')
    doc_count = fields.Integer('Number of attached documents', compute='_compute_attached_docs_count')


    def _compute_attached_docs_count(self):
        attachment = self.env['ir.attachment']
        for task in self:
            task.doc_count = attachment.search_count(['&',('res_model', '=', 'mro.task'), ('res_id', '=', task.id)])

    def attachment_tree_view(self):
        self.ensure_one()
        domain = ['&', ('res_model', '=', 'mro.task'), ('res_id', 'in', self.ids)]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,tree,form',
            'type': 'ir.actions.act_window',
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }


class MroTaskPartLines(models.Model):
    _name = 'mro.task.parts.line'
    _description = 'Maintenance Planned Spare Parts'

    parts_id = fields.Many2one('product.product', 'Spare Part', required=True, domain=[('maintenance_ok', '=', True)])
    parts_qty = fields.Float('Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    parts_uom = fields.Many2one('uom.uom', 'Unit of Measure', related='parts_id.uom_id')
    parts_type = fields.Selection(string='Product Type', related='parts_id.type', readonly=True)
    parts_categ_id = fields.Many2one('product.category', 'Product Category', related='parts_id.categ_id', readonly=True)
    task_id = fields.Many2one('mro.task', 'Maintenance Task')


class MroTaskTools(models.Model):
    _name = 'mro.task.tool'
    _description = 'Maintenance Task Tools'

    tool_id = fields.Many2one('mro.tool', 'Tools', required=True)
    task_id = fields.Many2one('mro.task', 'Maintenance Task')


    @api.constrains('tool_id')
    def check_tool_id(self):
        for record in self:
            tools = self.env['mro.task.tool'].search([('task_id', '=', record.task_id.id), ('tool_id', '=', record.tool_id.id)])
        if len(tools) > 1:
            raise UserError(_("Tool already entered"))
