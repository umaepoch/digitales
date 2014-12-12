
from __future__ import unicode_literals
import frappe
from frappe.widgets.reportview import get_match_cond
from frappe.utils import add_days, cint, cstr, date_diff, rounded, flt, getdate, nowdate, \
	get_first_day, get_last_day,money_in_words, now, nowtime
from frappe import _
from frappe.model.db_query import DatabaseQuery


def create_purchase_order(doc,method):

	for d in doc.get('sales_order_details'):
		ordered_qty=frappe.db.sql("""select sum(s.qty)-sum(s.delivered_qty) as qty  
				from `tabSales Order Item` s inner join `tabSales Order` so on s.parent=so.name 
				where s.item_code='%s' and so.docstatus=1 and so.delivery_status='Not Delivered' 
				or so.delivery_status='Partly Delivered'"""%d.item_code,as_list=1,debug=1)
		frappe.errprint(ordered_qty)
		qty=flt(ordered_qty[0][0]-d.actual_qty)
		frappe.errprint(qty)

		if qty>0:
				supplier=frappe.db.sql("""select default_supplier from `tabItem` where name='%s'"""%d.item_code,as_list=1)
				frappe.errprint(supplier[0][0])
				purchase_order=frappe.db.sql("""select name from `tabPurchase Order` where supplier='%s' and docstatus=0"""%supplier[0][0],as_list=1)
				frappe.errprint(purchase_order)

				if purchase_order:
					purchase_order_item=frappe.db.sql("""select item_code from `tabPurchase Order Item` where parent='%s' and item_code='%s'"""%(purchase_order[0][0],d.item_code),as_list=1)
					frappe.errprint(purchase_order_item)

					if purchase_order_item:
						for item in purchase_order_item:
							frappe.errprint(item[0])

							if item[0]==d.item_code:
					 			frappe.errprint(item[0])
						 		update_qty(doc,d,item[0],purchase_order[0][0],qty)			 	
			 	
							else:
								frappe.errprint(["not equal",d.item_code])
								child_entry=update_child_entry(doc,d,purchase_order[0][0],qty)

					else:
						frappe.errprint(["not equal",d.item_code])
						child_entry=update_child_entry(doc,d,purchase_order[0][0],qty)

				else:
					create_new_po(doc,d,supplier[0][0],qty)

def create_new_po(doc,d,supplier,qty):
	po = frappe.new_doc('Purchase Order')
	po.supplier= supplier
	e = po.append('po_details', {})
	e.item_code=d.item_code
	e.item_name=d.item_name
	e.description=d.description
	e.qty= qty
	e.uom=d.stock_uom
	e.conversion_factor=1
	e.rate=d.rate
	e.amount=d.amount
	e.base_rate=d.rate
	e.base_amount=d.amount
	e.warehouse=d.warehouse
	e.schedule_date=d.transaction_date
	po.taxes_and_charges=doc.taxes_and_charges
	po.save(ignore_permissions=True)
	frappe.errprint(po.name)
	#update_so_details(doc,d,d.item_code,po.name)
	#update_sales_order(doc,d.item_code,po.name,e.name)

def update_child_entry(doc,d,purchase_order,qty):
	doc1 = frappe.get_doc("Purchase Order", purchase_order)
	frappe.errprint(doc1)
	poi = doc1.append('po_details', {})
	poi.item_code=d.item_code
	poi.item_name=d.item_name
	poi.description=d.description
	poi.qty=qty
	poi.uom=d.stock_uom
	poi.conversion_factor=1
	poi.rate=d.rate
	poi.amount=d.amount
	poi.base_rate=d.rate
	poi.base_amount=d.amount
	poi.warehouse=d.warehouse
	poi.schedule_date=d.transaction_date
	doc1.save(ignore_permissions=True)
	
def update_qty(doc,d,item,purchase_order,qty):
	frappe.errprint("in update qty")
	qty11=frappe.db.sql("""select qty from `tabPurchase Order Item` where item_code='%s' and parent='%s'"""%(item,purchase_order),as_list=1,debug=1)
	frappe.errprint(["query qty",qty11[0][0]])
	qty1=flt(qty11[0][0]+flt(qty))
	frappe.errprint(qty1)
	frappe.db.sql("""update `tabPurchase Order Item` set qty='%s' where parent='%s' and item_code='%s'"""%(qty1,purchase_order,item))
	frappe.db.commit()
