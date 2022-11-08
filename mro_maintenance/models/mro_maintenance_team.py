# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from datetime import datetime, date, time, timedelta
import time


class ResUsers(models.Model):
    _inherit = 'res.users'

    maintenance_team_id = fields.Many2many('mro.maintenance.team', string='Maintenance Team')


class MroMaintenanceTeam(models.Model):
    _name = 'mro.maintenance.team'
    _description = 'Maintenance Teams'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Maintenance Team', required=True)
    order_ids = fields.One2many('mro.order', 'maintenance_team_id', 'Maintenance Orders', copy=False)
    mroequi_count = fields.Integer('Equipments', compute='_mroequi_count')
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Default Warehouse', check_company=True)
    resource_calendar_id = fields.Many2one('resource.calendar', 'Working Time', required=True,
        default=lambda self: self.env.company.resource_calendar_id.id)
    user_id = fields.Many2one('res.users', 'Team Leader')
    member_ids = fields.Many2many('res.users', 'maintenance_team_user_rel', 'maintenance_team_id', 'uid', string='Team Members', copy=False)
    labour_cost_unit = fields.Float('Hourly Labour Cost', digits='Product Price', required=True, default=0.00)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id')
    maintenance_cost_analytic_account_id = fields.Many2one('account.analytic.account', "Maintenance Costs Analytic Account", required=True, check_company=True)
    # Dashboard
    color = fields.Integer('Color', default=0)
    order_count = fields.Integer('Orders', compute='_compute_order_count')
    order_draft_count = fields.Integer('Draft Orders', compute='_compute_order_count')
    order_released_count = fields.Integer('Released Orders', compute='_compute_order_count')
    order_ready_count = fields.Integer('Ready Orders', compute='_compute_order_count')
    order_late_count = fields.Integer('Total Late Orders', compute='_compute_order_count')

    @api.depends('order_ids.maintenance_team_id', 'order_ids.state', 'order_ids.date_start_scheduled')
    def _compute_order_count(self):
        MroOrder = self.env['mro.order']
        result = {wid: {} for wid in self.ids}
        #Count Late Orders
        data = MroOrder.read_group([('maintenance_team_id', 'in', self.ids), ('state', 'in', ('released', 'ready', 'draft')), ('date_start_scheduled', '<', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))], ['maintenance_team_id'], ['maintenance_team_id'])
        count_data = dict((item['maintenance_team_id'][0], item['maintenance_team_id_count']) for item in data)
        #Count All, Draft, Released, Ready Orders
        res = MroOrder.read_group(
            [('maintenance_team_id', 'in', self.ids)],
            ['maintenance_team_id', 'state', 'date_start_scheduled'], ['maintenance_team_id', 'state'],
            lazy=False)
        for res_group in res:
            result[res_group['maintenance_team_id'][0]][res_group['state']] = res_group['__count']
        for maintenance_team in self:
            maintenance_team.order_count = sum(count for state, count in result[maintenance_team.id].items() if state not in ('done', 'cancel'))
            maintenance_team.order_draft_count = result[maintenance_team.id].get('draft', 0)
            maintenance_team.order_released_count = result[maintenance_team.id].get('released', 0)
            maintenance_team.order_ready_count = result[maintenance_team.id].get('ready', 0)
            maintenance_team.order_late_count = count_data.get(maintenance_team.id, 0)

    def _mroequi_count(self):
        equipment = self.env['mro.equipment']
        for maintenance_team in self:
            self.mroequi_count = equipment.search_count([('maintenance_team_id', '=', maintenance_team.id)])
        return True

    def action_view_equipment(self):
        context={'search_default_open': 1,'search_default_maintenance_team_id': [self.id],'default_maintenance_team_id': self.id,}
        return {
            'domain': "[('maintenance_team_id','in',[" + ','.join(map(str, self.ids)) + "])]",
            'context':context,
            'name': _('Equipments'),
            'view_mode': 'tree,form',
            'res_model': 'mro.equipment',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
