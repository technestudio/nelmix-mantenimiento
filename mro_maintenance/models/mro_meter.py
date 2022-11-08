# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import time
from datetime import datetime, date, time, timedelta


class MroMeter(models.Model):
    _name = 'mro.meter'
    _description = 'Equipment Meters'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    STATE_SELECTION = [
        ('draft', 'Setup'),
        ('operative', 'Operative')
    ]

    MEASURE_TYPE_SELECTION = [
        ('up', 'Progressive'),
        ('delta', 'Delta')
    ]

    name = fields.Char('Meter Name', required=True)
    state = fields.Selection(STATE_SELECTION, 'Status', readonly=True, default='draft')
    meter_uom = fields.Many2one('uom.uom', 'Unit of Measure', required=True, readonly=True, states={'draft': [('readonly', False)]})
    meter_line_ids = fields.One2many('mro.meter.line', 'meter_id', 'Meter Measures')
    equipment_id = fields.Many2one('mro.equipment', 'Equipment', readonly=True)
    measure_type = fields.Selection(MEASURE_TYPE_SELECTION, 'Measure Type', required=True, readonly=True, states={'draft': [('readonly', False)]}, default='up')
    actual_utilization = fields.Float('Actual Utilization', compute='_get_utilization', store=True)
    date_meter_install = fields.Datetime('Meter installment date', readonly=True)
    date = fields.Datetime('Measure Date', compute='_get_utilization', store=True)
    doc_count = fields.Integer('Number of documents attached', compute='_compute_attached_docs_count')
    note = fields.Text(string='Internal Notes')
    
    
    def install_meter(self):
        for meter in self:
            if not meter.equipment_id:
                raise UserError(_("Please assign an Equipment before installing it"))
            else:
                meter.state = 'operative'
                meter.date_meter_install = fields.Datetime.now()
        return True
        
    def detact_meter(self):
        for meter in self:
            meter.state = 'draft'
            meter.date_meter_install = False
        return True

    @api.depends('meter_line_ids')
    def _get_utilization(self):
        utilization = 0
        date = False
        for meter in self:
            if meter.measure_type == 'delta':
                for line in meter.meter_line_ids:
                    utilization += line.value
                    date = line.date
            elif meter.measure_type == 'up':
                for line in meter.meter_line_ids:
                    utilization = line.value
                    date = line.date
            meter.actual_utilization = utilization
            meter.date = date
        return True
        
    def _compute_attached_docs_count(self):
        attachment = self.env['ir.attachment']
        for meter in self:
            meter.doc_count = attachment.search_count(['&',('res_model', '=', 'mro.meter'), ('res_id', '=', meter.id)])
    
    def attachment_tree_view(self):
        self.ensure_one()
        domain = ['&', ('res_model', '=', 'mro.meter'), ('res_id', 'in', self.ids)]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,tree,form',
            'type': 'ir.actions.act_window',
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

class MroMeterLine(models.Model):
    _name = 'mro.meter.line'
    _description = 'Meter Measure'
    _order = 'meter_id, date'

    date = fields.Datetime('Measure Date', required=True)
    value = fields.Float('Measure Value', required=True)
    meter_id = fields.Many2one('mro.meter', 'Meter', ondelete='restrict', required=True)
    meter_uom = fields.Many2one('uom.uom', 'Unit of Measure', related='meter_id.meter_uom')
    planning_run_result = fields.Char('Planning Run Result', readonly=True)
    
    def write(self, vals):
        if not 'planning_run_result' in vals:
            raise UserError(_("record cannot be changed; please delete record")) 
        else:
            super().write(vals)
        return True
        
    @api.constrains('meter_id')
    def check_meter_id(self):
        if self.meter_id.state == 'draft':
            raise UserError(_("Meter has not been installed"))
        domain = ['|',('meter_id', '=', self.meter_id.id), ('plan_meter_id', '=', self.meter_id.id)]
        equipment = self.env['mro.equipment'].search(domain, limit=1)
        if not equipment:
            raise UserError(_("Meter has not been assigned to any equipment"))
            
    @api.constrains('date')
    def check_date(self):
        if self.date and self.meter_id.date_meter_install:
            if self.meter_id.date_meter_install >= self.date:
                raise UserError(_("Measure date is before the meter installment date"))
            if self.meter_id.date:
                if self.date < self.meter_id.date:
                    raise UserError(_("Measure date is before the last measure"))
    
    @api.constrains('value')
    def check_value(self):
        if self.value < 0:
            raise UserError(_("Measure has to be a positive value"))
        if self.meter_id.measure_type == 'up':
            line_ids = self.env['mro.meter.line'].search([('meter_id', '=', self.meter_id.id)])
            last_line = 0
            if len(line_ids) > 1:
                last_line = self.env['mro.meter.line'].search([('meter_id', '=', self.meter_id.id)])[-2].value
                if self.value < last_line:
                    raise UserError(_("In Progressive measure type the measure should be greated than the last one"))

