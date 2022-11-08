# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MroTool(models.Model):
    _name = 'mro.tool'
    _description = 'Maintenance Tool'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']


    name = fields.Char('Tool Name', required=True)
    order_id = fields.Many2one('mro.order', string='Maintenance Order', readonly=True)
    tool_cost_unit = fields.Float('Hourly Tool Cost', digits='Product Price', required=True, default=0.00)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id)
    active = fields.Boolean('Active', default=True)
    tool_number = fields.Char('Tool Code')
    model = fields.Char('Model Code')
    serial = fields.Char('Serial no.')
    asset_id = fields.Char('Asset Number')
    purchase_value = fields.Float('Purchase Value', tracking=True)
    manufacturer_id = fields.Many2one('res.partner', 'Manufacturer')
    warranty_start_date = fields.Date('Warranty Start Date')
    warranty_end_date = fields.Date('Warranty End Date')
    vendor_id = fields.Many2one('res.partner', 'Vendor')
    purchase_date = fields.Date('Purchase Date')
    doc_count = fields.Integer("Number of attached documents", compute='_compute_attached_docs_count')
    note = fields.Text('Internal Notes')
    date_next_calibration = fields.Datetime('Next Calibration Date')


    @api.constrains('name', 'tool_number')
    def check_unique(self):
        tool_name = self.env['mro.tool'].search([('name', '=', self.name)])
        if len(tool_name) > 1:
            raise UserError(_("Tool Name already exists"))
        tool_number = self.env['mro.tool'].search([('name', '=', self.tool_number)])
        if len(tool_number) > 1:
            raise UserError(_("Tool Number already exists"))
        return True

    @api.constrains('warranty_start_date','warranty_end_date')
    def _check_warranty_dates(self):
        if (self.warranty_start_date and self.warranty_end_date) and (self.warranty_start_date >= self.warranty_end_date):
            raise UserError(_('check validity dates'))
        return True

    def _compute_attached_docs_count(self):
        attachment = self.env['ir.attachment']
        for tool in self:
            tool.doc_count = attachment.search_count(['&',('res_model', '=', 'mro.tool'), ('res_id', '=', tool.id)])

    def attachment_tree_view(self):
        self.ensure_one()
        domain = ['&', ('res_model', '=', 'mro.tool'), ('res_id', 'in', self.ids)]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'type': 'ir.actions.act_window',
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }










