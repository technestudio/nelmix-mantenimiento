# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"


    maintenance_id = fields.Many2one("mro.order", string="Maintenance Order", copy=False, index=True)
