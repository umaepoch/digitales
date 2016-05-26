frappe.ui.form.on("Sync Log", "refresh", function(doc){
	html = frappe.render(frappe.templates.sync_log_status, {
			"entities": JSON.parse(cur_frm.doc.synced_entities),
		}, is_path = true);
	$(cur_frm.fields_dict.sync_stat.$wrapper).empty()
	$(cur_frm.fields_dict.sync_stat.$wrapper).append(html)
})