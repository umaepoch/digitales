import json
import frappe
import requests
from requests_oauthlib import OAuth1 as OAuth
from digitales.digitales.Api_methods import (GetOauthDetails, create_scheduler_exception,
		log_sync_error, create_item)

def get_missing_items(item=None, mannual_sync=False):
	""" Get the missing items from magento """
	items = get_entity_ids_to_sync(entity_type="Item") if not all(item, mannual_sync) else [item]
	if not items:
		return

	url = "http://digitales.com.au/api/rest/products?filter[1][attribute]=sku&filter[1][eq]=%s"

	for item in items:
		response = get_entity_from_magento(url%(item), entity_type="Item", entity_id=item)

		idx = response.keys()[0]
		create_item(idx, response)

	update_sync_status("Item", items)

def get_missing_customers(customer=None, mannual_sync=False):
	""" Get the missing customer from magento """
	customers = get_entity_ids_to_sync(entity_type="Customer") if not all(customer, mannual_sync) else [customer]

def get_missing_orders(order=None, mannual_sync=False):
	""" Get the missing orders from magento """
	orders = get_entity_ids_to_sync(entity_type="Sales Order") if not all(order, mannual_sync) else [order]

def get_entity_ids_to_sync(entity_type=None):
	""" get the list of entity ids from `Sync Error Log` to re-sync """
	entities = []
	if not entity_type:
		frappe.errprint("Select the DocType to sync")

	filters = {
		"sync_doctype": entity_type,
		"is_synced": "No",
		"sync_attempts": ("<", 4)
	}
	fields = "sync_docname" if entity_type != "Sales Order" else ["sync_docname", "missing_items", "missing_customer"]		
	results = frappe.db.get_values("Sync Error Log", filters, fields, as_dict=True)

	if entity_type == "Sales Order":
		for order in results:
			entity_id = order.get("sync_docname")
			items = []
			customer = []

			if order.get("missing_items"):
				missing_items = [item for item in json.dumps(order.get("missing_items")) or []]
				if missing_items: items = check_if_entity_already_synced("Item", missing_items)
			
			if not items and order.get("missing_customer"):
				customer = check_if_entity_already_synced("Customer", [order.get("missing_customer")])

			if not customer:
				entities.append(entity_id)
	else:
		entities = list(set([result.get("sync_docname") for result in results]))
		if entities: entities = check_if_entity_already_synced(entity_type, entities)

	return entities

def update_sync_status(entity_type, entities):
	""" update the sync error log status to Yes if entity is synced """
	if not entities:
		return

	# get the list of synced entities from entities and update the status
	check_if_entity_already_synced(entity_type, entities)

def check_if_entity_already_synced(entity_type, entities):
	""" check if Items or Customer is already synced """
	if not entities:
		return []

	query = """ select name from `tab{table}` where name in ({names}) """.format(
				table=entity_type,
				names=",".join(["'%s'"%entity for entity in entities])
			)

	results = frappe.db.sql(query, as_dict=True)
	
	if not results:
		return entities
	
	synced_entities = list(set([result.get("name") for result in results]))
	
	if synced_entities:
		""" Update the Sync Status """
		query = """ update `tabSync Error Log` set is_synced='Yes' where sync_docname in ({names})""".format(
					table=entity_type,
					names=",".join(["'%s'"%entity for entity in synced_entities])
				)
		frappe.db.sql(query, debug=True)

	entities = list(set(entities) - set(synced_entities))
	return entities

def get_entity_from_magento(url, entity_type=None, entity_id=None):
	""" get Item, Customer, Sales Order from Magento """

	if not all([entity_type, entity_id]):
		return

	headers = {"Content-Type": "application/json", "Accept": "application/json"}
	oauth = GetOauthDetails()
	response = requests.get(url=url, headers=headers, auth=oauth)

	if response.status_code != 200:
		""" error while fetching item, create scheduler log"""
		msg = "Error While fetching missing %s #%s"%(entity_type, entity_id)
		create_scheduler_exception(msg, "get_entity_from_magento", obj=json.dumps(response.json() or {}))
		
	elif not response.json():
		""" create log entity not available in magento """
		error = "can not find %s #%s in magento, please contact administrator"
		log_sync_error(
				entity_type, entity_id, response,
				error, "get_entity_from_magento",
				force_stop=True
			)
	else:
		return response.json()