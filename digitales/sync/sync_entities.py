from digitales.sync import (get_products, get_customers, get_orders)
from frappe.utils import now, get_datetime

max_date = "1991-09-07 05:43:13"
header = {'Content-Type': 'application/json', 'Accept': 'application/json'}

def sync_entity_from_magento():
	""" check and decide which entity to sync """
	sync_methods = {
		"Product": get_products,
		"Customer": get_customers,
		"Order": get_orders
	}

	conf = frappe.get_doc("API Configuration Page", "API Configuration Page")
	if now() > get_datetime(conf.date):
		sync_methods[conf.api_type]()