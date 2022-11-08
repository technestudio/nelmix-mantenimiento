# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from datetime import datetime, date, time, timedelta
from odoo.exceptions import UserError


class MroMaintenancePlanRun(models.TransientModel):
    _name = 'mro.mp.plan'
    _description = 'Maintenance Plan Run'

    equipment_ids = fields.Many2many('mro.equipment', string='Equipments')
    all_equipments = fields.Boolean('All Equipments')


    def planning_run_mp(self):
        equi_ids = False
        messages = []
        if not self.equipment_ids and not self.all_equipments:
            raise UserError(_('select an equipment at least or set All Equipments indicator either'))
        if self.equipment_ids and self.all_equipments:
            raise UserError(_('select an equipment at least or set All Equipments indicator either'))
        if self.all_equipments:
            equi_ids = self.env['mro.equipment'].search([('active', '=', True),('state', 'in',('wh','br','op'))])
        else:
            equi_ids = self.env['mro.equipment'].search([('active', '=', True),('id', 'in', self.equipment_ids.ids),('state', 'in',('wh','br','op'))])
        for equi in equi_ids:
            message = self.single_planning_run_mp(equi)
            if message:
                messages.append(message)
        return messages

    def single_planning_run_mp(self, equi):
        message = False
        if equi.plan_meter_id and equi.plan_meter_id.state == 'operative':
            order_active = self.env['mro.order'].search([('equipment_id', '=', equi.id),('state', '=', 'draft'),('maintenance_type', '=', 'mp')], limit=1)
            if not order_active:
                maintenance_plan_id = self.env['mro.maintenance.plan'].search([('equipment_id', '=', equi.id),('state', '=', 'draft')], limit=1)
                if maintenance_plan_id:
                    if maintenance_plan_id.date_planned <= datetime.now() or maintenance_plan_id.planned_utilization <= equi.plan_meter_id.actual_utilization:
                        task_id = maintenance_plan_id.plan_task_id
                        new_order = self.mro_order_create_mp(task_id, equi, maintenance_plan_id)
                        message = _('new maintenance order created %r' % new_order.name)
                        maintenance_plan_id.write({'planning_run_result': message})
        return message

    def action_planning_run_mp(self):
        messages = self.planning_run_mp()
        t_mess_id = False
        if messages:
            out_message = ''
            for message in messages:
                out_message += '\n' + message
                t_mess_id = self.env["mro.mp.message"].create({'name': out_message}).id
        else:
            t_mess_id = self.env["mro.mp.message"].create({'name': 'no new maintenance order has been created'}).id
        return {
            'name': _('Periodic Planning Run Results'),
            "view_mode": 'form',
            'res_model': "mro.mp.message",
            'res_id': t_mess_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def mro_order_create_mp(self, task_id, equipment_id, maintenance_plan_id):
        new_parts_lines = []
        for line in task_id.parts_lines:
            new_parts_lines.append([0,0,{
                'parts_id': line.parts_id.id,
                'parts_qty': line.parts_qty,
                'parts_uom': line.parts_uom.id,
                'parts_type': line.parts_type,
                'parts_categ_id': line.parts_categ_id.id,
                }])
        new_tool_ids = []
        for tool in task_id.tool_ids:
            new_tool_ids.append([0,0,{
                'tool_id': tool.tool_id.id,
                }])
        order = self.env['mro.order']
        order_id = False
        order_id = order.create({
            'date_planned': datetime.now(),
            'date_scheduled': datetime.now(),
            'state': 'draft',
            'maintenance_type': 'mp',
            'order_duration': task_id.order_duration,
            'equipment_id': equipment_id.id,
            'task_id': task_id.id,
            'origin': 'maintenance plan',
            'maintenance_team_id': equipment_id.maintenance_team_id.id,
            'cause': 'maintenance plan',
            'parts_lines' : new_parts_lines,
            'tool_ids' : new_tool_ids,
            'check_list_id' : task_id.check_list_id.id,
            'maintenance_plan_id' : maintenance_plan_id.id
        })
        return order_id


class MroMPMessage(models.TransientModel):
    _name = "mro.mp.message"
    _description = "MRO Maintenance Plan Temporary Messages"

    name = fields.Text('Result', readonly=True)