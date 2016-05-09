import frappe

def get_orders():
	""" 
		get newly created orders from magento
		fetch the orders based on updated_at field in magento
	"""
	try:
		max_date = frappe.db.sql("select max(modified_date) as max_date from `tabSales Order`")
		max_date = "1991-09-07 05:43:13" if not max_date else max_date[0].get("max_date")
	except Exception, e:
		raise e
	finally:
		update_execution_date('Product')
