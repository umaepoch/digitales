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

	key = items_key_mapper[cur_frm.doctype];
	if(key){
		frappe.dom.freeze();
		window.setTimeout(function(){
			items = cur_frm.doc[key];
		
			items.map(function(item, idx){
				var _item = {}
				_item.name = item.name;
				_item.item_name = item.item_name
				_item.idx = idx;

				item_names.push(_item);
			});

			item_names.sort(function(a, b) {
				return (a.item_name > b.item_name) ? 1 : ((b.item_name > a.item_name) ? -1 : 0);
			});

			$.each(item_names, function(idx, item){
				cur_frm.doc[key][item.idx].idx = idx+1;
			})

			cur_frm.doc.__unsaved=true
			cur_frm.refresh();
			frappe.dom.unfreeze();
		}, 10);
	}
}