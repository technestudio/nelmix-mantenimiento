# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = "product.template"


    maintenance_ok = fields.Boolean(_('Spare Part'), default=False, help="Specify whether the product can be selected in a maintenance parts list.")
