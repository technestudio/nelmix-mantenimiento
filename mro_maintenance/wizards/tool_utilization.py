# -*- coding: utf-8 -*-


from odoo import api, fields, models, _


class ToolUtilization(models.TransientModel):
    _name = 'tool.utilization'
    _description = 'Tool Utilization Analysis'


    tool_id = fields.Many2one("mro.tool", "Tool", required=True)


    def get_tool_utilization(self):
        sel_tool_id = self.tool_id.id
        return {'domain': "[('tool_id', '=', %s)]" %sel_tool_id,
                    'name': _("Tool Utilization Analysis"),
                    'view_mode': 'tree,pivot',
                    'auto_search': True,
                    'res_model': 'mro.order.tool.utilization',
                    'view_id': False,
                    'context' : {},
                    'type': 'ir.actions.act_window'}