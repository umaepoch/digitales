erpnext.selling.CustomSalesOrder = erpnext.selling.SalesOrderController.extend({
  init:function(){
    var a;
  }
});

frappe.require("assets/css/tab_scroll.css");
cur_frm.cscript['Stop Sales Order'] = function(doc) {
	var doc = cur_frm.doc;
	var count=items_to_stop(doc);
	if(count=="true"){
		create_dialog(doc);
	}
	else{
		msgprint("No Item to STOP");
	}
}

function create_dialog(doc){
	this.dialog = new frappe.ui.Dialog({
		title:__('Select Item To Stop'),
		fields: [
			{fieldtype:'HTML', fieldname:'styles_name', label:__('Styles'), reqd:false,
			description: __("")},
			{fieldtype:'Button', fieldname:'status_update', label:__('Action') }
		]
	})
	this.fd = dialog.fields_dict;

	this.table = $("<div id='container'><table class='table table-bordered table-hover', id='tb1'>\
	                      <thead><tr>\
	                      	<th width='50px'><b><input type='checkbox' id='all'></b></th>\
 			 				<th><b>Item Code</b></th>\
 			 				<th><b>Item Name</b></th>\
 			 				<th width='110px'><b>Ordered Qty</b></th>\
 			 				<th width='110px'><b>Assigned Qty</b></th>\
	                      </tr></thead>\
	                      <tbody></tbody>\
	                     </table></div>").appendTo($(this.fd.styles_name.wrapper))

	for(i=0;i < doc.sales_order_details.length;i++){
		if(doc.sales_order_details[i].stop_status!="Yes" && (flt(doc.per_delivered, 2) < 100 || flt(doc.per_billed) < 100))
		{
			$("<tr>\
				<td><input type='checkbox' class='select'></td>\
				<td>"+doc.sales_order_details[i].item_code+"</td>\
				<td>"+doc.sales_order_details[i].item_name+"</td>\
				<td style='text-align:center'>"+doc.sales_order_details[i].qty+"</td>\
				<td style='text-align:center'>"+doc.sales_order_details[i].assigned_qty+"</td>\
			</tr>").appendTo($("#tb1 tbody"))
		}
	}
	this.dialog.show();

	checkall();
	var outer_this=this;
	$(this.fd.status_update.input).click(function() {
		this.item_dict={};
		var inner_me=this;
		inner_me.check = false;
		frappe.confirm(__("Are you sure you want to STOP selected items"), function(){
			outer_this.dialog.hide()
			frappe.call({
					method: "digitales.digitales.Api_methods.assign_stopQty_toOther",
					args: {'doc': doc.name,
							'item_list':inner_me.item_dict
						},
					callback: function(r) {
						refresh_field('sales_order_details')
						cur_frm.reload_doc();
					}
			})
		}, function(){});

    	$(outer_this.fd.styles_name.wrapper).find('#tb1 tbody tr').filter(':has(:checkbox:checked)').each(function() {
          var $tds = $(this).find('td');
            item_c = $tds.eq(1).text();
            item_q = $tds.eq(3).text();
            inner_me.item_dict[item_c]=item_q;
   		});
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


function checkall(){
	var me=this;
	$(this.fd.styles_name.wrapper).find('#all').click(function () {
	var checkAll = $(me.fd.styles_name.wrapper).find('#all').prop('checked');
	    if (checkAll) {
	       $(me.fd.styles_name.wrapper).find(".select").prop("checked", true);
	    } else {
	        $(me.fd.styles_name.wrapper).find(".select").prop("checked", false);
	    }
	});
}
