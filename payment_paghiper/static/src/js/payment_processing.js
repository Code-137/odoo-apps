odoo.define('payment_paghiper.processing', function (require) {
    'use strict';
    
    var publicWidget = require('web.public.widget');
    
    var PaymentProcessing = publicWidget.registry.PaymentProcessing;
    
    return PaymentProcessing.include({
        processPolledData: function(transactions) {
            if (transactions.length == 1 && ['paghiper'].indexOf(transactions[0].acquirer_provider) >= 0) {
                window.location = transactions[0].return_url;
                return;
            }
            return this._super.apply(this, arguments);
        }

    });

});