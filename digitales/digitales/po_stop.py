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
						projected_qty = ((actual_qty - %s) - reserved_qty),  
						ordered_qty = (ordered_qty - %s)
					where 
						item_code = "%s" 
					and 
						warehouse = "%s"

				"""%(
						flt(po_draft_dict[0]["qty"] if po_draft_dict else 0), 
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
		bin_qty = frappe.db.sql(query,as_dict=1)

		for bin_item in bin_qty:
			if bin_item['projected_qty']<0:
				supplier = frappe.db.get_value("Purchase Order", po_name, "supplier")
				query = """ 
							select
								po.name
							from 
								`tabPurchase Order Item`poi, 
								`tabPurchase Order`po 
							where 
								poi.parent = po.name 
							and 
								poi.item_code = "%s"
							and 
								poi.warehouse = "%s"
							and 
								po.status = "Draft"
							and
								po.supplier = "%s"
						"""%(bin_item['item_code'], bin_item['warehouse'], supplier)	
				draft_po = frappe.db.sql(query,as_dict=1)

				if draft_po:
					increase_po_qty(draft_po[0]['name'], bin_item['item_code'], bin_item['projected_qty'])
				else:
					# create_new_po(bin_item['item_code'], bin_item['projected_qty'], bin_item['warehouse'], supplier)
					new_po_items.append({
						"item_code": bin_item['item_code'],
						"qty": bin_item['projected_qty'],
					})
		if new_po_items:
			create_purchase_order(new_po_items, bin_item['warehouse'], supplier)


def increase_po_qty(draft_po, item_code, pro_qty):
	frappe.db.sql(""" 
					update 
						`tabPurchase Order Item`
					set 
						qty = '%s' 
					where 
						parent = '%s'
				"""%((pro_qty * -1), draft_po))
	item_qty = frappe.db.get_value("Purchase Order Item", {"parent":draft_po, "item_code": item_code}, ["name","qty"])
	frappe.db.set_value("Purchase Order Item", item_qty[0], "qty", item_qty[1] + (pro_qty*-1))

# def create_new_po(item_code, pro_qty, warehouse, supplier):
# 	po = frappe.new_doc('Purchase Order')
# 	po.supplier= supplier
# 	poi = po.append('po_details', {})
# 	poi.item_code = item_code
# 	poi.qty = (pro_qty * -1)
# 	poi.warehouse = warehouse
# 	po.save(ignore_permissions=True)
# 	return po.name
		
def create_purchase_order(items, warehouse, supplier):
	""" create new purchase order for cancelled po """
	doc = frappe.new_doc("Purchase Order")
	doc.supplier = supplier
	
	doc.set("po_details", [])
	for item in items:
		frappe.errprint(item)
		po_item = doc.append("po_details", {})
		po_item.item_code = item.get("item_code")
		po_item.qty = item.get("qty") * -1
		po_item.warehouse = warehouse
	
	doc.save(ignore_permissions=True)