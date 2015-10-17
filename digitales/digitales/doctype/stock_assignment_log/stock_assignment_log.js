cur_frm.cscript.refresh = function(doc){
	cur_frm.toggle_enable("assign_qty", false);
	if(user=='maya@digitales.com.au' || user=='Administrator'){
		cur_frm.toggle_enable("assign_qty", true);
	}
}

cur_frm.add_fetch("sales_order", "customer_name", "customer_name")

cur_frm.cscript.item_code = function(doc, cdt, cdn){
	get_server_fields('get_item_details', '', '', doc, cdt, cdn, 1, function(){
		refresh_field(['Media', 'item_name', 'ordered_qty'])
	})
}