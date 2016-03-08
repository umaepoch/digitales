cur_frm.cscript['Stop Purchase Order'] = function(){
	if(is_items_to_stop(cur_frm.doc))
		render_dialog(cur_frm.doc)
	else
		msgprint("No Item to Stop")
}

is_items_to_stop = function(doc) {
	is_item_available = false;
	$.each(doc["po_details"], function(i, row) {
		if(row.stop_status != "Yes" && (row.qty - row.received_qty) != 0){
			is_item_available = true
			return false
		}
	})

	return is_item_available
}

render_dialog = function(doc) {
	var me=this;
	dialog = new frappe.ui.Dialog({
			title: "Select Item to Stop",
			fields: [
					{fieldtype: "HTML" , fieldname: "items" , label: "Item To Stop"},
				],
			primary_action_label: "Stop",
			primary_action: get_and_stop_po_items
		});
	fd = this.dialog.fields_dict;

	dialog.show();

	html = frappe.render(frappe.templates.po_stop_items, {
			"items": doc.po_details,
		}, is_path = true);
	$(html).appendTo(fd.items.wrapper)
	
	bind_events();
}

bind_events = function(){
	$(fd.items.wrapper).find(".all").click(function(){
		check_all()
	})
}

check_all = function(){
	var checked = $(fd.items.wrapper).find(".all").prop("checked");
	if(checked)
		$(fd.items.wrapper).find(".select").prop("checked", true);
	else
		$(fd.items.wrapper).find(".select").prop("checked", false);
}

get_and_stop_po_items =function(){
	items_to_stop = {}
	$.each($(fd.items.wrapper).find(".select:checked").parent().parent(), function(idx, item){
		items_to_stop[$(item).children("td#item_code").text()] = {
			"qty":$(item).children("td#qty").text(),
			"warehouse": $(item).children("td#warehouse").text()
		}
	})
	console.log([items_to_stop.length, items_to_stop])
	if(items_to_stop.length){
		frappe.call({
			freeze: true,
			method:"digitales.digitales.po_stop.stop_po_items",
			args: { 
				po_name: cur_frm.doc.name,
				items: items_to_stop
			},
			callback: function(r) {
				cur_frm.reload_doc();
				dialog.hide();
			}
		})
	}
	else
		msgprint("Select Item to Stop")
}
