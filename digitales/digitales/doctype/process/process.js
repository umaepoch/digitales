// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('get_sales_order','customer','customer_id');
cur_frm.add_fetch('get_sales_order','customer_name','customer_name');

cur_frm.add_fetch('get_sales_order','name','order_no');
cur_frm.add_fetch('get_sales_order','transaction_date','order_date');

cur_frm.add_fetch('item_code','item_name','item_name');
cur_frm.add_fetch('item_code','description','description');

cur_frm.add_fetch('process','charge','charge');
cur_frm.add_fetch('process','barcode','barcode');

cur_frm.cscript.process_type = function(doc, cdt, cdn) {
	cur_frm.cscript.toggle_related_fields(doc);
}
	
cur_frm.get_field("process_type").get_query=function(doc,cdt,cdn){
	return {filters: { is_service_item: "Yes"}}
}

cur_frm.cscript.qty = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if (d.qty && d.charge){
		d.amount=d.qty*d.charge;
		cur_frm.set_value('amount',d.amount)
	}
	refresh_field('amount');
}

cur_frm.cscript.barcode = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	get_server_fields('get_service_details', d.barcode ,'', doc, cdt, cdn, 1,function(r,rt){refresh_field('shelf_ready_service_details')});
}

cur_frm.fields_dict.shelf_ready_service_details.grid.get_field("process").get_query = function(doc){
    if(doc.process_type){
		return "select name from `tabShelf Ready Service` where process_type='"+doc.process_type+"'"
    }
    else
       	msgprint("First select process type")
}

cur_frm.cscript.toggle_related_fields = function(doc) {
	disable_item_barcode= inList(["Processing", "Graphics"], doc.process_type);
	cur_frm.fields_dict["shelf_ready_service_details"].grid.set_column_disp("item_barcode", !disable_item_barcode);
	cur_frm.fields_dict["shelf_ready_service_details"].grid.set_column_disp("file_name", !disable_item_barcode);
	cur_frm.fields_dict["shelf_ready_service_details"].grid.set_column_disp("file_attachment", !disable_item_barcode);
}


// cur_frm.cscript.shelf_ready_service_details_add=function(doc,cdt,cdn){
// 	alert("Hi")
// }