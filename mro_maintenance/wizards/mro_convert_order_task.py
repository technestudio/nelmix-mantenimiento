# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MroConvertOrder(models.TransientModel):
    _name = 'mro.convert.order'
    _description = 'Convert Order to Task'


    task_name = fields.Char('Task Name', required=True)

    def convert_order(self):
        order_id = self.env.context.get('active_id', False)
        if order_id:
            order = self.env['mro.order'].browse(order_id)
            if not order.check_list_id:
                raise UserError(_('Please enter a check list'))
            new_parts_lines = []
            for line in order.parts_lines:
                new_parts_lines.append([0,0,{
                    'parts_id': line.parts_id.id,
                    'parts_qty': line.parts_qty,
                    'parts_uom': line.parts_uom.id,
                    'parts_type': line.parts_type,
                    'parts_categ_id': line.parts_categ_id.id
                    }])

            new_tool_ids = []
            for tool in order.tool_ids:
                new_tool_ids.append([0,0,{
                    'tool_id': tool.tool_id.id,
                    }])
            values = {
                'name': self.task_name,
                'category_id': order.equipment_id.category_id.id,
                'parts_lines': new_parts_lines,
                'tool_ids': new_tool_ids,
                'check_list_id': order.check_list_id.id,
                'order_duration': order.order_duration,
            }
            return {
                'name': _('Task'),
                'view_mode': 'form',
                'res_model': 'mro.task',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': self.env['mro.task'].create(values).id
            }
        return True