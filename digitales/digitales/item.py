import frappe

@frappe.whitelist()
def get_item_release_date(item_code):
	release_date = frappe.db.get_value("Item", item_code, "product_release_date")
	if release_date:
		return str(release_date)
	else:
		return False