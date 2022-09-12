odoo.define('code137_hide_action.HideAction', function (require) {
    "use strict";

    const BasicModel = require('web.BasicModel');
    const FormController = require('web.FormController');
    const ListController = require('web.ListController');

    BasicModel.include({
        _load: function() {
            var self = this;
            var defs = []
            defs.push(this._super(...arguments));
            defs.push(this.getSession().user_has_group('code137_hide_action.group_hide_action_button').then(
                result => self.hide_action_button = result
            ));
            return $.when(...defs);
        }
    })

    FormController.include({
        _getActionMenuItems: function (state) {
            let values = this._super.apply(this, arguments);
            if(values && this.model.hide_action_button) {
                values.items.action = [];
                values.items.other = [];
            }
            return values;
        }
    });

    ListController.include({
        _getActionMenuItems: function (state) {
            let values = this._super.apply(this, arguments);
            if (!this.hasActionMenus || !this.selectedRecords.length) {
                return values;
            }
            if(this.model.hide_action_button) {
                values.items.action = [];
                values.items.other = [];
            }
            return values;
        }
    });

});
