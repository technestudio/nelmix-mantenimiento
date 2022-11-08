# -*- coding: utf-8 -*-

from odoo import fields, models, _


class stock_location(models.Model):
    _inherit = "stock.location"


    usage = fields.Selection(selection_add=[('equi', 'Spare Parts Consumption')], ondelete={'equi': 'set default'})