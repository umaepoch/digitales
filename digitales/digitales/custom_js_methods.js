erpnext.selling.CustomSalesOrder = erpnext.selling.SalesOrderController.extend({
  init:function(){
    var a;
  }


 
});

// cur_frm.cscript['Stop Sales Order'] = function(doc) {
// 	var doc = cur_frm.doc;
// 	var check = confirm(__("Are you sure you want to STOP ") + doc.name);

// 	if (check) {

// 		return $c('runserverobj', {
// 			'method':'stop_sales_order',
// 			'docs': doc
// 			}, function(r,rt) {
// 				frappe.call({
// 					method: "digitales.digitales.Api_methods.assign_stopQty_toOther",
// 					args: {'doc': doc.name},
// 					callback: function(r) {
// 						refresh_field('sales_order_details')
// 						cur_frm.reload_doc();
// 					}	
// 				})
// 				cur_frm.refresh();
// 		});
// 	}	
// }




// //added by pitambar

frappe.require("assets/css/tab_scroll.css");
cur_frm.cscript['Stop Sales Order'] = function(doc) {
	var doc = cur_frm.doc;
	var count=items_to_stop(doc);	
	if(count=="true"){
		create_dialog(doc);
	}
	else{
		alert("No Item to STOP");
	}
}

function create_dialog(doc){
	var dialog = new frappe.ui.Dialog({
	title:__('Select Item To Stop'),
	fields: [
	{fieldtype:'HTML', fieldname:'styles_name', label:__('Styles'), reqd:false,
	description: __("")},
	{fieldtype:'Button', fieldname:'status_update', label:__('Action') }
	]
	})
	var fd = dialog.fields_dict;
	
	this.table = $("<div id='container'><table class='table', id='tb1'>\
	                      <thead><tr>\
	                      	<th><b>Select</b></th>\
 			 				<th><b>Item Code</b></th>\
 			 				<th><b>Ordered Qty</b></th>\
 			 				<th><b>Assigned Qty</b></th>\
	                      </tr></thead>\
	                      <tbody></tbody>\
	                     </table></div>").appendTo($(fd.styles_name.wrapper))

	for(i=0;i < doc.sales_order_details.length;i++){
		if(doc.sales_order_details[i].stop_status!="Yes")
		{
			$("<tr>\
				<td><input type='checkbox' id='select'></td>\
				<td>"+doc.sales_order_details[i].item_code+"</td>\
				<td style='text-align:center'>"+doc.sales_order_details[i].qty+"</td>\
				<td style='text-align:center'>"+doc.sales_order_details[i].assigned_qty+"</td>\
			</tr>").appendTo($("#tb1 tbody"))
		}
	}
	dialog.show();
	var item_dict={};

	$(fd.status_update.input).click(function() {
		var check = confirm(__("Are you sure you want to STOP selected items"));
    	$('#tb1 tr').filter(':has(:checkbox:checked)').each(function() {
          var $tds = $(this).find('td'),
            item_c = $tds.eq(1).text(),
            item_q = $tds.eq(2).text();
            item_dict[item_c]=item_q;

    });
    	if (check) {
			dialog.hide()
			frappe.call({
					method: "digitales.digitales.Api_methods.assign_stopQty_toOther",
					args: {'doc': doc.name,
							'item_list':item_dict
						},
					callback: function(r) {
						refresh_field('sales_order_details')
						cur_frm.reload_doc();
					}	
			})
		}		
	})
}

function items_to_stop(doc){
	var count;
	for(i=0;i < doc.sales_order_details.length;i++){
		if(doc.sales_order_details[i].stop_status!="Yes")
		{
			count="true";
			break;
		}
	}	
	return count;
}
