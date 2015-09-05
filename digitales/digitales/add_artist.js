// documents=['Sales Order Item','Sales Invoice Item', 'Delivery Note Item', 'Packing Slip Item']

frappe.ui.form.on('Sales Order Item','item_code', function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	get_artist_field(d)
})

frappe.ui.form.on('Sales Invoice Item','item_code', function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	get_artist_field(d)
})

frappe.ui.form.on('Delivery Note Item','item_code', function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	get_artist_field(d)
})

frappe.ui.form.on('Packing Slip Item','item_code', function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	get_artist_field(d)
})

function get_artist_field(d){
	return frappe.call({
		method: "digitales.digitales.Api_methods.get_artist",
		args: {'item_code': d.item_code},
		callback: function(r) {
			d.artist = r.message
			refresh_field('artist');
		}
	});
}