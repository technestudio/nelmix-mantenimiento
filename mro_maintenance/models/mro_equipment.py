# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo import tools


class MroEquipment(models.Model):
    _name = 'mro.equipment'
    _description = 'Equipments'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _mail_post_access = 'write'
    _parent_name = 'parent_id'
    _parent_store = True
    _order = 'complete_name'
    #_rec_name = 'complete_name'


    CRITICALITY_SELECTION = [
        ('0', _('General')),
        ('1', _('Important')),
        ('2', _('Very important')),
        ('3', _('Critical'))
    ]

    STATE_SELECTION = [
        ("wh", _("Warehouse")),
        ("br", _("Breakdown")),
        ("mn", _("Maintenance")),
        ("op", _("Operative")),
        ("sc", _("Scrapped"))
    ]

    @api.model
    def _get_default_functional_location(self):
        return self.env['mro.equipment.location'].search([
            ('default_warehouse', '=', True),
        ], limit=1).id

    name = fields.Char('Equipment Name', required=True)
    state= fields.Selection(STATE_SELECTION, 'Status', tracking=True, required=True, copy=False, default='wh')
    employee_id = fields.Many2one('hr.employee', 'Assigned to', tracking=True)
    active = fields.Boolean('Active', default=True)
    equipment_number = fields.Char('Equipment Code')
    model = fields.Char('Model Code')
    serial = fields.Char('Serial no.')
    vendor_id = fields.Many2one('res.partner', 'Vendor')
    manufacturer_id = fields.Many2one('res.partner', 'Manufacturer')
    start_date = fields.Date('Start Date')
    purchase_date = fields.Date('Purchase Date')
    warranty_start_date = fields.Date('Warranty Start Date')
    warranty_end_date = fields.Date('Warranty End Date')
    asset_id = fields.Char('Asset Number')
    category_id = fields.Many2one('mro.equipment.category', 'Category')
    purchase_value = fields.Float('Purchase Value', tracking=True)
    location_id = fields.Many2one('mro.equipment.location', "Functional Location", required=True, default=_get_default_functional_location)
    note = fields.Text('Internal Notes')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id') 
    mroord_count = fields.Integer('MRO Orders', compute='_mroord_count')
    maintenance_date = fields.Datetime('Next Maintenance Date', compute='_next_maintenance')
    mroreq_count = fields.Integer('MRO Requests', compute='_mroreq_count')
    maintenance_team_id = fields.Many2one('mro.maintenance.team', 'Maintenance Team', required=True, domain="[('company_id','=', company_id)]")
    criticality = fields.Selection(CRITICALITY_SELECTION, 'Criticality', default="0")
    doc_count = fields.Integer("Number of attached documents", compute='_compute_attached_docs_count')
    work_email = fields.Char('Assignee work email', related='employee_id.work_email')
    # gauge management
    gauge_id = fields.Many2one('mro.gauge', string='Gauge', readonly=True)
    date_gauge_install = fields.Datetime('Gauge installment date', related='gauge_id.date_gauge_install')
    threshold_id = fields.Many2one('mro.gauge.threshold', 'Gauge Thresholds', readonly=True)
    threshold_min = fields.Float('Gauge Threshold Min', related='threshold_id.threshold_min', readonly=True)
    threshold_max = fields.Float('Gauge Threshold Max', related='threshold_id.threshold_max', readonly=True)
    gauge_uom = fields.Many2one('uom.uom', string='Gaufe UoM', related='gauge_id.gauge_uom', readonly=True)
    oc_task_id = fields.Many2one('mro.task', 'Task', readonly=True)
    # meter management - periodic maintenance
    meter_id = fields.Many2one('mro.meter', 'Meter', readonly=True)
    theoretical_time = fields.Float('Threshold Time (hours)', readonly=True)
    theorical_utilization = fields.Float('Threshold Utilization', readonly=True) 
    actual_utilization = fields.Float('Actual Utilization', related='meter_id.actual_utilization')
    date_meter_install = fields.Datetime('Meter installment date', related='meter_id.date_meter_install')
    resource_calendar_id = fields.Many2one('resource.calendar', 'Equipment Working Time', readonly=True)
    meter_uom = fields.Many2one('uom.uom', 'Meter UoM', related='meter_id.meter_uom')
    pr_task_id = fields.Many2one('mro.task', 'Task', readonly=True)
    actual_last_utilization = fields.Float('Last Actual Utilization Periodic Maintenance', readonly=True)
    actual_last_maintenance = fields.Datetime('Last Maintenance Date Periodic Maintenance', readonly=True)
    last_measure_date = fields.Datetime('Last Measure Date Periodic Maintenance', readonly=True)
    # hierarchy
    parent_id = fields.Many2one('mro.equipment', 'Parent Equipment', index=True, ondelete='cascade')
    child_ids = fields.One2many('mro.equipment', 'parent_id', 'SubEquipments')
    all_child_ids = fields.One2many('mro.equipment', string='All SubEquipments', compute='_compute_subequipments', compute_sudo=True)
    child_all_count = fields.Integer('All SubEquipments Count', compute='_compute_subequipments', compute_sudo=True)
    parent_path = fields.Char(index=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    # maintenance costs 
    order_ids = fields.One2many('mro.order', 'equipment_id', 'Maintenance Orders')
    act_mat_cost = fields.Float('Actual Material Cost', digits='Product Price', compute='_actual_costs', readonly=True, store=True)
    act_tool_cost = fields.Float('Actual Tool Cost', digits='Product Price', compute='_actual_costs', readonly=True, store=True)
    act_labour_cost = fields.Float('Actual Labour Cost', digits='Product Price', compute='_actual_costs', readonly=True, store=True)
    hierarchy_act_mat_cost = fields.Float('Actual Material Cost Cumulate', digits='Product Price', compute='_actual_costs_hierarchy', readonly=True, store=True)
    hierarchy_act_tool_cost = fields.Float('Actual Tool Cost Cumulate', digits='Product Price', compute='_actual_costs_hierarchy', readonly=True, store=True)
    hierarchy_act_labour_cost = fields.Float('Actual Labour Cost Cumulate', digits='Product Price', compute='_actual_costs_hierarchy', readonly=True, store=True)
    # maintenance plan
    plan_ids = fields.One2many('mro.maintenance.plan', 'equipment_id', 'Equipment Maintenance Plan')
    plan_meter_id = fields.Many2one('mro.meter', 'Meter', readonly=True)
    plan_actual_utilization = fields.Float('Actual Utilization', related='plan_meter_id.actual_utilization')
    plan_date_meter_install = fields.Datetime('Meter installment date', related='plan_meter_id.date_meter_install')
    plan_meter_uom = fields.Many2one('uom.uom', 'Meter UoM', related='plan_meter_id.meter_uom')

    
    def action_plan_meter_line_equipment(self):
        context={'default_meter_id': self.plan_meter_id.id,}
        domain = [('meter_id', '=', self.plan_meter_id.id)]
        return {
            'context': context,
            'domain': domain,
            'name': _('Meter Measures'),
            'view_mode': 'tree',
            'res_model': 'mro.meter.line',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        
    def action_meter_line_equipment(self):
        context={'default_meter_id': self.meter_id.id,}
        domain = [('meter_id', '=', self.meter_id.id)]
        return {
            'context': context,
            'domain': domain,
            'name': _('Meter Measures'),
            'view_mode': 'tree',
            'res_model': 'mro.meter.line',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        
    def action_gauge_line_equipment(self):
        context={'default_gauge_id': self.gauge_id.id,}
        domain = [('gauge_id', '=', self.gauge_id.id)]
        return {
            'context': context,
            'domain': domain,
            'name': _('Gauge Measures'),
            'view_mode': 'tree',
            'res_model': 'mro.gauge.line',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
    
    @api.constrains('name', 'equipment_number')
    def check_unique(self):
        equip_name = self.env['mro.equipment'].search([('name', '=', self.name)])
        if len(equip_name) > 1:
            raise UserError(_("Equipment Name already exists"))
        equip_number = self.env['mro.equipment'].search([('equipment_number', '=', self.equipment_number)])
        if len(equip_number) > 1:
            raise UserError(_("Equipment Number already exists"))
        return True
    
    def action_gauge_unassign(self):
        for equi in self:
            if equi.gauge_id.state == 'operative':
                raise UserError(_("please detach the gauge before unassigning it"))
            else:
                equi.gauge_id.equipment_id = False
                equi.gauge_id = False
                equi.oc_task_id = False
                equi,threshold_id = False
        return True
        
    def action_meter_unassign(self):
        for equi in self:
            if equi.meter_id.state == 'operative':
                raise UserError(_("please detach the meter before unassigning it"))
            else:
                equi.meter_id.equipment_id = False
                equi.meter_id = False
                equi.pr_task_id = False
                equi.theoretical_time = 0.0
                equi.theorical_utilization = 0.0
                equi.resource_calendar_id = False
        return True
        
    def action_plan_meter_unassign(self):
        for equi in self:
            if equi.plan_meter_id.state == 'operative':
                raise UserError(_("please detach the meter before unassigning it"))
            else:
                equi.plan_meter_id.equipment_id = False
                equi.plan_meter_id = False
                equi.plan_ids.unlink()
        return True
    
    @api.constrains('warranty_start_date','warranty_end_date')
    def _check_warranty_dates(self):
        if (self.warranty_start_date and self.warranty_end_date) and (self.warranty_start_date >= self.warranty_end_date):
            raise UserError(_('check validity dates'))
        return True

    @api.constrains('location_id')
    def _check_state_location(self):
        loc_scr_id = self.env['mro.equipment.location'].search([('default_scrap','=',True)],limit=1).id
        loc_whr_id = self.env['mro.equipment.location'].search([('default_warehouse','=',True)], limit=1).id
        for equi in self:
            if equi.state == 'sc' and equi.location_id.id != loc_scr_id:
                raise UserError(_('Scrap Functional Location is necessary'))
            if equi.state == 'wh' and equi.location_id.id != loc_whr_id:
                raise UserError(_('Warehouse Functional Location is necessary'))
            if (equi.state == 'br' or equi.state == 'op') and ((equi.location_id.id == loc_whr_id) or (equi.location_id.id == loc_scr_id)):
                raise UserError(_('Operable Functional Location is necessary'))
            if equi.state == 'mn' and equi.location_id.id == loc_scr_id:
                raise UserError(_('Scrap Functional Location cannot be assigned'))
        return True

    def action_put_warehouse(self):
        for equi in self:
            loc_whr_id = self.env['mro.equipment.location'].search([('default_warehouse','=',True)], limit=1).id
            if not loc_whr_id:
                raise UserError(_("Warehouse Functional Location has not been created"))
            else:
                equi.state = 'wh'
                equi.location_id = loc_whr_id
            equi.state = 'wh'
        return True
        
    def action_in_breakdown(self):
        for equi in self:
            equi.state = 'br'
        return True
        
    def action_scrap(self):
        loc_scr_id = self.env['mro.equipment.location'].search([('default_scrap','=',True)], limit=1).id
        if not loc_scr_id:
            raise UserError(_("Scrap Functional Location has not been created"))
        else:
            for equi in self:
                equi.state = 'sc'
                equi.location_id = loc_scr_id
        return True
        
    def _mroord_count(self):
        order = self.env['mro.order']
        for equi in self:
            self.mroord_count = order.search_count([('equipment_id', '=', equi.id)])
        return True

    @api.depends('order_ids.state', 'order_ids.date_scheduled')
    def _next_maintenance(self):
        for equi in self:
            equi.maintenance_date = False
            order_id = self.env['mro.order'].search(
                [('equipment_id', '=', equi.id),
                ('state', 'not in', ('done','cancel'))],
                limit=1)
            if order_id:
                equi.maintenance_date = order_id.date_start_execution or order_id.date_start_scheduled 
        return True

    def action_view_maintenance_order(self):
        context = {'search_default_equipment_id': [self.id],'default_equipment_id': self.id,}
        return {
            'domain': "[('equipment_id','in',[" + ','.join(map(str, self.ids)) + "])]",
            'context': context,
            'name': _('Maintenance Orders'),
            #'view_mode': 'tree,form',
            'views': [(self.env.ref('mro_maintenance.mro_order_tree_view').id, "tree"), (self.env.ref('mro_maintenance.mro_order_form_view').id, "form")],
            'res_model': 'mro.order',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def _mroreq_count(self):
        request = self.env['mro.request']
        for equi in self:
            self.mroreq_count = request.search_count([('equipment_id', '=', equi.id)])
        return True

    def action_view_maintenance_request(self):
        context={'search_default_equipment_id': [self.id],'default_equipment_id': self.id,}
        return {
            'domain': "[('equipment_id','in',[" + ','.join(map(str, self.ids)) + "])]",
            'context':context,
            'name': _('Maintenance requests'),
            'view_mode': 'tree,form',
            'res_model': 'mro.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def _compute_attached_docs_count(self):
        attachment = self.env['ir.attachment']
        for equipment in self:
            equipment.doc_count = attachment.search_count(['&',('res_model', '=', 'mro.equipment'), ('res_id', '=', equipment.id)])
    
    def attachment_tree_view(self):
        self.ensure_one()
        domain = ['&', ('res_model', '=', 'mro.equipment'), ('res_id', 'in', self.ids)]
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

    @api.constrains('parent_id')
    def _check_hierarchy(self):
        if not self._check_recursion():
            raise UserError(_('Error! You cannot create recursive equipment hierarchy.'))

    def _get_subequipments(self, parents=None):
        if not parents:
            parents = self.env[self._name]
        subequipments = self.env[self._name]
        parents |= self
        direct_subequipments = self.child_ids - parents
        for child in direct_subequipments:
            child_subequipment = child._get_subequipments(parents=parents)
            child.all_child_ids = child_subequipment
            subequipments |= child_subequipment
        return subequipments | direct_subequipments

    @api.depends('child_ids', 'child_ids.child_all_count')
    def _compute_subequipments(self):
        for equipment in self:
            equipment.all_child_ids = equipment._get_subequipments()
            equipment.child_all_count = len(equipment.all_child_ids)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for equipment in self:
            if equipment.parent_id:
                equipment.complete_name = _('%(parent)s / %(own)s') % {
                    'parent': equipment.parent_id.complete_name,
                    'own': equipment.name,
                }
            else:
                equipment.complete_name = equipment.name
            
    @api.constrains('active')
    def check_parent_active(self):
        for equipment in self:
            if (equipment.active and equipment.parent_id and equipment.parent_id not in self and not equipment.parent_id.active):
                raise UserError(_('Please activate first parent equipment %s')% equipment.parent_id.complete_name)
                
    def write(self, vals):
        if self and 'active' in vals and not vals['active']:
            self.mapped('child_ids').write({'active': False})
        return super().write(vals)
        
    @api.depends('order_ids.act_mat_cost','order_ids.act_tool_cost','order_ids.act_labour_cost')
    def _actual_costs(self):
        act_mat_cost = 0.0
        act_tool_cost = 0.0
        act_labour_cost = 0.0
        for equipment in self:
            domain = [('equipment_id', '=', equipment.id),('state', '=', 'done')]
            equipment_cost_data = self.env['mro.order'].read_group(
                domain=domain,
                fields=['currency_id', 'act_mat_cost', 'act_tool_cost', 'act_labour_cost'],
                groupby=['currency_id'],
                lazy=False,
            )
            act_mat_cost = sum(map(
                lambda x: self.env['res.currency'].browse(x['currency_id'][0])._convert(
                    x['act_mat_cost'],
                    self.env.user.company_id.currency_id,
                    self.env.user.company_id,
                    fields.Date.today()
                ),
                equipment_cost_data
            ))
            act_tool_cost = sum(map(
                lambda x: self.env['res.currency'].browse(x['currency_id'][0])._convert(
                    x['act_tool_cost'],
                    self.env.user.company_id.currency_id,
                    self.env.user.company_id,
                    fields.Date.today()
                ),
                equipment_cost_data
            ))
            act_labour_cost = sum(map(
                lambda x: self.env['res.currency'].browse(x['currency_id'][0])._convert(
                    x['act_labour_cost'],
                    self.env.user.company_id.currency_id,
                    self.env.user.company_id,
                    fields.Date.today()
                ),
                equipment_cost_data
            ))
            equipment.act_mat_cost = act_mat_cost
            equipment.act_tool_cost = act_tool_cost
            equipment.act_labour_cost = act_labour_cost
        return True
            
    @api.depends('child_ids.order_ids.act_mat_cost','child_ids.order_ids.act_tool_cost','child_ids.order_ids.act_labour_cost','order_ids.act_mat_cost','order_ids.act_tool_cost','order_ids.act_labour_cost')
    def _actual_costs_hierarchy(self):
        act_mat_cost_hierarchy = 0.0
        act_tool_cost_hierarchy = 0.0
        act_labour_cost_hierarchy = 0.0
        for equipment in self:
            if not equipment.child_all_count == 0:
                domain = [('equipment_id', 'child_of', equipment.id),('state', '=', 'done')]
                equipment_cost_data_hierarchy = self.env['mro.order'].read_group(
                    domain=domain,
                    fields=['currency_id', 'act_mat_cost', 'act_tool_cost', 'act_labour_cost'],
                    groupby=['currency_id'],
                    lazy=False,
                )
                act_mat_cost_hierarchy = sum(map(
                    lambda x: self.env['res.currency'].browse(x['currency_id'][0])._convert(
                        x['act_mat_cost'],
                        self.env.user.company_id.currency_id,
                        self.env.user.company_id,
                        fields.Date.today()
                    ),
                    equipment_cost_data_hierarchy
                ))
                act_tool_cost_hierarchy = sum(map(
                    lambda x: self.env['res.currency'].browse(x['currency_id'][0])._convert(
                        x['act_tool_cost'],
                        self.env.user.company_id.currency_id,
                        self.env.user.company_id,
                        fields.Date.today()
                    ),
                    equipment_cost_data_hierarchy
                ))
                act_labour_cost_hierarchy = sum(map(
                    lambda x: self.env['res.currency'].browse(x['currency_id'][0])._convert(
                        x['act_labour_cost'],
                        self.env.user.company_id.currency_id,
                        self.env.user.company_id,
                        fields.Date.today()
                    ),
                    equipment_cost_data_hierarchy
                ))
            if act_mat_cost_hierarchy == 0.0:
                equipment.hierarchy_act_mat_cost = equipment.act_mat_cost
            else:
                equipment.hierarchy_act_mat_cost = act_mat_cost_hierarchy
            if act_tool_cost_hierarchy == 0.0:
                equipment.hierarchy_act_tool_cost = equipment.act_tool_cost
            else:
                equipment.hierarchy_act_tool_cost = act_tool_cost_hierarchy
            
            if act_labour_cost_hierarchy == 0.0:
                equipment.hierarchy_act_labour_cost = equipment.act_labour_cost
            else:
                equipment.hierarchy_act_labour_cost = act_labour_cost_hierarchy
        return True
            

class LocAssign(models.TransientModel):
    _name = 'mro.equipment.location.assignment'
    _description = "Wizard Functional Location Assignment to Equipment"

    equipment_id = fields.Many2one('mro.equipment', "Equipment", readonly=True)
    location_id = fields.Many2one('mro.equipment.location', "Functional Location", required=True)
    
    @api.model
    def default_get(self, fields):
        default = super().default_get(fields)
        active_id = self.env.context.get('active_id', False)
        if active_id:
            default['equipment_id'] = active_id
        return default
    
    def do_assign(self):
        self.ensure_one()
        loc_whr_id = self.env['mro.equipment.location'].search([('default_warehouse','=',True)], limit=1).id
        loc_scr_id = self.env['mro.equipment.location'].search([('default_scrap','=',True)], limit=1).id
        if self.location_id == loc_whr_id or self.location_id == loc_scr_id:
            raise UserError(_("Operable Functional Location has to be assigned"))
        else:
            self.equipment_id.state = 'op'
            self.equipment_id.location_id = self.location_id
        return True
   
        
class GaugeAssign(models.TransientModel):
    _name = 'mro.equipment.gauge.assignment'
    _description = "Wizard Gauge Assignment to Equipment"

    equipment_id = fields.Many2one('mro.equipment', "Equipment", readonly=True)
    gauge_id = fields.Many2one('mro.gauge', 'Gauge',  required=True, domain=[('equipment_id', '=', False)])
    oc_task_id = fields.Many2one('mro.task', 'Task', required=True)
    threshold_id = fields.Many2one('mro.gauge.threshold', 'Gauge Thresholds', required=True)
    category_id = fields.Many2one('mro.equipment.category', 'Category', related='equipment_id.category_id', store=True)
    
    @api.model
    def default_get(self, fields):
        default = super().default_get(fields)
        active_id = self.env.context.get('active_id', False)
        if active_id:
            default['equipment_id'] = active_id
        return default
    
    def do_assign(self):
        self.ensure_one()
        self.equipment_id.gauge_id = self.gauge_id.id
        self.equipment_id.oc_task_id = self.oc_task_id.id
        self.equipment_id.threshold_id = self.threshold_id.id
        self.gauge_id.equipment_id = self.equipment_id.id
        return True
  
        
class MeterAssign(models.TransientModel):
    _name = 'mro.equipment.meter.assignment'
    _description = "Wizard Meter Assignment to Equipment"

    equipment_id = fields.Many2one('mro.equipment', string=_("Equipment"), readonly=True)
    meter_id = fields.Many2one('mro.meter', string=_('Meter'),  required=True, domain=[('equipment_id', '=', False)])
    pr_task_id = fields.Many2one('mro.task', 'Task', required=True)
    category_id = fields.Many2one('mro.equipment.category', 'Category', related='equipment_id.category_id', store=True)
    theoretical_time = fields.Float(_('Threshold Time (hours)'), required=True)
    theorical_utilization = fields.Float(_('Threshold Utilization'), required=True) 
    resource_calendar_id = fields.Many2one('resource.calendar', string=_('Equipment Working Time'), required=True)
    meter_uom = fields.Many2one('uom.uom', string=_('Unit of Measure'), related='meter_id.meter_uom')
    
    @api.model
    def default_get(self, fields):
        default = super().default_get(fields)
        active_id = self.env.context.get('active_id', False)
        if active_id:
            default['equipment_id'] = active_id
        return default
    
    def do_assign(self):
        self.ensure_one()
        if self.meter_id and self.theoretical_time <= 0:
            raise UserError('set a positive threshold time')
        if self.meter_id and self.theorical_utilization <= 0:
            raise UserError('set a positive threshold utilization')
        self.equipment_id.meter_id = self.meter_id.id
        self.equipment_id.pr_task_id = self.pr_task_id.id
        self.equipment_id.theoretical_time = self.theoretical_time
        self.equipment_id.theorical_utilization = self.theorical_utilization
        self.equipment_id.resource_calendar_id = self.resource_calendar_id.id
        self.meter_id.equipment_id = self.equipment_id.id
        return True
        
