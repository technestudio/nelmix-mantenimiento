# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, date, time, timedelta

from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES


class StockMove(models.Model):
    _inherit = "stock.move"

    maintenance_id =  fields.Many2one('mro.order', 'Maintenance Order', check_company=True)


    #@api.depends('maintenance_id.priority')
    #def _compute_priority(self):
    #    super()._compute_priority()
    #    for move in self:
    #        move.priority = move.maintenance_id.priority or move.priority or '0'


class MroOrder(models.Model):
    _name = 'mro.order'
    _description = 'Maintenance Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'maintenance_priority desc, date_start_execution asc,id'

    STATE_SELECTION = [
        ('draft', 'DRAFT'),
        ('released', 'WAITING PARTS'),
        ('ready', 'READY TO MAINTENANCE'),
        ('done', 'CLOSED'),
        ('cancel', 'REJECTED')
    ]

    MAINTENANCE_TYPE_SELECTION = [
        ('bm', 'Corrective'),
        ('pm', 'Preventive'),
        ('oc', 'On Condition'),
        ('pr', 'Periodic'),
        ('in', 'Inspection'),
        ('rf', 'Retrofit'),
        ('mp', 'Maintenance Plan'),
    ]

    PRIORITY_SELECTION = [
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Breakdown')
    ]

    name = fields.Char('Reference', required=True, index=True, copy=False, readonly=True, default='New')
    origin = fields.Char('Source Document', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(STATE_SELECTION, 'Status', readonly=True, default='draft')
    maintenance_type = fields.Selection(MAINTENANCE_TYPE_SELECTION, 'Maintenance Type', required=True, default='bm')
    task_id = fields.Many2one('mro.task', 'Task', readonly=True, states={'draft': [('readonly', False)]})
    equipment_id = fields.Many2one('mro.equipment', 'Equipment', required=True, domain="[('company_id','=', company_id)]",
        readonly=True, states={'draft': [('readonly', False)]})
    nochange = fields.Boolean('No change indicator', compute='_get_nochange_indicator', store=True, default=False)
    user_id = fields.Many2one('res.users', 'Responsible Technician', readonly=True, states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, readonly=True)
    category_id = fields.Many2one('mro.equipment.category', 'Equipment Category', related='equipment_id.category_id', readonly=True)
    active = fields.Boolean('Active', default=True)
    request_id = fields.Many2one('mro.request', 'Maintenance Request', readonly=True)
    maintenance_team_id = fields.Many2one('mro.maintenance.team', 'Maintenance Team', required=True, 
        domain="[('company_id','=', company_id)]", readonly=True, states={'draft': [('readonly', False)]})
    maintenance_priority = fields.Selection(PRIORITY_SELECTION, 'Maintenance Priority', default='0', required=True, 
        readonly=True, states={'draft': [('readonly', False)]})
    #priority = fields.Selection(PROCUREMENT_PRIORITIES, string='Procurement Priority', default='0', index=True,
    #    help="Components will be reserved first for the Maintenance Orders with the highest priorities.")
    # dates
    date_planned = fields.Datetime('Requested Date', required=True)
    date_scheduled = fields.Datetime('Planned End Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    date_start_scheduled = fields.Datetime('Planned Start Date', readonly=True, compute='_get_scheduled_dates', store=True)
    date_execution = fields.Datetime('Execution End Date', readonly=True)
    date_start_execution = fields.Datetime('Execution Start Date', readonly=True)
    date_document = fields.Datetime('Document Date', default=fields.Datetime.now(), required=True, readonly=True, states={'draft': [('readonly', False)]})
    # text
    cause = fields.Text('Cause', readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Text('Description')
    reject_reason = fields.Text('Reject Reason', readonly=True)
    # parts
    parts_stock_moves = fields.One2many('stock.move', 'maintenance_id', 'Parts Stock Moves')
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement group', copy=False)
    parts_lines = fields.One2many('mro.order.parts.line', 'maintenance_id', 'Planned Spare Parts', readonly=True, states={'draft':[('readonly',False)]})
    delivery_count = fields.Integer('Inventory Movements Count', compute='_compute_picking_ids')
    picking_ids = fields.Many2many('stock.picking', 'Pickings related to a Maintenance Order', compute='_compute_picking_ids')    
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type', readonly=True, states={'draft': [('readonly', False)]})
    picking_id = fields.Many2one('stock.picking', 'Picking')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True,  states={'draft': [('readonly', False)]})
    location_parts_id = fields.Many2one('stock.location', 'Spare Parts Location', readonly=True, states={'draft': [('readonly', False)]})
    # operations
    tool_ids = fields.One2many('mro.order.tool', 'maintenance_id', 'Tools', readonly=True, states={'draft': [('readonly', False)]})
    check_list_id = fields.Many2one('mro.check.list', 'Check List', readonly=True, states={'draft': [('readonly', False)]})
    checklist_progress = fields.Float('Progress', compute='_checklist_progress', store=True)
    activity = fields.Many2many('mro.activity', string='Operations', domain="[('check_list_id','=', check_list_id)]", 
        readonly=True, states={'released': [('readonly', False)],'ready': [('readonly', False)]})
    order_duration = fields.Float('Duration', readonly=True, states={'draft':[('readonly',False)]})
    # document management
    doc_count = fields.Integer("Number of attached documents", compute='_compute_attached_docs_count')
    doc_count_task = fields.Integer("Number of task attached documents", compute='_compute_attached_docs_task_count')
    doc_count_req = fields.Integer("Number of request attached documents", compute='_compute_attached_docs_request_count')
    # maintenance costs
    std_mat_cost = fields.Float('Material Cost', digits='Product Price', compute='_calculate_planned_costs', store=True)
    std_tool_cost = fields.Float('Tool Cost', digits='Product Price', compute='_calculate_planned_costs', store=True)
    std_labour_cost = fields.Float('Labour Cost', digits='Product Price', compute='_calculate_planned_costs', 
        store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id.id)
    n_resourse = fields.Integer('# Allocated Resourses', default=1, required=True, readonly=True, states={'draft':[('readonly',False)]})
    act_mat_cost = fields.Float('Material Cost', digits='Product Price', readonly=True)
    act_tool_cost = fields.Float('Tool Cost', digits='Product Price', readonly=True)
    act_labour_cost = fields.Float('Labour Cost', digits='Product Price', readonly=True)
    actual_duration = fields.Float('Actual Duration', readonly=True)
    delta_duration = fields.Float('Delta Duration', readonly=True, default=0.0)
    delta_mat_cost = fields.Float('Delta Material Cost', digits='Product Price', readonly=True, default=0.0)
    delta_tool_cost = fields.Float('Delta Tool Cost', digits='Product Price', readonly=True, default=0.0)
    delta_labour_cost = fields.Float('Delta Labour Cost', digits='Product Price', readonly=True, default=0.0)
    act_mat_cost_unplanned = fields.Float('Actual Material Cost Unplanned', digits='Product Price', readonly=True, default=0.0)
    # periodic maintenance
    actual_utilization = fields.Float('Actual Utilization Periodic Maintenance', readonly=True)
    date_measure = fields.Datetime('Measure Date', readonly=True)
    # maintenance plan
    maintenance_plan_id = fields.Many2one('mro.maintenance.plan', 'Maintenance Plan Item', readonly=True)

    def unlink(self):
        for record in self:
            if record.state in ('released','ready'):
                raise UserError(_('Maintenance Order is still running'))
        return super().unlink()

    @api.depends('request_id','state')
    def _get_nochange_indicator(self):
        for record in self:
            if record.request_id:
                record.nochange = True
            if record.state != 'draft':
                record.nochange = True
        return True
    
    @api.depends('check_list_id','activity')
    def _checklist_progress(self):
        progress = 0.0
        for order in self:
            total_len = self.env['mro.activity'].search_count([('check_list_id', '=', order.check_list_id.id)])
            check_list_len = len(order.activity)
            if total_len != 0:
                progress = (check_list_len*100) / total_len
            else:
                progress = 100
            order.checklist_progress = progress
        return True
    
    @api.model
    def _create_sequence(self, vals):
        if not vals.get('name') or vals.get('name') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('mro.order') or 'New'
        return vals
        
    @api.model
    def create(self, vals):
        vals = self._create_sequence(vals)
        order = super().create(vals)
        group_id = self.env['procurement.group'].create({'name': order.name})
        order.procurement_group_id = group_id.id
        return order
    
    @api.onchange('maintenance_team_id')
    def onchange_maintenance_team(self):
        members = []
        for order in self:
            if order.maintenance_team_id:
                for member in order.maintenance_team_id.member_ids:
                    members.append(member.id)
        return {'domain': {'user_id':[('id','in',members)]}}
        
    @api.onchange('maintenance_team_id')
    def get_default_warehouse(self):
        for order in self:
            if order.maintenance_team_id:
                order.warehouse_id = order.maintenance_team_id.warehouse_id.id
    
    @api.onchange('warehouse_id')
    def _get_location_parts_id(self):
        if self.warehouse_id:
            self.location_parts_id = self.warehouse_id.lot_stock_id.id
            self.picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'internal'),('warehouse_id', '=', self.warehouse_id.id)], limit=1).id
            self.company_id = self.warehouse_id.company_id.id
    
    @api.onchange('equipment_id','maintenance_type')
    def onchange_equipment(self):
        if self.equipment_id:
            self.category_id = self.equipment_id.category_id
        return {'domain': {'task_id': [('category_id', '=', self.category_id.id)]}}

    @api.onchange('date_planned')
    def onchange_planned_date(self):
        self.date_scheduled = self.date_planned

    @api.onchange('task_id')
    def onchange_task(self):
        task = self.task_id
        self.order_duration = task.order_duration
        if self.parts_lines or self.tool_ids:
            raise UserError(_('before changing task, please delete tools and part list'))
        new_parts_lines = []
        for line in task.parts_lines:
            new_parts_lines.append([0,0,{
                'parts_id': line.parts_id.id,
                'parts_qty': line.parts_qty,
                'parts_uom': line.parts_uom.id,
                'parts_type': line.parts_type,
                'parts_categ_id': line.parts_categ_id.id,
                }])
        self.parts_lines = new_parts_lines
        new_tool_ids = []
        for tool in task.tool_ids:
            new_tool_ids.append([0,0,{
                'tool_id': tool.tool_id.id,
                }])
        self.tool_ids = new_tool_ids
        self.check_list_id = self.task_id.check_list_id.id
     
    @api.constrains('equipment_id')
    def _check_scrap(self):
        for order in self:
            if order.equipment_id.state == 'sc':
                raise UserError(_('equipment has been scrapped'))
        return True

    @api.depends('date_scheduled','order_duration', 'maintenance_team_id')
    def _get_scheduled_dates(self):
        for order in self:
            duration = -order.order_duration
            start_date = order.date_scheduled
            if order.date_scheduled and order.maintenance_team_id:
                order.date_start_scheduled = order.maintenance_team_id.resource_calendar_id.plan_hours(duration, start_date, True)
        return True
                
    @api.onchange('maintenance_priority')
    def onchange_maintenance_priority(self):
        if self.maintenance_priority == '3':
            self.date_planned = datetime.today()
                
    @api.onchange('equipment_id')
    def _get_maintenance_team(self):
        if self.equipment_id:
            self.maintenance_team_id = self.equipment_id.maintenance_team_id
    
    @api.onchange('date_planned')
    def _check_date_planned(self):
        if self.request_id:
            raise UserError(_('Requested Date cannot be changed because it has been entered in Maintenance Request'))
                
    @api.constrains('maintenance_priority', 'maintenance_type')
    def _check_maintenance_type(self):
        for order in self:
            if order.maintenance_priority == '3' and not order.maintenance_type == 'bm':
                raise UserError(_('corrective maintenance type has to be chosen for Equipment in breakdown'))
        return True

    def action_confirm(self):        
        request_obj = self.env['mro.request']
        cons_loc_id = self.env['stock.location'].search([('usage', '=', 'equi')], limit=1).id
        active_orders = self.env['mro.order'].search([('state', 'in', ('released','ready'),)])
        tools = []
        for order in self:
            for tool in order.tool_ids:
                tools.append(tool.tool_id)
            if any(tool.date_next_calibration and tool.date_next_calibration <= order.date_start_scheduled for tool in order.tool_ids):
                raise UserError(_('A tool has to be calibrated at least'))
        for active_order in active_orders:
            if active_order.equipment_id == self.equipment_id:
                raise UserError(_('Equipment already in maintenance'))
            for tool in active_order.tool_ids:
                if tool.tool_id in tools:
                    raise UserError(_('Tool already in use'))
        for order in self:
            if not order.maintenance_team_id:
                raise UserError(_('please enter a Maintenance Team'))
            if not order.user_id:
                raise UserError(_('please enter a Responsible Technician'))
            products = self.env['mro.order.parts.line'].search([('maintenance_id', '=', order.id),('parts_type', '=', 'product')])
            if not order.warehouse_id and products:
                raise UserError(_('please enter a Warehouse'))
            if not order.location_parts_id and products:
                raise UserError(_('please enter a Location'))
            if not order.picking_type_id and products:
                raise UserError(_('please enter an Operation Type'))
        for order in self:
            products = self.env['mro.order.parts.line'].search([('maintenance_id', '=', order.id),('parts_type', '=', 'product')])
            if len(order.parts_lines) > 0 and products:
                order._generate_parts_moves()
                Picking = self.env['stock.picking']
                picking_id = Picking.create(order.get_picking_values()).id
                order.picking_id = picking_id
                order.parts_stock_moves.write({'picking_id': picking_id})
                order.write({'state':'released'})
                order.check_availability()
            else:
                order.action_ready()
            order.equipment_id.state = 'mn'
            order.date_start_execution = datetime.today()
            if order.tool_ids:
                for tool in order.tool_ids:
                    tool.tool_id.order_id = order.id
        return True

    def _generate_parts_moves(self):
        cons_loc_id = self.env['stock.location'].search([('usage', '=', 'equi')], limit=1).id
        for order in self:
            for line in order.parts_lines:
                if line.parts_id.type == 'product':
                    move = self.env['stock.move'].create({
                        'name': order.name,
                        'date': order.date_start_scheduled,
                        'date_deadline': order.date_start_scheduled,
                        'product_id': line.parts_id.id,
                        'product_uom': line.parts_uom.id,
                        'product_uom_qty': line.parts_qty,
                        'location_id': order.location_parts_id.id,
                        'location_dest_id': cons_loc_id,
                        'company_id': order.company_id.id,
                        'origin': order.name,
                        'reference': order.name,
                        'maintenance_id': order.id,
                        'group_id': order.procurement_group_id.id,
                    })
                    move._action_confirm()

    def get_picking_values(self):
        cons_loc_id = self.env['stock.location'].search([('usage', '=', 'equi')], limit=1).id
        return {
            'origin': self.name,
            'company_id': self.company_id.id,
            'location_id': self.location_parts_id.id,
            'location_dest_id': cons_loc_id,
            'scheduled_date': self.date_start_scheduled,
            'group_id': self.procurement_group_id.id,
            'move_type': 'direct',
            'picking_type_id': self.picking_type_id.id,
        }

    def check_availability(self):
        cons_loc_id = self.env['stock.location'].search([('usage', '=', 'equi')], limit=1).id
        for order in self:
            if order.parts_lines:
                order.parts_stock_moves._action_assign()
                states = []
                move_ids = self.env['stock.move'].search([('maintenance_id', '=', order.id)])
                states += [move.state not in ('assigned','done','cancel') for move in move_ids if move.location_dest_id.id == cons_loc_id]
                if not(any(states) or len(states) == 0):
                    order.action_ready() 
        return True
    
    def action_ready(self):
        self.write({'state': 'ready'})
        return True

    def action_done_before(self):
        for order in self:
            if not order.state == 'ready':
                raise UserError(_("order not in 'ready for maintenance' state"))
            else:    
                if len(order.parts_stock_moves) > 0:
                    picking_ids = self.env['stock.picking'].search([('group_id', '=', order.procurement_group_id.id)])
                    for picking in picking_ids:
                        if not (picking.state ==  'done' or picking.state ==  'cancel'):
                            raise UserError(_('please process Goods Movements'))
                if order.checklist_progress != 100:
                    raise UserError(_('please complete activities in check list'))
        return {'name': _("Record Actual Duration"),
                'res_model': 'mro.order.duration.record',
                'binding_model_id': 'mro.order',
                'view_mode': 'form',
                'target' : "new",
                'type': 'ir.actions.act_window'}

    def action_done_after(self):
        for order in self:
            order.write({
                'date_execution': fields.Datetime.now(),
                'state': 'done',
                #'priority': '0',
            })
            for tool in order.tool_ids:
                tool.tool_id.order_id = False
            loc_whr_id = self.env['mro.equipment.location'].search([('default_warehouse','=',True)], limit=1).id
            if order.equipment_id.location_id.id == loc_whr_id:
                order.equipment_id.state = 'wh'
            else:
                order.equipment_id.state = 'op'
            order._calculate_actual_costs()
            order._analytic_postings()
            if order.request_id:
                order.request_id.action_done()
                order.sudo().notification_mail_send()
            if order.maintenance_type == 'pr':
                order.equipment_id.actual_last_utilization = order.actual_utilization
                order.equipment_id.actual_last_maintenance = order.date_start_execution
                order.equipment_id.last_measure_date = order.date_measure
            if order.maintenance_type == 'mp' and order.maintenance_plan_id:
                order.maintenance_plan_id.state = 'done'
                order.maintenance_plan_id.order_id = order.id
            order.delta_duration = order.actual_duration - order.order_duration
            order.delta_mat_cost = order.act_mat_cost - order.std_mat_cost
            order.delta_tool_cost = order.act_tool_cost - order.std_tool_cost
            order.delta_labour_cost = order.act_labour_cost - order.std_labour_cost
            cost_picking = 0.0
            for move in order.picking_id.move_lines:
                cost_picking += move.product_id.standard_price * move.quantity_done
            order.act_mat_cost_unplanned = cost_picking - order.act_mat_cost
        return True

    def notification_mail_send(self):
        mail_obj = self.env['mail.mail']
        for order in self:
            subject = 'Maintenance Notification: '+ str(order.request_id.name)
            mail_data = {
                        'subject': subject,
                        'body_html': 'the requested maintenance has been performed',
                        'email_from': order.create_uid.partner_id.email,
                        'email_to': order.request_id.requested_by.partner_id.email,
                        }
        mail_id = mail_obj.sudo().create(mail_data)
        mail_id.sudo().send()
        return True

    def _compute_picking_ids(self):
        for order in self:
            order.picking_ids = self.env['stock.picking'].search([('group_id', '=', order.procurement_group_id.id)])
            order.delivery_count = len(order.picking_ids)
        return True

    def action_view_delivery(self):
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action
    
    @api.depends('parts_lines','order_duration','tool_ids','n_resourse','maintenance_team_id')
    def _calculate_planned_costs(self):
        mat_cost = 0.0
        tool_cost = 0.0
        for order in self:
            for line in order.parts_lines:
                mat_cost += line.parts_id.standard_price * line.parts_qty
            order.std_mat_cost = mat_cost
            for tool in order.tool_ids:
                tool_cost += tool.tool_id.tool_cost_unit * order.order_duration
            order.std_tool_cost = tool_cost
            order.std_labour_cost = order.n_resourse * order.order_duration * order.maintenance_team_id.labour_cost_unit
        return True
        
    def _calculate_actual_costs(self):
        mat_cost1 = 0.0
        mat_cost2 = 0.0
        tool_cost = 0.0
        for order in self:
            if order.state == 'done':
                for move in order.parts_stock_moves:
                    mat_cost1 += move.product_id.standard_price * move.product_uom_qty
                for line in order.parts_lines:
                    if line.parts_id.type != 'product':
                        mat_cost2 += line.parts_id.standard_price * line.parts_qty
                order.act_mat_cost = mat_cost2 + mat_cost1
                for tool in order.tool_ids:
                    tool_cost += tool.tool_id.tool_cost_unit * order.actual_duration
                order.act_tool_cost = tool_cost
                order.act_labour_cost = order.n_resourse * order.actual_duration * order.maintenance_team_id.labour_cost_unit
        return True
    
    def _analytic_postings(self):
        for order in self:
            if order.maintenance_type in ('in','rf') and order.request_id and order.request_id.analytic_account_id:
                analytic_account_id = order.request_id.analytic_account_id
            else:
                analytic_account_id = order.maintenance_team_id.maintenance_cost_analytic_account_id
            # material cost analytic posting
            if order.act_mat_cost != 0.00:
                id_created= self.env['account.analytic.line'].create({
                    'name': order.name,
                    'account_id': analytic_account_id.id,
                    'ref': "material cost analytic posting",
                    'date': order.date_execution,
                    'amount': - order.act_mat_cost,
                    'company_id': order.company_id.id,
                    'maintenance_id': order.id,
                })
            # tool cost analytic posting
            if order.act_tool_cost != 0.00:
                id_created= self.env['account.analytic.line'].create({
                    'name': order.name,
                    'account_id': analytic_account_id.id,
                    'ref': "tool cost analytic posting",
                    'date': order.date_execution,
                    'amount': - order.act_tool_cost,
                    'company_id': order.company_id.id,
                    'maintenance_id': order.id,	
                })
            # labour cost analytic posting
            if order.act_labour_cost != 0.00:
                id_created= self.env['account.analytic.line'].create({
                    'name': order.name,
                    'account_id': analytic_account_id.id,
                    'ref': "labour cost analytic posting",
                    'date': order.date_execution,
                    'amount': - order.act_labour_cost,
                    'company_id': order.company_id.id,
                    'maintenance_id': order.id,
                })
            # counterpart cost analytic posting
            #if (order.act_labour_cost + order.act_mat_cost + order.act_tool_cost) != 0.00:
            #    id_created= self.env['account.analytic.line'].create({
            #        'name': order.name,
            #        'account_id': analytic_account_id.id,
            #        'ref': "counterpart cost analytic posting",
            #        'date': order.date_execution,
            #        'amount': order.act_labour_cost + order.act_mat_cost + order.act_tool_cost,
            #        'company_id': order.company_id.id,
            #        'maintenance_id': order.id,
            #    })
        return True
        
    def _compute_attached_docs_count(self):
        attachment = self.env['ir.attachment']
        for order in self:
            order.doc_count = attachment.search_count(['&',('res_model', '=', 'mro.order'), ('res_id', '=', order.id)])
    
    def attachment_tree_view(self):
        self.ensure_one()
        domain = ['&', ('res_model', '=', 'mro.order'), ('res_id', 'in', self.ids)]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

    def _compute_attached_docs_task_count(self):
        attachment = self.env['ir.attachment']
        for order in self:
            order.doc_count_task = attachment.search_count(['&',('res_model', '=', 'mro.task'), ('res_id', '=', order.task_id.id)])

    def task_attachment_tree_view(self):
        self.ensure_one()
        domain = ['&', ('res_model', '=', 'mro.task'), ('res_id', 'in', self.task_id.ids)]
        return {
            'name': _('Task Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

    def _compute_attached_docs_request_count(self):
        attachment = self.env['ir.attachment']
        for order in self:
            order.doc_count_req = attachment.search_count(['&',('res_model', '=', 'mro.request'), ('res_id', '=', order.request_id.id)])

    def request_attachment_tree_view(self):
        self.ensure_one()
        domain = ['&', ('res_model', '=', 'mro.request'), ('res_id', 'in', self.request_id.ids)]
        return {
            'name': _('Request Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

    def create_tool_utilization_records(self):
        for tool in self.tool_ids:
            record_id = self.env['mro.order.tool.utilization'].create({
                'tool_id':tool.tool_id.id,
                'maintenance_id': self.id,
            })

class MroOrderPartsLine(models.Model):
    _name = 'mro.order.parts.line'
    _description = 'Maintenance Planned Spare Parts'

    parts_id = fields.Many2one('product.product', 'Spare Parts', required=True, domain=[('maintenance_ok', '=', True)])
    parts_qty = fields.Float('Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    parts_uom = fields.Many2one('uom.uom', 'Unit of Measure', related='parts_id.uom_id')
    maintenance_id = fields.Many2one('mro.order', 'Maintenance Order')
    parts_type = fields.Selection(string='Product Type', related='parts_id.type', readonly=True)
    parts_categ_id = fields.Many2one('product.category', 'Product Category', related='parts_id.categ_id', readonly=True)


class MroOrderTools(models.Model):
    _name = 'mro.order.tool'
    _description = 'Maintenance Order Tools'

    tool_id = fields.Many2one('mro.tool', 'Tools', required=True)
    maintenance_id = fields.Many2one('mro.order', 'Maintenance Order')
    order_id = fields.Many2one('mro.order', 'Other Maintenance Order', readonly=True, related='tool_id.order_id')
    date_next_calibration = fields.Datetime('Next Calibration Date', readonly=True, related='tool_id.date_next_calibration', store=True)


    @api.constrains('tool_id')
    def check_tool_id(self):
        for record in self:
            tools = self.env['mro.order.tool'].search([('maintenance_id', '=', record.maintenance_id.id), ('tool_id', '=', record.tool_id.id)])
        if len(tools) > 1:
            raise UserError(_("Tool already entered"))


class MroOrderToolsUtilization(models.Model):
    _name = 'mro.order.tool.utilization'
    _description = 'Maintenance Order Tools Utilization Analysis'

    tool_id = fields.Many2one('mro.tool', 'Tools')
    maintenance_id = fields.Many2one('mro.order', 'Maintenance Order')
    maintenance_type = fields.Selection(string='Maintenance Type', related='maintenance_id.maintenance_type', store=True)
    equipment_id = fields.Many2one('mro.equipment', 'Equipment', related='maintenance_id.equipment_id', store=True)
    order_duration = fields.Float('Planned Duration', related='maintenance_id.order_duration', store=True)
    actual_duration = fields.Float('Actual Duration', related='maintenance_id.actual_duration', store=True)
    user_id = fields.Many2one('res.users', 'Responsible Technician', related='maintenance_id.user_id', store=True)
    date_execution = fields.Datetime('Execution Date', related='maintenance_id.date_execution', store=True)
    date_start_execution = fields.Datetime('Execution Start Date', related='maintenance_id.date_start_execution', store=True)
    maintenance_team_id = fields.Many2one('mro.maintenance.team', 'Maintenance Team', related='maintenance_id.maintenance_team_id', store=True)
    
        
class DurationRecord(models.TransientModel):
    _name = 'mro.order.duration.record'
    _description = "Wizard Actual Duration Recording"

    order_id = fields.Many2one('mro.order', "Maintenance Order", readonly=True)
    actual_duration = fields.Float('Actual Duration', required=True)
    
    @api.model
    def default_get(self, fields):
        default = super().default_get(fields)
        active_id = self.env.context.get('active_id', False)
        if active_id:
            default['order_id'] = active_id
        return default
    
    def do_record(self):
        self.ensure_one()
        self.order_id.actual_duration = self.actual_duration
        self.order_id.action_done_after()
        self.order_id.create_tool_utilization_records()
        return True
        