# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from datetime import datetime, date, time, timedelta
from odoo.exceptions import UserError


class MroPeriodicPlan(models.TransientModel):
    _name = 'mro.pr.plan'
    _description = 'Planning Run Periodic'

    equipment_ids = fields.Many2many('mro.equipment', string='Equipments')
    all_equipments = fields.Boolean('All Equipments')


    def planning_run_pr(self):
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
            message = self.single_planning_run_pr(equi)
            if message:
                messages.append(message)
        return messages

    def single_planning_run_pr(self, equi):
        message = False
        if equi.meter_id and equi.pr_task_id and equi.meter_id.state == 'operative':
            order_active = self.env['mro.order'].search([('equipment_id', '=', equi.id),('state', '=', 'draft'),('maintenance_type', '=', 'pr')], limit=1)
            if not order_active:
                start_dt = equi.actual_last_maintenance or equi.meter_id.date_meter_install
                end_dt = datetime.now()
                last_utilization = equi.actual_last_utilization or 0.0
                last_date = equi.last_measure_date or datetime.strptime('1900-01-01','%Y-%m-%d')
                hours = equi.resource_calendar_id.get_work_hours_count(start_dt,end_dt,True,None)
                if hours > equi.theoretical_time or (equi.meter_id.actual_utilization - last_utilization) >= equi.theorical_utilization:
                    task_id = equi.pr_task_id
                    new_order = self.mro_order_create_pr(task_id, equi)
                    message = _('new maintenance order created %r' % new_order.name)
                    last_measure = self.env['mro.meter.line'].search([('meter_id', '=', equi.meter_id.id),('date', '>', last_date)], order='date desc', limit=1)
                    if last_measure:
                        last_measure.write({'planning_run_result': message})
        return message

    def action_planning_run_pr(self):
        messages = self.planning_run_pr()
        t_mess_id = False
        if messages:
            out_message = ''
            for message in messages:
                out_message += '\n' + message
                t_mess_id = self.env["mro.pr.message"].create({'name': out_message}).id
        else:
            t_mess_id = self.env["mro.pr.message"].create({'name': 'no new maintenance order has been created'}).id
        return {
            'name': _('Periodic Planning Run Results'),
            "view_mode": 'form',
            'res_model': "mro.pr.message",
            'res_id': t_mess_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def mro_order_create_pr(self, task_id, equipment_id):
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
            'maintenance_type': 'pr',
            'order_duration': task_id.order_duration,
            'equipment_id': equipment_id.id,
            'task_id': task_id.id,
            'origin': 'periodic maintenance',
            'maintenance_team_id': equipment_id.maintenance_team_id.id,
            'cause': 'periodic maintenance',
            'parts_lines' : new_parts_lines,
            'tool_ids' : new_tool_ids,
            'check_list_id' : task_id.check_list_id.id,
            'actual_utilization' : equipment_id.meter_id.actual_utilization,
            'date_measure' : equipment_id.meter_id.date
        })
        return order_id


class MroPRMessage(models.TransientModel):
    _name = "mro.pr.message"
    _description = "MRO Periodic Temporary Messages"

    name = fields.Text('Result', readonly=True)