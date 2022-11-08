# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import time
from datetime import datetime, date, time, timedelta
import math


class MroGauge(models.Model):
    _name = 'mro.gauge'
    _description = 'Equipment Gauges'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    STATE_SELECTION = [
        ('draft', 'Setup'),
        ('operative', 'Operative')
    ]

    name = fields.Char('Gauge Name', required=True)
    gauge_uom = fields.Many2one('uom.uom', 'Unit of Measure', required=True, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(STATE_SELECTION, 'Status', readonly=True, default='draft')
    gauges_line_ids = fields.One2many('mro.gauge.line', 'gauge_id', string='Points of Measure')
    #threshold_id = fields.Many2one('mro.gauge.threshold', 'Gauge Thresholds', ondelete='restrict', required=True)
    equipment_id = fields.Many2one('mro.equipment', 'Equipment', readonly=True)
    date_gauge_install = fields.Datetime('Gauge installment date', readonly=True)
    doc_count = fields.Integer('Number of documents attached', compute='_compute_attached_docs_count')
    note = fields.Text('Internal Notes')


    def install_gauge(self):
        for gauge in self:
            if not gauge.equipment_id:
                raise UserError(_("Please assign an Equipment before installing it"))
            else:
                gauge.state = 'operative'
                gauge.date_gauge_install = fields.Datetime.now()
        return True

    def detact_gauge(self):
        for gauge in self:
            gauge.state = 'draft'
            gauge.date_gauge_install = False
        return True

    def _compute_attached_docs_count(self):
        attachment = self.env['ir.attachment']
        for gauge in self:
            gauge.doc_count = attachment.search_count(['&',('res_model', '=', 'mro.gauge'), ('res_id', '=', gauge.id)])

    def attachment_tree_view(self):
        self.ensure_one()
        domain = ['&', ('res_model', '=', 'mro.gauge'), ('res_id', 'in', self.ids)]
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


class MroGaugeThreshold(models.Model):
    _name = 'mro.gauge.threshold'
    _description = 'Gauge Thresholds'

    def _get_name(self):
        for threshold in self:
            threshold.name = str(threshold.threshold_min) + ' - ' + str(threshold.threshold_max)

    name = fields.Char('Thresholds', compute='_get_name')
    threshold_min = fields.Float('Threshold Min', required=True)
    threshold_max = fields.Float('Threshold Max', required=True)

    @api.constrains('threshold_min')
    def check_min(self):
        if self.threshold_min > self.threshold_max:
            raise UserError(_("Gauge Threshold Min has to be higher than Gauge Threshold Max"))

    @api.constrains('threshold_max')
    def check_max(self):
        if self.threshold_min > self.threshold_max:
            raise UserError(_("Gauge Threshold Min has to be higher than Gauge Threshold Max"))


class MroGaugeLine(models.Model):
    _name = 'mro.gauge.line'
    _description = 'Gauge Measure'
    _order = 'gauge_id, date desc'

    date = fields.Datetime('Date', required=True)
    value = fields.Float('Measure Value', required=True)
    gauge_id = fields.Many2one('mro.gauge', 'Gauge', ondelete='restrict', required=True)
    processed = fields.Boolean('Measure Processed', default=False)
    planning_run_result = fields.Char('Planning Run Result', readonly=True)
    gauge_uom = fields.Many2one('uom.uom', 'Unit of Measure', related='gauge_id.gauge_uom')

    @api.constrains('gauge_id')
    def check_gauge_id(self):
        if self.gauge_id.state == 'draft':
            raise UserError(_("Gauge has not been installed"))
        equipment_id = self.env['mro.equipment'].search([('gauge_id', '=', self.gauge_id.id)], limit=1).id
        if not equipment_id:
            raise UserError(_("Gauge has not been assigned to any equipment"))

    @api.constrains('date')
    def check_date(self):
        if self.date and self.gauge_id.date_gauge_install:
            if self.gauge_id.date_gauge_install > self.date:
                raise UserError(_("Measure date is before the gauge installment date"))

