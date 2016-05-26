frappe.listview_settings['Sync Error Log'] = {
	onload: function(me) {
		frappe.route_options = {
			"is_synced": ["!=", "Yes"],
		};
	},
	// add_fields: ["reference_type", "reference_name"],
}