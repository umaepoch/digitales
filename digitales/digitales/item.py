import frappe

@frappe.whitelist()
def get_item_release_date(item_code):
	return str(frappe.db.get_value("Item", item_code, "product_release_date")) or ""