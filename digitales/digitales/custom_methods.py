
from __future__ import unicode_literals
import frappe
from frappe.widgets.reportview import get_match_cond
from frappe.utils import add_days, cint, cstr, date_diff, rounded, flt, getdate, nowdate, \
	get_first_day, get_last_day,money_in_words, now, nowtime
from frappe import _
from frappe.model.db_query import DatabaseQuery

# On submission of sales order---------------------------------------------------------------------------------------------------------------------------------------------------------------------
def create_purchase_order(doc,method):

	for d in doc.get('sales_order_details'):
		ordered_qty=frappe.db.sql("""select sum(s.qty)-sum(s.delivered_qty) as qty  
									from `tabSales Order Item` s inner join `tabSales Order` so 
										on s.parent=so.name where s.item_code='%s' and so.docstatus=1 
										and so.delivery_status='Not Delivered' 
										or so.delivery_status='Partly Delivered'"""
										%d.item_code,as_list=1)
		#frappe.errprint(ordered_qty)
		qty=flt(ordered_qty[0][0]-d.actual_qty)
		#frappe.errprint(qty)
		if qty>0:
				supplier=frappe.db.sql("""select default_supplier from `tabItem` where 
											name='%s'"""%d.item_code,as_list=1)
				#frappe.errprint(supplier[0][0])
				purchase_order=frappe.db.sql("""select name from `tabPurchase Order` where supplier='%s'
												 and docstatus=0"""%supplier[0][0],as_list=1)
				#frappe.errprint(purchase_order)
				if purchase_order:
					purchase_order_item=frappe.db.sql("""select item_code from `tabPurchase Order Item`
															 where parent='%s' and item_code='%s'"""
															 %(purchase_order[0][0],d.item_code),as_list=1)
					#frappe.errprint(purchase_order_item)
					if purchase_order_item:
						for item in purchase_order_item:
							#frappe.errprint(item[0])
							if item[0]==d.item_code:
					 			#frappe.errprint(item[0])
						 		update_qty(doc,d,item[0],purchase_order[0][0],qty)			 		
							else:
								#frappe.errprint(["not equal",d.item_code])
								child_entry=update_child_entry(doc,d,purchase_order[0][0],qty)
					else:
						#frappe.errprint(["not equal",d.item_code])
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
	#frappe.errprint(po.name)
	#update_so_details(doc,d,d.item_code,po.name)
	#update_sales_order(doc,d.item_code,po.name,e.name)

def update_child_entry(doc,d,purchase_order,qty):
	doc1 = frappe.get_doc("Purchase Order", purchase_order)
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
	#update_so_details(doc,d,d.item_code,doc1.name)
	
def update_qty(doc,d,item,purchase_order,qty):
	#frappe.errprint("in update qty")
	qty11=frappe.db.sql("""select qty from `tabPurchase Order Item` where 
							item_code='%s' and parent='%s'"""
								%(item,purchase_order),as_list=1)
	qty1=flt(qty11[0][0]+flt(qty))
	frappe.db.sql("""update `tabPurchase Order Item` set qty='%s' 
						where parent='%s' and item_code='%s'"""
							%(qty1,purchase_order,item))
	frappe.db.commit()
	#update_so_details(doc,d,item,purchase_order)

def update_so_details(doc,d,item,purchase_order):
	doc2 = frappe.get_doc("Purchase Order", purchase_order)
	so = doc2.append('so_item_detail', {})
	so.item_code=item
	so.qty=d.qty
	so.sales_order_name=doc.name
	doc2.save(ignore_permissions=True)




# On submission of Purchase Receipt--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def stock_assignment(doc,method):
	#frappe.errprint("in stock assignment")
	for d in doc.get('purchase_receipt_details'):
		if d.item_code:
			sales_order=frappe.db.sql("""select s.parent,s.qty-s.assigned_qty as qty from `tabSales Order Item` s 
										inner join `tabSales Order` so on s.parent=so.name 
										 where s.item_code='%s' and so.docstatus=1 and 
										 s.qty!=s.assigned_qty and so.delivery_status='Not Delivered' 
										 or so.delivery_status='Partly Delivered' order by 
										 so.priority,so.creation"""%d.item_code,as_list=1)
			qty=d.qty
			if sales_order:
				for i in sales_order:
					assigned_qty=frappe.db.sql(""" select assigned_qty from `tabSales Order Item` 
													where parent='%s' and item_code='%s'"""
														%(i[0],d.item_code),as_list=1)
					if qty>0 and i[1]>0:
						if qty>=i[1]:
							qty=qty-i[1]
							
							assigned_qty=(assigned_qty[0][0]+i[1])
							update_assigned_qty(assigned_qty,i[0],d.item_code)				
							create_stock_assignment(doc.name,d,i[0],i[1],i[1])
						else:
							assigned_qty=flt(assigned_qty[0][0]+qty)
							update_assigned_qty(assigned_qty,i[0],d.item_code)
							create_stock_assignment(doc.name,d,i[0],i[1],qty)
							qty=0.0

