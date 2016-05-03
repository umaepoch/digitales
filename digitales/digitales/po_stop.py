import frappe
import json
from frappe.utils import flt, today
from frappe import _

@frappe.whitelist()
def stop_po_items(po_name, items):
	items = json.loads(items)
	check_available_pr(items, po_name)
	update_bin_qty(items)
	update_po_item_status(items, po_name)
	create_po_negative_qty(items,po_name)
	return "true"

def update_po_item_status(items, po_name): 
	query = """ update 
					`tabPurchase Order Item` 
				set 
					stop_status = "Yes",
					stop_date = '{}'
				where 
					item_code in ({}) 
				and 
					parent = "{}" 
			""".format(today(), ",".join(["'%s'"%item_code for item_code in items.keys()]), po_name)
	frappe.db.sql(query)

def update_bin_qty(items):
	item_qty_po_draft = frappe.db.sql(
		"""select
				item_code,
				sum(qty) as qty,
				warehouse
			from 

				`tabPurchase Order Item`poi, 
				`tabPurchase Order`po 
			where 
				poi.parent = po.name 
			and 
				poi.item_code in ({})
			and 
				po.status = "Draft"
			group by item_code, warehouse
		""".format(
				",".join(["'%s'"%item_code for item_code in items.keys()])
			), as_dict=True)
	
	for item_code, item in items.iteritems():
		filters = {
			"item_code": item_code,
			"warehouse": item.get('warehouse')
		}

		docname = frappe.db.get_value("Bin", filters, "name")
		bin = frappe.get_doc("Bin", docname)

		po_draft_dict = filter(lambda _item: _item.get("item_code") == item_code
								and _item.get("warehouse") == item.get('warehouse'), 
								item_qty_po_draft
							)
		
		query = """ update 
						`tabBin` 
					set 
						projected_qty = (projected_qty - %s),
						ordered_qty = (ordered_qty - %s)
					where 
						item_code = "%s" 
					and 
						warehouse = "%s"
				"""%(
						flt(item.get('qty')), 
						flt(item.get('qty')),  
						item_code, 
						item.get('warehouse')
					)
		frappe.db.sql(query)

def check_available_pr(items, po_name):
	query = """
				select
					pr.name as pr_name,
					group_concat(pri.item_code) as items
				from 
					`tabPurchase Receipt` pr,
					`tabPurchase Receipt Item` pri
				where 
					pri.item_code in ({}) 
				and 
					pri.prevdoc_docname = "{}"
				and 
					pr.status = "Draft"
				and
					pr.name=pri.parent
				group by pri.parent
			""".format(
					",".join(["'%s'"%item_code for item_code in items.keys()]), 
					po_name
				)
	pr_available = frappe.db.sql(query, as_dict=True)
	
	if pr_available:
		pr_data = ["Items: " + item['items'] + " linked with: " + item['pr_name'] for item in pr_available ]
		frappe.throw(_(pr_data[0]))

def create_po_negative_qty(items,po_name):
	new_po_items = []
	for item_code, item in items.iteritems():
		query = """
					select 
						item_code,
						warehouse,
						projected_qty
					from
						`tabBin`
					where
						item_code = "%s"
					and
						warehouse = "%s"
				"""%(item_code, 
						item.get('warehouse'))
		bin_details = frappe.db.sql(query)
		for item_code, warehouse, projected_qty in bin_details:
			if projected_qty<0:
				supplier = frappe.db.get_value("Purchase Order", po_name, "supplier")

				# get draft po name
				draft_po = frappe.db.get_value(
					"Purchase Order", 
					{ 
						"supplier": supplier,
						"docstatus": 0,
						"status": "Draft"
					},
					"name"
				)

				if draft_po:
					append_or_increase_po_item_qty(draft_po, item_code, projected_qty, warehouse)
				else:
					new_po_items.append({
						"item_code": item_code,
						"qty": projected_qty,
						"warehouse": warehouse
					})

	if new_po_items:
		create_purchase_order(new_po_items, supplier)

def append_or_increase_po_item_qty(draft_po, item_code, projected_qty, warehouse):
	def append_item(draft_po, item_code, qty, warehouse):
		"""append new item to PO"""
		po = frappe.get_doc("Purchase Order", draft_po)
		po_item = po.append("po_details", {})
		po_item.item_code = item_code
		po_item.qty = qty
		po_item.warehouse = warehouse
		po.save(ignore_permissions=True)

	def increase_item_qty(draft_po, poi_name, item_code, warehouse):
		""" increase PO item qty """
		query = """ select ifnull(sum(qty), 0) as qty from `tabPurchase Order Item` poi, `tabPurchase Order` po
				where po.name=poi.parent and poi.item_code='{}' and po.name<>'{}' and po.docstatus=0""".format(item_code,draft_po)
		aready_in_draft = frappe.db.sql(query, as_dict=True)

		if aready_in_draft: aready_in_draft = aready_in_draft[0].get('qty') or 0
		draft_qty = (projected_qty * -1) - aready_in_draft

		if draft_qty > 0:
			frappe.db.set_value("Purchase Order Item", poi_name, "qty", draft_qty)
		else:
			frappe.throw("You have extra copies of Item : {} in draft".format(item_code))

	poi_name = frappe.db.get_value(
			"Purchase Order Item",
			{
				"parent":draft_po,
				"item_code": item_code,
				"warehouse": warehouse
			},
			"name")

	if poi_name:
		increase_item_qty(draft_po, poi_name, item_code, warehouse)
	else:
		append_item(draft_po, item_code, projected_qty*-1, warehouse)

def create_purchase_order(items, supplier):
	""" create new purchase order for cancelled po """
	doc = frappe.new_doc("Purchase Order")
	doc.supplier = supplier
	
	doc.set("po_details", [])
	for item in items:
		po_item = doc.append("po_details", {})
		po_item.item_code = item.get("item_code")
		po_item.qty = item.get("qty") * -1
		po_item.warehouse = item.get("warehouse")
	
	doc.save(ignore_permissions=True)

# def check_po_draft(doc, method):
# 	item_in_draft = []
# 	for item in doc.po_details:
# 		query = """
# 					select 
# 						item_code,
# 						po.name
# 					from 
# 						`tabPurchase Order Item`poi,
# 						`tabPurchase Order`po 
# 					where 
# 						poi.parent = po.name
# 					and
# 						poi.item_code = "%s"
# 					and
# 						po.docstatus = 0
# 				"""
# 		item = frappe.db.sql(query%(item.item_code),as_list=True)
# 		if item:
# 			item_in_draft.append(item[0][0])
# 		if item_in_draft:
# 			frappe.msgprint("Items are Already In PO Draft : " + ",".join(item_in_draft))
# 	return item_in_draft