import frappe
from frappe import _, msgprint, throw
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
	"""Fetching Details from Process to Sales Invoice"""
	
	sales_order = frappe.db.get_value("Process", source_name, "get_sales_order")
	def set_missing_values(source, target):
		target.customer = source.customer_id
		target.customer_name = source.customer_name
		target.run_method("set_missing_values");

	def update_values(source, target, source_parent):
		target.sales_order = source_parent.get_sales_order
		target.delivery_note = source_parent.get_delivery_note
		target.cost_center = frappe.db.get_value("Item", source.process, "selling_cost_center")

	doclist = get_mapped_doc("Process", source_name, 	{
		"Process": {
			"doctype": "Sales Invoice",
			"validation": {
				"docstatus": ["=", 1],
				"customer_id": "customer"
			}
		},
		"Shelf Ready Service Details": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"process": "item_code",
				"qty": "qty",
				"item_barcode": "barcode",
				"file_name": "marcfile_name"
			},
			"postprocess": update_values,
		}, 
	}, target_doc, set_missing_values)

	return doclist


def check_billed_processes(doc, method):
	"""check existing Sales Invoice against Processes"""
	processes_billed = []
	for item in doc.entries:
		if frappe.db.get_value("Process", item.process_id, "sales_invoice_status") == "Done":
			processes_billed.append(item.item_code)
	if processes_billed:
		frappe.throw("Sales Invoice for Process:  {0} is already Submitted.".format(", ".join(processes_billed)))
	
def get_sales_order(doctype, txt, searchfield, start, page_len, filters):
	query = """
				select distinct s.parent from `tabSales Order Item` s inner join `tabSales Order` so 
				on s.parent=so.name where so.docstatus=1 and s.assigned_qty>0 and s.stop_status = "No" and s.parent like "%%%s%%" limit %s, %s
			"""%(txt, start, page_len)
	return frappe.db.sql(query, as_list = 1)