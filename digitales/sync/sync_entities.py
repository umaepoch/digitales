import frappe
from frappe.utils import now, get_datetime, now_datetime
from .utils import (date_minus_sec, get_entity_and_page_count, get_entities_from_magento,
	log_sync_status, update_execution_date, create_scheduler_exception)
from digitales.sync import (create_or_update_item, create_or_update_customer, create_or_update_sales_order)
from digitales.sync.sync_missing_entities import (get_missing_items, get_missing_customers, get_missing_orders,
	get_sync_error_entities_count)

entity_map = { "Product": "Item", "Customer": "Customer", "Order": "Sales Order" }
next_sync_type = { "Product": "Customer", "Customer": "Order", "Order": "Product" }
missing_entity_methods = {
	"Product": get_missing_items,
	"Customer": get_missing_customers,
	"Order": get_missing_orders
}

def sync_entity_from_magento():
	""" check and decide which entity to sync """
	conf = frappe.get_doc("API Configuration Page", "API Configuration Page")
	if get_datetime(now()) > get_datetime(conf.date):
		get_and_sync_entities(api_type=conf.api_type)
	elif conf.api_type != "Product":
		prev_type = { "Order": "Customer", "Customer": "Product" }
		get_and_sync_entities(api_type=prev_type[conf.api_type], update_config=False)

	start = now_datetime()
	total_entities_to_resync = get_sync_error_entities_count(entity_map[conf.api_type])
	if not total_entities_to_resync:
		return

	sync_stat = missing_entity_methods[conf.api_type]()
	end = now_datetime()
	log_sync_status(
		entity_map[conf.api_type], count_response=total_entities_to_resync, entities_to_sync=total_entities_to_resync,
		pages_to_sync=1, entities_received=0, synced_entities=sync_stat, start=start, end=end,
		is_resync=True
	)

def get_and_sync_entities(api_type="Product", update_config=True):
	""" get and sync the Item, Customer, Sales Order """
	urls = []
	count = {}
	sync_stat = {}
	page_count = 0
	magento_response = []
	total_entities_to_sync = 0
	total_entities_received = 0
	start = end = now_datetime()
	max_date = "1991-09-07 05:43:13"
	entity_url = { "Item": "products", "Customer": "customers", "Sales Order": "orders" }
	sync_methods = {
		"Item": create_or_update_item,
		"Customer": create_or_update_customer,
		"Sales Order": create_or_update_sales_order
	}
	entity_type = entity_map[api_type]

	try:
		query = "select max(modified_date) as max_date from `tab{}`".format(entity_type)
		max_date = frappe.db.sql(query, as_dict=True)
		max_date = "1991-09-07 05:43:13" if not all([max_date, max_date[0].get("max_date")]) else max_date[0].get("max_date")

		count = get_entity_and_page_count(date_minus_sec(max_date), entity_type=entity_type)
		if not count:
			return

		total_entities_to_sync = count.get("entity_count")
		if (count.get("page_count") == 0 and count.get("entity_count") > 0):
			page_count = count.get("page_count") + 2
		else:
			page_count = count.get("page_count") + 1

		#m2_changes_start
		if api_type == "Customer":
			m2_url ="https://digitales.com.au/rest/V1/{}/search?searchCriteria[filter_groups][0][filters][0][field]=updated_at".format(entity_url[entity_type])
		else:
			m2_url ="https://digitales.com.au/rest/V1/{}/?searchCriteria[filter_groups][0][filters][0][field]=updated_at".format(entity_url[entity_type])

		m2_url += "&searchCriteria[filter_groups][0][filters][0][value]={}&page={}&searchCriteria[filter_groups][0][filters][0][condition_type]=gteq&limit=100&order=updated_at&dir=asc"
		#m2_changes_end
		for idx in xrange(1, page_count):
			response = get_entities_from_magento(m2_url.format(date_minus_sec(max_date), idx), entity_type=entity_type)
			if not response:
				continue

			magento_response.append(response)
			total_entities_received += response.get("total_count") #m2_changes
			urls.append(m2_url.format(date_minus_sec(max_date), idx))

			if entity_type == "Customer": #m2_changes
				sync_stat.update({ entity.get("id") : { "modified_date": entity.get("updated_at") } for  entity in response.get("items") })
			elif entity_type == "Sales Order": #m2_changes3
				sync_stat.update({ entity.get("entity_id") : { "modified_date": entity.get("updated_at") } for  entity in response.get("items") })
			else:
				sync_stat.update({ entity.get("sku"): { "modified_date": entity.get("updated_at") } for  entity in response.get("items") }) #m2_changes

			for entity in response.get("items"):
				status = sync_methods[entity_type](entity)
				if status: sync_stat.update(status)
				frappe.db.commit()
	except Exception, e:
		create_scheduler_exception(e , sync_methods[entity_type].func_name, frappe.get_traceback())
	finally:
		end = now_datetime()
		log_sync_status(
			entity_type, count_response=count, entities_to_sync=total_entities_to_sync,
			pages_to_sync=page_count, entities_received=total_entities_received, synced_entities=sync_stat,
			start=start, end=end, max_date=max_date, urls=urls, response=magento_response
		)
		if update_config: update_execution_date(next_sync_type[api_type])

