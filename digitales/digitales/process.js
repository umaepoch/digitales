//Make Invoice button on Process form
frappe.ui.form.on("Process", "refresh", function(frm) {
	if(frm.doc.docstatus === 1 && frm.doc.sales_invoice_status == "Not Done") {
		cur_frm.add_custom_button(__('Make Invoice'),
			function() {
				frappe.model.open_mapped_doc({
					method: "digitales.digitales.process.make_sales_invoice",
					frm: cur_frm
				})
		}, frappe.boot.doctype_icons["Sales Invoice"])
	}
})