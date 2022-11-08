# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    mroequi_count = fields.Integer(compute='_mroequi_count', string=_('##Equipments'))


    def _mroequi_count(self):
        equipment = self.env['mro.equipment']
        for employee in self:
            employee.mroequi_count = equipment.search_count([('employee_id', '=', employee.id)])
        return True

    def action_view_equipment(self):
        context={'search_default_open': 1,'search_default_employee_id': [self.id],'default_employee_id': self.id,}
        return {
            'domain': "[('employee_id','in',[" + ','.join(map(str, self.ids)) + "])]",
            'context':context,
            'name': _('Equipments'),
            'view_mode': 'tree,form',
            'res_model': 'mro.equipment',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
