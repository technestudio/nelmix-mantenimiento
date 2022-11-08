# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MroMaintenancePlan(models.Model):
    _name = 'mro.maintenance.plan'
    _description = 'Equipment Maintenance Plan'
    _order = 'date_planned'


    STATE_SELECTION = [
        ('draft', _('DRAFT')),
        ('done', _('CLOSED')),
    ]

    equipment_id = fields.Many2one('mro.equipment', 'Equipment', readonly=True)
    state = fields.Selection(STATE_SELECTION, 'Status', readonly=True, default='draft')
    plan_meter_id = fields.Many2one('mro.meter', 'Meter')
    plan_meter_uom = fields.Many2one('uom.uom', 'Meter UoM', related='plan_meter_id.meter_uom')
    date_planned = fields.Datetime('Planned Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    planned_utilization = fields.Float('Planned Utilization', required=True, readonly=True, states={'draft': [('readonly', False)]}, group_operator=False)
    planning_run_result = fields.Char('Planning Run Result', readonly=True)
    plan_task_id = fields.Many2one('mro.task', 'Task', required=True, readonly=True, states={'draft': [('readonly', False)]})
    category_id = fields.Many2one('mro.equipment.category', 'Category', related='equipment_id.category_id', store=True)
    order_id = fields.Many2one('mro.order', 'Maintenance Order', readonly=True, states={'draft': [('readonly', False)]})
    maintenance_type = fields.Selection(string='Maintenance Type', related='order_id.maintenance_type', store=True)


    def action_close(self):
        self.write({'state': 'done'})
        return True

    def action_reset(self):
        self.write({'state': 'draft'})
        return True


class PlanMeterAssign(models.TransientModel):
    _name = 'mro.equipment.plan.meter.assignment'
    _description = "Wizard Meter Assignment to Equipment for Maintenance Plan"

    equipment_id = fields.Many2one('mro.equipment', "Equipment", readonly=True)
    plan_meter_id = fields.Many2one('mro.meter', 'Meter',  required=True, domain=[('equipment_id', '=', False)])


    @api.model
    def default_get(self, fields):
        default = super().default_get(fields)
        active_id = self.env.context.get('active_id', False)
        if active_id:
            default['equipment_id'] = active_id
        return default

    def do_assign(self):
        self.ensure_one()
        self.equipment_id.plan_meter_id = self.plan_meter_id.id
        self.plan_meter_id.equipment_id = self.equipment_id.id
        return True