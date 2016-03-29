
frappe.ui.form.on("Purchase Order Item", "item_code", function(doc, cdt, cdn){
	// get the item release date

	doc = locals[cdt][cdn];
	return frappe.call({
		method: "digitales.digitales.item.get_item_release_date",
		args: { item_code: doc.item_code },
		callback: function(r){
			if(r.message)
				doc.product_release_date = r.message
			cur_frm.refresh_fields();
		}
	});
})