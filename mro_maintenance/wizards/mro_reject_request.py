# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class MroRequestReject(models.TransientModel):
    _name = 'mro.request.reject'
    _description = 'Reject Request'

    reject_reason = fields.Text(_('Reject Reason'), required=True)

    def reject_request(self):
        request_id = self.env.context.get('active_id', False)
        if request_id:
            request = self.env['mro.request'].browse(request_id)
            request.write({'reject_reason': self.reject_reason})
            request.action_reject()
        return True