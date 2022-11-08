# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo import exceptions


class MroEquipmentLocation(models.Model):   
    _name = "mro.equipment.location"
    _description = "Functional Location" 
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_id'
    _rec_name = 'complete_name'
    
    
    name = fields.Char('Functional Location Name', required=True)
    default_warehouse = fields.Boolean('Warehouse Functional Location', copy=False)
    default_scrap = fields.Boolean('Scrap Functional Location', copy=False)
    active = fields.Boolean('Active', default=True)
    parent_id = fields.Many2one('mro.equipment.location', 'Parent Location', ondelete='cascade')
    parent_path = fields.Char('Parent path', index=True)
    child_ids = fields.One2many('mro.equipment.location', 'parent_id', 'Sublocations')
    complete_name = fields.Char("Full Location Name", compute='_compute_complete_name', store=True)
    mroequi_count = fields.Integer('Equipments', compute='_mroequi_count')
    note = fields.Text('Internal Notes')
    
 
    @api.constrains('parent_id')
    def _check_hierarchy(self):
        if not self._check_recursion():
            raise exceptions.UserError(_('Error! You cannot create recursive locations.'))
    
    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for location in self:
            if location.parent_id:
                location.complete_name = '%s / %s' % (location.parent_id.complete_name, location.name)
            else:
                location.complete_name = location.name

    @api.model
    def create(self, vals):
        res = super().create(vals)
        loc_obj_whr = self.env['mro.equipment.location'].search([('default_warehouse','=',True)])
        if len(loc_obj_whr) > 1:
            raise exceptions.UserError(_("Warehouse Functional Location has been already set"))
        loc_obj_scr = self.env['mro.equipment.location'].search([('default_scrap','=',True)])
        if len(loc_obj_scr) > 1:
            raise exceptions.UserError(_("Scrap Functional Location has been already set"))
        return res
    
    def write(self, vals):
        res = super().write(vals)
        loc_obj_whr = self.env['mro.equipment.location'].search([('default_warehouse','=',True)])
        if len(loc_obj_whr) > 1:
            raise exceptions.UserError(_("Warehouse Functional Location has been already set"))
        loc_obj_scr = self.env['mro.equipment.location'].search([('default_scrap','=',True)])
        if len(loc_obj_scr) > 1:
            raise exceptions.UserError(_("Scrap Functional Location has been already set"))
        return res

    @api.constrains('default_warehouse','default_scrap')
    def _default_indicators(self):
        if self.default_warehouse and self.default_scrap:
            raise exceptions.UserError(_('Warehouse Location cannot be set as Scrap also!'))
        return True
        
    def unlink(self):
        for location in self:
            if location.mroequi_count > 0:
                raise exceptions.UserError(_("You cannot delete a location assigned to equipments"))
        res = super().unlink()
        return res
    
    def _mroequi_count(self):
        read_group_res = self.env['mro.equipment'].read_group([('location_id', 'child_of', self.ids)], ['location_id'], ['location_id'])
        group_data = dict((data['location_id'][0], data['location_id_count']) for data in read_group_res)
        for location in self:
            mroequi_count = 0
            for sub_location_id in location.search([('id', 'child_of', location.ids)]).ids:
                mroequi_count += group_data.get(sub_location_id, 0)
            location.mroequi_count = mroequi_count

    def action_view_equipment(self):
        context={'search_default_open': 1,'search_default_location_id': [self.id],'default_location_id': self.id,}
        return {
            'domain': "[('location_id','in',[" + ','.join(map(str, self.ids)) + "])]",
            'context':context,
            'name': _('Equipments'),
            'view_mode': 'tree,form',
            'res_model': 'mro.equipment',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
