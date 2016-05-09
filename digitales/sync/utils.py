from __future__ import unicode_literals
import json
import frappe
import requests
import datetime
from frappe import _
from frappe.utils import get_datetime, now
from requests_oauthlib import OAuth1 as OAuth
from digitales.digitales.Api_methods import update_execution_date, GetOauthDetails, create_scheduler_exception

def date_minus_sec(date):
	return get_datetime(date) - datetime.timedelta(seconds=1)

def get_entity_and_page_count(max_date, entity_type="Item"):
	""" get total number of entities to sync and page count """

	entity_count = {
		"Item": "products_mcount",
		"Customer": "customer_mcount",
		"Sales Order": "orders_mcount"
	}
	page_count = {
		"Item": "product_pages_per_100_mcount",
		"Customer": "customer_pages_per_100_mcount",
		"Sales Order": "orders_pages_per_100_mcount"
	}

	url = "http://digitales.com.au/api/rest/mcount?start_date=%s"%max_date
	response = get_entities_from_magento(url, entity_type="Item")

	if response:
		return {
			"entity_count": response.get(entity_count[entity_type]),
			"page_count": response.get(page_count[entity_type])
		}
	else:
		return None

def get_entities_from_magento(url, entity_type=None):
	""" get Item, Customer, Sales Order from Magento """

	if not entity_type:
		return

	headers = {"Content-Type": "application/json", "Accept": "application/json"}
	oauth = GetOauthDetails()
	response = requests.get(url=url, headers=headers, auth=oauth)

	if response.status_code != 200:
		""" error while fetching item, create scheduler log"""
		msg = "Error While fetching %s(s)"%(entity_type)
		create_scheduler_exception(msg, "get_entity_from_magento", obj=json.dumps(response.json() or {}))
		return None
		
	elif not response.json():
		""" create log entity not available in magento """
		error = "empty response from magento, please contact administrator"
		create_scheduler_exception(msg, "get_entity_from_magento", obj=json.dumps(response.json() or {}))
		return None
	else:
		return response.json()

def log_sync_status(
	entity_type, count_response={},
	entities_to_sync=0, pages_to_sync=0,
	synced_entities={}):

	""" log Magento >> ERPNext entity sync status """

	log = frappe.new_doc("Sync Log")
	log.date = now()
	log.entity_type = entity_type
	log.total_count = entities_to_sync
	log.pagewise_count = pages_to_sync - 1 if pages_to_sync else 0
	log.synced_failed = len([entity_id for entity_id, status in synced_entities.iteritems() if status.get("operation") == None])
	log.synced_count = len([entity_id for entity_id, status in synced_entities.iteritems() if status.get("operation") != None])
	log.count_api_response = json.dumps(count_response)
	log.synced_entities = json.dumps(synced_entities)
	log.sync_stat = ""
	log.save(ignore_permissions=True)