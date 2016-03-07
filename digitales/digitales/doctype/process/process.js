// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('get_sales_order','customer','customer_id');
cur_frm.add_fetch('get_sales_order','customer_name','customer_name');

cur_frm.add_fetch('get_sales_order','name','order_no');
cur_frm.add_fetch('get_sales_order','transaction_date','order_date');

cur_frm.add_fetch('get_delivery_note','customer','customer_id');
cur_frm.add_fetch('get_delivery_note','customer_name','customer_name');

cur_frm.add_fetch('get_delivery_note','name','delivery_note_no');
cur_frm.add_fetch('get_delivery_note','posting_date','delivery_note_date');


// cur_frm.add_fetch('item_code','item_name','item_name');
// cur_frm.add_fetch('item_code','description','description');

// cur_frm.add_fetch('process','charge','charge');
cur_frm.add_fetch('process','barcode','item_barcode');
cur_frm.cscript.item_barcode = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(d.item_barcode){
		return frappe.call({
			method: "digitales.digitales.doctype.process.process.get_process_from_barcode",
			args: {'barcode': d.item_barcode},
			callback: function(r) {
				d.process = r.message
				// cur_frm.set_value()
				refresh_field('process', d.name, 'shelf_ready_service_details');
			}
		});	
	}
}

cur_frm.cscript.process_type = function(doc, cdt, cdn) {
	cur_frm.cscript.toggle_related_fields(doc);
}
	
cur_frm.get_field("get_sales_order").get_query=function(doc,cdt,cdn){
	return "select distinct s.parent from `tabSales Order Item` s inner join `tabSales Order` so on s.parent=so.name where so.docstatus=1 and s.assigned_qty>0"
}

// cur_frm.cscript.qty = function(doc, cdt, cdn){
// 	var d = locals[cdt][cdn];
// 	if (d.qty && d.charge){
// 		d.amount=d.qty*d.charge;
// 		cur_frm.set_value('amount',d.amount)
// 	}
// 	refresh_field('amount');
// }

cur_frm.cscript.barcode = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	get_server_fields('get_service_details', d.barcode ,'', doc, cdt, cdn, 1,function(r,rt){refresh_field('shelf_ready_service_details')});
}

cur_frm.fields_dict.shelf_ready_service_details.grid.get_field("process").get_query = function(doc){
    return {
    	query : "digitales.digitales.doctype.process.process.get_shelfreadyservices_customer",
    	filters : {
    		'customer_name' : doc.customer_id
    	}
    }
}

cur_frm.cscript.toggle_related_fields = function(doc) {
	disable_item_barcode= inList(["Processing", "Graphics"], doc.process_type);
	cur_frm.fields_dict["shelf_ready_service_details"].grid.set_column_disp("item_barcode", !disable_item_barcode);
	cur_frm.fields_dict["shelf_ready_service_details"].grid.set_column_disp("file_name", !disable_item_barcode);
	cur_frm.fields_dict["shelf_ready_service_details"].grid.set_column_disp("file_attachment", !disable_item_barcode);
}


// cur_frm.fields_dict['shelf_ready_service_details'].grid.get_field('process').get_query = function(doc, cdt, cdn) {

//    	return {filters: { is_service_item: "Yes"}}

// }


cur_frm.cscript.refresh = function(doc) {
	hide_field(['order_no', 'order_date', 'delivery_note_no', 'delivery_note_date'])
	cur_frm.cscript.toggele_fields_process(doc)	
}

cur_frm.cscript.get_sales_order = function(doc) {
	cur_frm.cscript.toggele_fields_process(doc)	
}

cur_frm.cscript.get_delivery_note = function(doc) {
	cur_frm.cscript.toggele_fields_process(doc)	
}

cur_frm.cscript.toggele_fields_process = function(doc) {
	if(doc.get_sales_order=="" && doc.get_delivery_note==""){
		cur_frm.set_df_property("get_delivery_note", "read_only", 0);
		cur_frm.set_df_property("get_sales_order", "read_only", 0);
	}

	if(doc.get_sales_order){
		unhide_field(['order_no', 'order_date'])
		hide_field(['delivery_note_date', 'delivery_note_no'])
		cur_frm.set_df_property("get_delivery_note", "read_only", 1);
	}
	if(doc.get_delivery_note){
		hide_field(['order_no', 'order_date'])
		unhide_field(['delivery_note_date', 'delivery_note_no'])
		cur_frm.set_df_property("get_sales_order", "read_only", 1);
	}	
}

cur_frm.fields_dict['get_delivery_note'].get_query = function(doc, dt, dn) {
	return {query: "digitales.digitales.custom_methods.delivery_note" }
}
