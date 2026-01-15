# -*- coding: utf-8 -*-
"""
Extend res.users to set Russian as default language

Author: AI Agent
Created: 2026-01-15
Purpose: Set lang='ru_RU' by default for all new users
"""

from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _get_default_lang(self):
        """Return Russian as default language"""
        return 'ru_RU'

    @api.model_create_multi
    def create(self, vals_list):
        """Set Russian language for new users if not specified"""
        for vals in vals_list:
            if 'lang' not in vals or not vals.get('lang'):
                vals['lang'] = 'ru_RU'
        return super().create(vals_list)
