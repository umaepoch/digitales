erpnext.selling.CustomSalesOrder = erpnext.selling.SalesOrderController.extend({
  init:function(){
    var a;
  }


 
});

cur_frm.cscript['Stop Sales Order'] = function(doc) {
	var doc = cur_frm.doc;

	var check = confirm(__("Are you sure you want to STOP ") + doc.name);

	if (check) {

		return $c('runserverobj', {
			'method':'stop_sales_order',
			'docs': doc
			}, function(r,rt) {
				frappe.call({
					method: "digitales.digitales.Api_methods.assign_stopQty_toOther",
					args: {'doc': doc.name},
					callback: function(r) {
						refresh_field('sales_order_details')
						cur_frm.reload_doc();
					}	
				})
				cur_frm.refresh();
		});
	}	
}