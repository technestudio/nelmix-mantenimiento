# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class MroEquipmentCategory(models.Model):
    _description = 'Equipment Category'
    _name = 'mro.equipment.category'

    name = fields.Char('Category Name', required=True)
    categ_no = fields.Char('Category Code')
    active = fields.Boolean('Active', default=True)
    mroequi_count = fields.Integer('Equipments', compute='_mroequi_count')
    note = fields.Text('Internal Notes')


    def unlink(self):
        for category in self:
            if category.mroequi_count > 0:
                raise UserError(_("You cannot delete an equipment category containing equipments"))
        res = super().unlink()
        return res

    def _mroequi_count(self):
        equipment = self.env['mro.equipment']
        for category in self:
            self.mroequi_count = equipment.search_count([('category_id', '=', category.id)])
        return True

    def action_view_equipment(self):
        context={'search_default_open': 1,'search_default_category_id': [self.id],'default_category_id': self.id,}
        return {
            'domain': "[('category_id','in',[" + ','.join(map(str, self.ids)) + "])]",
            'context':context,
            'name': _('Equipments'),
            'view_mode': 'tree,form',
            'res_model': 'mro.equipment',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }