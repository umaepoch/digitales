import frappe
import json
from frappe.utils import flt, today
from frappe import _

@frappe.whitelist()
def stop_po_items(po_name, items):
	items = json.loads(items)
	check_available_pr(items, po_name)
	update_po_item_status(items, po_name)
	update_bin_qty(items)
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
			), as_dict=True, debug=True)
	
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