def update_assigned_qty(assigned_qty,sales_order,item_code):
	frappe.db.sql("""update `tabSales Order Item` 
						set assigned_qty='%s' where parent='%s' 
							and item_code='%s'"""%
								(assigned_qty,sales_order,item_code))
	frappe.db.commit()


def create_stock_assignment(purchase_receipt,d,sales_order,ordered_qty,assigned_qty):
	#frappe.errprint("in stock assignment")
	sa = frappe.new_doc('Stock Assignment Log')
	sa.purchase_receipt=purchase_receipt
	sa.sales_order=sales_order
	sa.ordered_qty=ordered_qty
	sa.assign_qty=assigned_qty
	sa.item_code=d.item_code
	sa.save(ignore_permissions=True)
	
def stock_cancellation(doc,method):
	# frappe.errprint("in stock cancellation")
	delivered_note=frappe.db.sql("""select delivery_note from `tabStock Assignment Log`
										where purchase_receipt='%s'"""
										%doc.name,as_list=1)
	if delivered_note:
		frappe.msgprint("Delivery Note is already generated against this purchase receipt,so first you have to delete delivery note='"+delivered_note[0][0]+"'")
	else:
		pass

# Onn sibmission of delivery Note---------------------------------------------------------------------------------------------------------------------------------
def update_stock_assignment_log_on_submit(doc,method):
	# frappe.errprint("in update stock assignment log")
	for d in doc.get('delivery_note_details'):
		sales_order_name=frappe.db.sql("""select s.against_sales_order from 
										`tabDelivery Note Item` s inner join `tabDelivery Note` so 
											on s.parent=so.name where s.item_code='%s' 
												and so.docstatus=1 and s.parent='%s' 
													order by so.creation"""
														%(d.item_code,doc.name),as_list=1)
		break
	if sales_order_name:
		frappe.db.sql("""update `tabStock Assignment Log` 
							set delivered_qty='%s', delivery_note='%s'
								where sales_order='%s' and item_code='%s'"""
									%(d.qty,doc.name,sales_order_name[0][0],d.item_code))
		frappe.db.commit()



def update_stock_assignment_log_on_cancel(doc,method):
	for d in doc.get('delivery_note_details'):
		frappe.db.sql("""update `tabStock Assignment Log` 
							set delivery_note='',delivered_qty=0.00
								where item_code='%s'"""%d.item_code)
		frappe.db.commit()


def validate_qty_on_submit(doc,method):
	for d in doc.get('delivery_note_details'):
		if d.assigned_qty>=d.qty:
			pass
		else:
			frappe.msgprint("Delivered Quantity must be less than assigned_qty for item_code='"+d.item_code+"'",raise_exception=1)




#For calling API through Poster--------------------------------------------------------------------------------------------


@webnotes.whitelist(allow_guest=True)
def GetItem(parameters):
	return "in getitem"
	check item_code (sku) is present or not
	if yes:
		item=update_item(parameters)
	if no:
		item=create_item(parameters)


def update_item(parameters):
	pass

def create_item(parameters):
	pass





@webnotes.whitelist(allow_guest=True)
def GetCustomer(parameters):
	parameters[1:-1]
	return "in customer"
	check customer id(cz name can be same) is present or not
	if yes:
		customer=update_customer(parameters)
	if no:
		customer=create_customer(parameters)


def update_customer(parameters):
	pass

def create_customer(parameters):
	pass





@webnotes.whitelist(allow_guest=True)
def GetSalesOrder(parameters):
	return "in GetSalesOrder"
	check sales_order id is present or not
	if yes and docstatus ==0:
		item=update_sales_order(parameters)
	if no:
		item=create_sales_order(parameters)


def update_sales_order(parameters):
	pass

def create_sales_order(parameters):
	pass