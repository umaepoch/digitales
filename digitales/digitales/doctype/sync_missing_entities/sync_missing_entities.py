# Copyright (c) 2013, digitales and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

from digitales.sync.orders import create_or_update_sales_order
from digitales.sync.products import create_or_update_item
from digitales.sync.sync_missing_entities import get_entity_from_magento

func_map = {
	"Item": create_or_update_item,
	"Sales Order": create_or_update_sales_order
}

class SyncMissingEntities(Document):

	def onload(self):
		self.sync_stat = ""
	
	def sync_entity(self):
		self.sync_stat = ""

		if self.missing_entities:
			entities = [idx.strip() for idx in self.missing_entities.split(",")]
			entity_type = "Item" if self.entity == "Products" else "Sales Order"
			self.sync_entities(entity_type, entities)
		else:
			frappe.throw("Please add the missing entities first")

	def sync_entities(self, entity_type, entities):
		url = "http://digitales.com.au/api/rest/{entity_type}?filter[1][attribute]={field}&filter[1][eq]=%s"
		if entity_type == "Item":
			url = url.format(
				entity_type="products",
				field="sku"
			)
		elif entity_type == "Sales Order":
			url = url.format(
				entity_type="orders",
				field="increment_id"
			)

		sync_stat = {}
		for entity in entities:
			response = get_entity_from_magento(url%(entity), entity_type=entity_type, entity_id=entity)
			if response:
				idx = response.keys()[0]
				status = func_map[entity_type](response[idx])
				sync_stat.update(status) if status else sync_stat.update({ entity: { "modified_date":  response[idx].get("updated_at") or ""} })
			else:
				sync_stat.update({
					entity: {
						"operation": "Entity Not Found",
						"name": response.get("entity_od") if response and response.get("entity_id") else entity,
					}
				})

		uri = "{url}/desk#Form/{dt}/".format(url=frappe.utils.get_url(), dt=entity_type)
		html = frappe.get_template("templates/status/sync_log_stat.html").render({"sync_stat": sync_stat, "uri":uri})
		self.sync_stat = html.strip()
