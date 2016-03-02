frappe.ui.form.on("Delivery Note", "refresh", function(frm){
	if(frm.doc.docstatus == 0)
		cur_frm.add_custom_button(__('Sort Items'), sort_items, "icon-sort-by-alphabet", "btn-default");
});

items_key_mapper = {
	"Delivery Note": "delivery_note_details",
	"Sales Order": "sales_order_details"
}

sort_items = function(){
	var item_names = [];
	var item_idx = {};

	key = items_key_mapper[cur_frm.doctype];
	if(key){
		frappe.dom.freeze();
		window.setTimeout(function(){
			items = cur_frm.doc[key];
		
			items.map(function(item, idx){
				item_names.push(item.item_name);
				item_idx[item.item_name] = idx;
			});

			item_names.sort()
			$.each(item_names, function(idx, item_name){
				index = item_idx[item_name];
				cur_frm.doc[key][index].idx = idx+1;
			})

			cur_frm.doc.__unsaved=true
			cur_frm.refresh();
			frappe.dom.unfreeze();
		}, 10);
	}
}