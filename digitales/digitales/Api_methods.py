from __future__ import unicode_literals
import frappe
from frappe.widgets.reportview import get_match_cond
from frappe.utils import add_days, cint, cstr, date_diff, rounded, flt, getdate, nowdate, \
	get_first_day, get_last_day,money_in_words, now, nowtime
from frappe import _
from frappe.model.db_query import DatabaseQuery
from requests_oauthlib import OAuth1 as OAuth
from datetime import datetime
from time import sleep
import requests
import json
import datetime
import time
import itertools

def create_purchase_order(doc,method):
	check_duplicate_item_code(doc)
	check_ispurchase_item(doc,method)
	return "Done"

def check_duplicate_item_code(doc):
	duplicate_item = []
	s = [duplicate_item.append(d.item_code) for d in doc.get('sales_order_details')]
	for item_code in duplicate_item:
		if duplicate_item.count(item_code) > 1:
			frappe.throw(_("Item code {0} is added twise, merge the qty against same Item Code").format(item_code))

def check_ispurchase_item(doc,method):
	for d in doc.get('sales_order_details'):
		if frappe.db.get_value("Item",{'is_purchase_item':'Yes','name':d.item_code},'name'):
			supplier_validate(d.item_code)
			if frappe.db.get_value("Item",{'is_stock_item':'Yes','name':d.item_code},'name'):
				Stock_Availability(doc,d)
				assign_extra_qty_to_other(d)
			else:
				create_purchase_order_record(doc,d, d.qty)
				# print d.qty
				# bin_details = frappe.db.sql(''' select ifnull(sum(soi.qty), 0) - ifnull(sum(soi.delivered_qty), 0)  from
                #                                `tabSales Order Item` soi, `tabSales Order` so where soi.parent = so.name
                #                               and ifnull(soi.stop_status, "No") <> "Yes" and so.status <> "Stopped" and soi.docstatus = 1
                #                              and soi.item_code ="%s" and soi.warehouse = "%s" '''%(d.item_code, d.warehouse), as_list=1, debug=1)
				# print "bin_details***********",bin_details
				# so_qty = flt(bin_details[0][0]) if bin_details else 0.0
				# print"so_qty",so_qty
				# po_qty = get_po_qty(d.item_code, d.warehouse) - so_qty # if negative then make po
				# print "PO qty", po_qty
				# ss
				# if po_qty < 0:
				# 	create_purchase_order_record(doc,d, flt(po_qty*-1))

def Stock_Availability(so_doc, child_args):
	bin_details = frappe.db.get_value('Bin', {'item_code': child_args.item_code, 'warehouse': child_args.warehouse}, '*', as_dict=1)
	if bin_details:
		assign_qty = get_assigned_qty(child_args.item_code, child_args.warehouse) #get assigned qty
		bin_qty = flt(bin_details.actual_qty) - flt(assign_qty) # To calculate the available qty
		if flt(bin_qty) > 0.0 and flt(bin_qty) >= flt(child_args.qty):
			sal = create_stock_assignment_document(child_args, so_doc.name, child_args.qty)
			# Stock in Hand
			make_history_of_assignment(sal, so_doc.transaction_date, "Stock In Hand", "", child_args.qty)
			child_args.assigned_qty = child_args.qty
		else:
			assigned_qty = bin_qty
			po_qty = (flt(child_args.qty) - flt(assigned_qty)) if flt(assigned_qty) > 0.0 else flt(child_args.qty)
			if flt(assigned_qty) > 0.0:
				sal = create_stock_assignment_document(child_args, so_doc.name, assigned_qty)
				# Stock in Hand
				make_history_of_assignment(sal, so_doc.transaction_date, "Stock In Hand", "", assigned_qty)
				child_args.assigned_qty = assigned_qty
			if flt(po_qty) > 0.0:
				new_po_qty = get_po_qty(child_args.item_code, child_args.warehouse) + flt(bin_details.actual_qty) - flt(bin_details.reserved_qty) # if negative then make po
				if new_po_qty < 0:
					create_purchase_order_record(so_doc, child_args, flt(new_po_qty * -1))

def get_assigned_qty(item_code, warehouse):
	assign_qty = frappe.db.sql(''' select sum(ifnull(assigned_qty,0)) - sum(ifnull(delivered_qty,0)) from `tabSales Order Item` where item_code = "%s"
		and warehouse ="%s" and docstatus=1 and ifnull(qty,0) >= ifnull(assigned_qty,0)'''%(item_code, warehouse), as_list = 1)
	if assign_qty:
		return assign_qty[0][0] or 0.0
	return 0.0

def assign_extra_qty_to_other(data):
	assign_qty = get_assigned_qty(data.item_code, data.warehouse)
	bin_details = frappe.db.get_value('Bin', {'item_code': data.item_code, 'warehouse': data.warehouse}, '*', as_dict=1)
	qty = flt(bin_details.actual_qty) - flt(assign_qty)
	if cint(qty) > 0:
		sales_order = get_item_SODetails(data.item_code)
		if sales_order:
			create_StockAssignment_AgainstSTopSOItem(data, sales_order, qty)

def get_po_qty(item_code, warehouse=None):
	cond = 'poi.warehouse ="%s"'%(warehouse) if warehouse else '1=1'
	qty = frappe.db.sql(''' select sum(ifnull(poi.qty,0)-ifnull(poi.received_qty,0)) from `tabPurchase Order Item` poi, `tabPurchase Order` po
		where poi.parent = po.name and po.status <> 'Stopped' and ifnull(poi.stop_status, 'No') <> 'Yes' and poi.docstatus <> 2 and poi.item_code = "%s" and %s'''%(item_code, cond), as_list=1)
	qty = flt(qty[0][0]) if qty else 0.0
	return qty

def supplier_validate(item_code):
	if not frappe.db.get_value('Item', item_code, 'default_supplier'):
		frappe.throw(_("Default supplier is not defined against the item code {0}").format(item_code))

def create_purchase_order_record(doc,d,qty):
	supplier=frappe.db.sql('''select default_supplier from `tabItem` where
								name="%s"'''%d.item_code,as_list=1)
	if supplier:
		purchase_order=frappe.db.sql('''select name from `tabPurchase Order` where supplier="%s"
										 and docstatus=0'''%supplier[0][0],as_list=1)
		if purchase_order:
			purchase_order_item=frappe.db.sql('''select item_code from `tabPurchase Order Item`
													 where parent="%s" and item_code="%s"'''
													 %(purchase_order[0][0],d.item_code),as_list=1)
			if purchase_order_item:
				for item in purchase_order_item:
					if item[0]==d.item_code:
						purchase_order_qty=frappe.db.sql('''select qty,rate from `tabPurchase Order Item`
													 where parent="%s" and item_code="%s"'''
													 %(purchase_order[0][0],d.item_code),as_list=1)

						qty_new= qty + flt(purchase_order_qty[0][0])
						update_qty(doc,d,item[0],purchase_order[0][0],qty_new,purchase_order_qty[0][1])
					else:
						child_entry=update_child_entry(doc,d,purchase_order[0][0],qty)
			else:
				child_entry=update_child_entry(doc,d,purchase_order[0][0],qty)
			purchase_order = purchase_order[0][0]
		else:
			purchase_order = create_new_po(doc,d,supplier[0][0],qty)

		if purchase_order:
			qty = qty if flt(qty) < flt(d.qty) else flt(d.qty)
			frappe.db.sql(''' update `tabSales Order Item` set po_data = "%s", po_qty="%s" where name = "%s"'''%(purchase_order, qty, d.name))
	else:
		frappe.throw("Supplier must be specify for items in Item Master Form.")

def create_stock_assignment_document(args, sales_order, assigned_qty):
	sa = frappe.new_doc('Stock Assignment Log')
	sa.item_name = args.item_name
	sa.sales_order = sales_order
	sa.ordered_qty = frappe.db.get_value('Sales Order Item', {'item_code': args.item_code, 'parent': sales_order}, 'qty')
	sa.assign_qty = assigned_qty
	sa.purchase_receipt_no = args.parent if args.doctype == 'Purchase Receipt Item' else ''
	sa.item_code = args.item_code
	sa.media  = frappe.db.get_value("Item",args.item_code,'item_group')
	sa.customer, sa.customer_name = frappe.db.get_value('Sales Order',sa.sales_order,['customer', 'customer_name'])
	sa.save(ignore_permissions=True)
	return sa.name

def delete_stock_assignment(doc, method):
	st_error=stop_error(doc)
	if(st_error=='true'):
		frappe.throw(_("You can not cancel this sales order"))
	else:
		stl = frappe.db.sql(""" select * from `tabStock Assignment Log` where sales_order = '%s'"""%(doc.name), as_dict=1)
		if stl:
			for data in stl:
				delete_stl(data)
		reduce_po(doc)
		#update_assigned_qty(doc)
		update_stock_assigned_qty_to_zero(doc)
		

def stop_error(doc):
	st_error=''
	for data in doc.get('sales_order_details'):
		if(data.stop_status=="Yes"):
			st_error='true'
			break
	return st_error

def delete_stl(args):
	frappe.db.sql(''' delete from `tabDocument Stock Assignment` where parent="%s"	'''%(args.name))
	frappe.db.sql(''' delete from `tabStock Assignment Log` where name="%s"	'''%(args.name))

def update_stock_assigned_qty_to_zero(doc):
	for data in doc.get('sales_order_details'):
		frappe.db.sql(''' update `tabSales Order Item` set po_data = (select true from dual where 1=2), po_qty=0.0, assigned_qty=0.0 where name = "%s"	'''%(data.name))
		data.assigned_qty = 0.0
		data.po_data = ''
		data.po_qty = 0.0

def update_assigned_qty(doc):
	query = '''	select s.parent as parent,ifnull(s.qty,0)-ifnull(s.assigned_qty,0) AS qty,
				s.assigned_qty as assigned_qty 
				from `tabSales Order Item` s inner join `tabSales Order` so
				on s.parent=so.name 
				where s.item_code="%s" and so.docstatus=1 and ifnull(s.stop_status, 'No') <> 'Yes' 
				and ifnull(s.qty,0)>ifnull(s.assigned_qty,0) 
				and so.status!='Stopped' order by so.priority,so.creation'''

	for item in doc.get('sales_order_details'):
		if item.assigned_qty > 0:
			sales_order = frappe.db.sql(query%(item.item_code), as_dict=1)
			
			if sales_order and len(sales_order)==1:
				assigned_qty_to_so(sales_order[0], item)
			elif sales_order and len(sales_order) > 1:
				so = [so[0] for so in sales_order]
				frappe.throw("Multiple Draft SO (%s) present for Item %s"%(",".join(so), item.item_code))
	
def assigned_qty_to_so(so, item):
	'''update assign qty to available so'''
	query = '''update `tabSales Order Item` 
			set assigned_qty = %s where item_code = "%s" and parent = "%s"'''
	if so.qty >= item.assigned_qty:
		frappe.db.sql(query%(item.assigned_qty, item.item_code, so.parent))
	elif so.qty < item.assigned_qty:
		frappe.db.sql(query%(so.qty, item.item_code, so.parent))
	


def reduce_po(doc):
	for data in doc.get('sales_order_details'):
		# get draft order(s)
		po_qty = data.qty - data.delivered_qty or 0
		query = '''
					select distinct poi.parent, poi.qty from `tabPurchase Order Item` poi, `tabPurchase Order` po
					where poi.parent=po.name and po.docstatus=0 and po.status="Draft" and poi.item_code='%s'
					and poi.warehouse='%s'
				'''%(data.item_code, data.warehouse)
		results = frappe.db.sql(query)
		order = [result[0] for result in results] if results else None
		if order and len(order)==1:
			po_details = frappe.db.get_value('Purchase Order Item', {
				'parent': order[0],
				'item_code': data.item_code,
				'docstatus': 0
				}, '*', as_dict=1)

			update_child_table(po_details, data)
			update_parent_table(po_details)
		elif order and len(order) > 1:
			frappe.throw("Multiple Draft PO (%s) present for Item %s"%(",".join(order), data.item_code))

def update_child_table(po_details, data):
	if po_details:
		# po_qty = flt(data.po_qty) or flt(data.qty)
		po_qty = data.qty - data.delivered_qty or 0
		qty = flt(po_details.qty) - po_qty
		if flt(qty) >= 1.0:
			frappe.db.sql(""" update `tabPurchase Order Item` set qty = '%s' where name ='%s'"""%(qty, po_details.name))
		elif flt(qty) <= 0.0:
			delete_document('Purchase Order Item', po_details.name)

def update_parent_table(po_details):
	if po_details:
		count = frappe.db.sql(''' select ifnull(count(*),0) from `tabPurchase Order Item` where parent = "%s"	'''%(po_details.parent), as_list=1)
		if count:
			if count[0][0] == 0:
				frappe.delete_doc('Purchase Order', po_details.parent, ignore_permissions=True)

def stock_assignment(doc,method):
	for pr_details in doc.get('purchase_receipt_details'):
		if frappe.db.get_value("Item",{'is_stock_item':'Yes','name':pr_details.item_code},'name'):
			qty = flt(pr_details.qty)
			sales_order = get_SODetails(pr_details.item_code, pr_details.warehouse)
			if sales_order:
				check_stock_assignment(qty, sales_order, pr_details)

# So list which has stock not assign or partially assign
def get_SODetails(item_code, warehouse):
	return frappe.db.sql('''select s.parent as parent,ifnull(s.qty,0)-ifnull(s.assigned_qty,0) AS qty,
				s.assigned_qty as assigned_qty from `tabSales Order Item` s inner join `tabSales Order` so
				on s.parent=so.name where s.item_code="%s" and so.docstatus=1 and ifnull(s.stop_status, 'No') <> 'Yes' and
				ifnull(s.qty,0)>ifnull(s.assigned_qty,0) and so.status!='Stopped' and s.warehouse="%s"
				order by so.priority,so.creation'''%(item_code, warehouse),as_dict=1)

def check_stock_assignment(qty, sales_order, pr_details):
	for so_details in sales_order:
		if flt(qty) > 0.0 and flt(so_details.qty)>0:
			stock_assigned_qty = so_details.qty if flt(qty) >= flt(so_details.qty) else flt(qty)
			qty = (flt(qty) - flt(so_details.qty)) if flt(qty) >= flt(so_details.qty) else 0.0
			create_stock_assignment(stock_assigned_qty , so_details, pr_details)

def create_stock_assignment(stock_assigned_qty, sales_order_data, pr_details):
	sal = frappe.db.get_value('Stock Assignment Log', {'sales_order': sales_order_data.parent, 'item_code': pr_details.item_code},'*', as_dict=1)
	stock_assigned_qty = sales_order_data.qty if sales_order_data.qty < stock_assigned_qty else stock_assigned_qty
	if sal:
		sal_name = update_stock_assigned_qty(sal, stock_assigned_qty, pr_details)
	else:
		sal_name = create_stock_assignment_document(pr_details, sales_order_data.parent, stock_assigned_qty)
		make_history_of_assignment(sal_name,nowdate(),"Purchase Receipt", pr_details.parent, stock_assigned_qty)

def update_stock_assigned_qty(stock_assignment_details, assigned_qty, pr_details):
	doc_qty = get_document_STOCK_qty(stock_assignment_details.name)
	if cint(doc_qty) == cint(stock_assignment_details.assign_qty):
		assign_qty = cint(stock_assignment_details.assign_qty) + cint(assigned_qty)
	else:
		assign_qty = cint(doc_qty) + cint(assigned_qty)
	obj = frappe.get_doc('Stock Assignment Log', stock_assignment_details.name)
	obj.assign_qty = assign_qty
	update_doc_SAL(obj, pr_details, assigned_qty)
	obj.save(ignore_permissions=True)
	return stock_assignment_details.name

def update_doc_SAL(obj, pr_details, assigned_qty):
	sal = obj.append('document_stock_assignment', {})
	sal.document_no = pr_details.parent
	sal.qty = assigned_qty
	sal.created_date = nowdate()
	sal.document_type = 'Purchase Receipt'
	return True

def get_document_STOCK_qty(name):
	sum_qty = 0.0
	qty = frappe.db.sql(''' select ifnull(sum(qty),0) from `tabDocument Stock Assignment`
		where parent = "%s"'''%(name), as_list=1)
	if qty:
		sum_qty = qty[0][0]
	return sum_qty

def make_history_of_assignment(sal, date, doc_type, pr_name, qty):
	sal= frappe.get_doc('Stock Assignment Log', sal)
	sal_child = sal.append('document_stock_assignment', {})
	sal_child.created_date = nowdate();
	sal_child.document_type = doc_type
	sal_child.document_no = pr_name
	sal_child.qty = qty
	sal.save(ignore_permissions=True)

def stock_cancellation(doc,method):
	cancel_all_child_table(doc)
	cancel_parent_table(doc)
	# check_assigned_qty(doc)

def check_assigned_qty(doc):
	for data in doc.get('purchase_receipt_details'):
		bin_details = frappe.db.get_value('Bin', {'item_code': data.item_code, 'warehouse': data.warehouse}, '*', as_dict=1)
		if bin_details:
			assign_qty = get_assigned_qty(data.item_code, data.warehouse) #get assigned qty
			actual_qty = flt(bin_details.actual_qty)
			if flt(assign_qty) > flt(actual_qty):
				frappe.throw(_("Not allowed to cancel, the available stock of item {0} is assigned to the sales order").format(data.item_code))

def cancel_all_child_table(doc):
	sal_details = frappe.db.sql(''' select * from `tabDocument Stock Assignment`
		where document_no = "%s"'''%(doc.name), as_dict=1)
	if sal_details:
		for sal in sal_details:
			obj = frappe.get_doc('Stock Assignment Log', sal.parent)
			obj.assign_qty = flt(obj.assign_qty) - flt(sal.qty)
			to_remove_obj = []
			for d in obj.get('document_stock_assignment'):
				if d.name == sal.name:
					to_remove_obj.append(d)
			[obj.remove(d) for d in to_remove_obj]
			obj.save(ignore_permissions=True)

def cancel_parent_table(doc):
	sal_data = frappe.db.sql(''' select * from `tabStock Assignment Log` where assign_qty = 0''', as_dict=1)
	if sal_data:
		for data in sal_data:
			obj = frappe.get_doc('Stock Assignment Log', data.name)
			obj.delete()

def delete_document(table, name):
	frappe.db.sql(''' delete from `tab%s` where name = "%s" '''%(table, name))

def update_so_assign_qty(args):
	so_details = frappe.db.get_value('Sales Order Item', {'parent': args.sales_order, 'item_code': args.item_code}, 'assigned_qty') or 0.0
	qty = (flt(so_details) - flt(args.qty)) if flt(so_details) >= flt(args.qty) else 0.0
	frappe.db.sql(''' update `tabSales Order Item` set assigned_qty = "%s" where parent = "%s" and
		item_code = "%s" '''%(qty, args.sales_order, args.item_code))

def create_new_po(doc,d,supplier,qty):
	po = frappe.new_doc('Purchase Order')
	po.supplier= supplier
	po.currency = frappe.db.get_value('Supplier', supplier, 'default_currency')
	e = po.append('po_details', {})
	item_price = frappe.db.get_value("Item Price", {"item_code": d.item_code, "buying": 1}, "price_list_rate")
	e.item_code = d.item_code
	e.item_name = d.item_name
	e.description = d.description
	e.qty =  qty
	e.uom = d.stock_uom
	e.conversion_factor = 1
	e.rate = item_price if item_price else 0.0
	e.warehouse = d.warehouse
	e.schedule_date = nowdate()
	e.product_release_date = frappe.db.get_value("Item", d.item_code, "product_release_date")
	po.save(ignore_permissions=True)
	return po.name

def update_child_entry(doc,d,purchase_order,qty):
	doc1 = frappe.get_doc("Purchase Order", purchase_order)
	poi = doc1.append('po_details', {})
	item_price = frappe.db.get_value("Item Price", {"item_code": d.item_code, "buying": 1}, "price_list_rate")
	poi.item_code = d.item_code
	poi.item_name = d.item_name
	poi.description = d.description
	poi.qty = qty
	poi.uom = d.stock_uom
	poi.conversion_factor = 1
	poi.rate = item_price if item_price else 0.0
	poi.warehouse=d.warehouse
	poi.schedule_date=nowdate()
	poi.product_release_date = d.release_date_of_item
	doc1.save(ignore_permissions=True)

def update_qty(doc,d,item,purchase_order,qty,rate):
	amount=rate*qty
	frappe.db.sql("""update `tabPurchase Order Item` set qty='%s', amount='%s'
						where parent='%s' and item_code='%s'"""
							%(qty,amount,purchase_order,item))

def update_so_details(doc,d,item,purchase_order):
	doc2 = frappe.get_doc("Purchase Order", purchase_order)
	so = doc2.append('so_item_detail', {})
	so.item_code=item
	so.qty=d.qty
	so.sales_order_name=doc.name
	doc2.save(ignore_permissions=True)

def update_stock_assignment_log_on_submit(doc,method):
	for d in doc.get('delivery_note_details'):
		sales_order_name=frappe.db.sql("""select s.against_sales_order from
										`tabDelivery Note Item` s inner join `tabDelivery Note` so
											on s.parent=so.name where s.item_code='%s'
												and so.docstatus=1 and s.parent='%s'
													order by so.creation"""
														%(d.item_code,doc.name),as_list=1)
		if sales_order_name:
			delivery_note_name=frappe.db.sql(""" select delivery_note  from `tabStock Assignment Log` where
							sales_order='%s' and item_code='%s' and delivery_note is not null"""%(sales_order_name[0][0],d.item_code))

			if not delivery_note_name:
				frappe.db.sql("""update `tabStock Assignment Log`
								set delivered_qty='%s', delivery_note='%s'
									where sales_order='%s' and item_code='%s'"""
										%(d.qty,doc.name,sales_order_name[0][0],d.item_code))
			else:
				delivery_note = doc.name
				delivery_note_details=frappe.db.sql("""select delivered_qty from `tabStock Assignment Log`
												where sales_order='%s' and item_code='%s'"""%(sales_order_name[0][0],d.item_code))
				if delivery_note_details:
					qty=cint(delivery_note_details[0][0])+d.qty
					frappe.db.sql("""update `tabStock Assignment Log`
								set delivered_qty='%s', delivery_note='%s'
									where sales_order='%s' and item_code='%s'"""
										%(qty,delivery_note,sales_order_name[0][0],d.item_code))

def update_delivery_note(doc,method):
	for d in doc.get('delivery_note_details'):
		if(d.stop_status=="Yes"):
			frappe.throw(_("Item code {0} is stopped please delete it.").format(d.item_code))

def update_sales_invoice(doc,method):
	for d in doc.get('entries'):
		if(d.stop_status=="Yes"):
			frappe.throw(_("Item code {0} is stopped please delete it.").format(d.item_code))


def update_stock_assignment_log_on_cancel(doc,method):
	update_delivery_note(doc, method)
	for d in doc.get('delivery_note_details'):
		name=frappe.db.sql(""" select name,delivered_qty from `tabStock Assignment Log` where
							sales_order='%s' and item_code='%s'"""%(d.against_sales_order,d.item_code))
		if name:
			delivery_note=frappe.db.sql("""select delivery_note from `tabStock Assignment Log` where
									name='%s'"""%name[0][0])
			delivery_note_name=cstr(delivery_note[0][0]).split(", ")
			if d.parent in delivery_note_name:
				delivery_note_name.remove(d.parent)
				qty=cint(name[0][1])-d.qty
				if name:
					frappe.db.sql("""update `tabStock Assignment Log`
								set delivered_qty='%s',delivery_note='%s' where item_code='%s'"""%(qty,','.join(delivery_note_name),d.item_code))

def validate_qty_on_submit(doc,method):
	qty_count = 0
	for d in doc.get('delivery_note_details'):
		qty_count += d.qty
		if not d.assigned_qty>=d.qty:
			frappe.throw("Delivered Quantity must be less than or equal to assigned_qty for item_code='"+d.item_code+"'")
	doc.total_qty = qty_count

def check_uom_conversion(item):
	stock_uom=frappe.db.sql(""" select stock_uom from `tabItem` where name='%s'"""%item,as_list=1)
	if stock_uom:
		uom_details= frappe.db.sql("""select ifnull(count(idx),0) from `tabUOM Conversion Detail` where uom='%s' and parent='%s'
		"""%(stock_uom[0][0],item),as_list=1)
		if uom_details:
			if uom_details[0][0]!=1:
				return False
			else:
				return True
	else:
		return False

@frappe.whitelist()
def upload():
	if not frappe.has_permission("Attendance", "create"):
		raise frappe.PermissionError

	from frappe.utils.csvutils import read_csv_content_from_uploaded_file
	from frappe.modules import scrub

	rows = read_csv_content_from_uploaded_file()
	rows = filter(lambda x: x and any(x), rows)
	if not rows:
		msg = [_("Please select a csv file")]
		return {"messages": msg, "error": msg}
	columns = [scrub(f) for f in rows[4]]
	columns[0] = "name"
	columns[3] = "att_date"
	ret = []
	error = False

	from frappe.utils.csvutils import check_record, import_doc
	attendance_dict = attendance_rowdata = {}
	for i, row in enumerate(rows[5:]):
		if not row: continue
		row_idx = i + 5
		if row[1]:
			data = row[1]
			attendance_rowdata.setdefault(data, row)
		if data in attendance_dict:
			attendance_dict[data].append([row[8], row[9]])
		else:
			attendance_dict.setdefault(data, [[row[8], row[9]]])
	if attendance_dict and attendance_rowdata:
		for r in attendance_rowdata:
			pass
	if error:
		frappe.db.rollback()
	return {"messages": ret, "error": error}

# added by pitambar
@frappe.whitelist()
def assign_stopQty_toOther(doc,item_list):
	import json
	stopping_items=item_list
	self = frappe.get_doc('Sales Order', doc)
	for data in self.get('sales_order_details'):
		if data.item_code in (stopping_items) and data.stop_status!="Yes":			# check item code in selected stopping item
			# get the draft po
			po_qty = data.qty - (data.delivered_qty or 0)
			query = '''
						select distinct poi.parent, poi.qty from `tabPurchase Order Item` poi, `tabPurchase Order` po
						where poi.parent=po.name and po.docstatus=0 and po.status="Draft" and poi.item_code='%s'
						and poi.warehouse='%s'
					'''%(data.item_code, data.warehouse)
			results = frappe.db.sql(query)
			order = [result[0] for result in results] if results else None
			if order and len(order)==1:
				reduce_po_item(order[0], data.item_code, po_qty)
			elif order and len(order) > 1:
				frappe.throw("Multiple Draft PO (%s) present for Item %s"%(",".join(order), data.item_code))
				# what if multiple PO are in draft

			update_so_item_status(data.item_code,data.parent)
			if flt(data.qty) > flt(data.delivered_qty):
				update_bin_qty(data.item_code,data.qty,data.delivered_qty,data.warehouse)
				qty = flt(data.assigned_qty) - flt(data.delivered_qty)
				if flt(data.assigned_qty) > 0.0:
					update_sal(data.item_code, data.parent, flt(data.delivered_qty), qty)
					sales_order = get_item_SODetails(data.item_code)
					if sales_order:
						create_StockAssignment_AgainstSTopSOItem(data, sales_order, qty, reduce_po=False)
					# 	change_assigned_qty(data.item_code,data.parent,qty)
					# else:
					# 	change_assigned_qty(data.item_code,data.parent,qty)
	return "Done"

def create_StockAssignment_AgainstSTopSOItem(data, sales_order, qty, reduce_po=True):
	for so_data in sales_order:
		if flt(so_data.qty) > 0.0 and qty > 0.0:
			stock_assigned_qty = so_data.qty if flt(qty) >= flt(so_data.qty) else flt(qty)
			qty = (flt(qty) - flt(so_data.qty)) if flt(qty) >= flt(so_data.qty) else 0.0
			if flt(stock_assigned_qty) > 0.0:
				sal = frappe.db.get_value('Stock Assignment Log', {'sales_order': so_data.parent, 'item_code':data.item_code}, 'name')
				if not sal:
					sal = create_stock_assignment_document_item(data, so_data.parent, so_data.qty, stock_assigned_qty)
				else:
					sal= frappe.get_doc('Stock Assignment Log', sal)
					sal.assign_qty = cint(sal.assign_qty) + cint(stock_assigned_qty)
				make_history_of_assignment_item(sal, nowdate(), "Stock In Hand", "", stock_assigned_qty)
				sal.save(ignore_permissions=True)
				update_or_reducePoQty(so_data.parent, data.item_code, reduce_po=reduce_po)

def update_or_reducePoQty(sales_order, item_code, reduce_po=True):
	obj = frappe.get_doc('Sales Order', sales_order)
	for data in obj.get('sales_order_details'):
		if data.item_code == item_code:
			assign_qty = flt(data.qty) - flt(data.assigned_qty)
			if flt(data.po_qty) > flt(assign_qty):
				po_qty = flt(assign_qty)
			else:
				po_qty = 0.0
			frappe.db.sql(""" update `tabSales Order Item` set
				po_qty = '%s' where name ='%s'"""%(po_qty, data.name))
			if reduce_po: reduce_po_item(data.po_data, data.item_code, data.assigned_qty)

def reduce_po_item(purchase_order,item, assign_qty):
	po_details = frappe.db.get_value('Purchase Order Item', {
						'parent': purchase_order,
						'item_code': item,
						'docstatus': 0
					}, '*', as_dict=1)
	if po_details:
		update_child_table_item(po_details, assign_qty)
		update_parent_table_item(po_details)

def update_child_table_item(po_details, po_qty):
	qty = flt(po_details.qty) - po_qty
	if flt(qty) >= 1.0:
		frappe.db.sql(""" update `tabPurchase Order Item` set qty = '%s' where name ='%s'"""%(qty, po_details.name))
	elif flt(qty) <= 0.0:
		delete_document('Purchase Order Item', po_details.name)

def update_parent_table_item(po_details):
	count = frappe.db.sql(''' select ifnull(count(*),0) from `tabPurchase Order Item` where parent = "%s"	'''%(po_details.parent), as_list=1)
	if count:
		if count[0][0] == 0:
			frappe.delete_doc("Purchase Order", po_details.parent, ignore_permissions=True)

def create_stock_assignment_document_item(args, sales_order, qty, assigned_qty):
	sa = frappe.new_doc('Stock Assignment Log')
	sa.item_name = args.item_name
	sa.sales_order = sales_order
	sa.ordered_qty = qty
	sa.assign_qty = assigned_qty
	sa.purchase_receipt_no = args.parent if args.doctype == 'Purchase Receipt Item' else ''
	sa.item_code = args.item_code
	sa.media  = frappe.db.get_value("Item",args.item_code,'item_group')
	sa.customer, sa.customer_name = frappe.db.get_value('Sales Order',sa.sales_order,['customer', 'customer_name'])
	return sa

def make_history_of_assignment_item(sal, date, doc_type, pr_name, qty):
	sal_child = sal.append('document_stock_assignment', {})
	sal_child.created_date = nowdate();
	sal_child.document_type = doc_type
	sal_child.document_no = pr_name
	sal_child.qty = qty

def get_item_SODetails(item_c):
	return frappe.db.sql('''select s.parent as parent,ifnull(s.qty,0)-ifnull(s.assigned_qty,0) AS qty,
				s.assigned_qty as assigned_qty from `tabSales Order Item` s inner join `tabSales Order` so
				on s.parent=so.name where s.item_code="%s" and so.docstatus=1 and ifnull(s.stop_status, 'No') <> 'Yes' and
				ifnull(s.qty,0)>ifnull(s.assigned_qty,0) and so.status!='Stopped' order by so.priority,so.creation'''%(item_c),as_dict=1)

def update_bin_qty(item_code,qty,delivered_qty,warehouse):
	obj=frappe.get_doc("Bin",{"item_code":item_code,"warehouse":warehouse})
	obj.reserved_qty=flt(obj.reserved_qty)-(flt(qty) - flt(delivered_qty))
	obj.save(ignore_permissions=True)

def update_so_item_status(item_code,parent):
	frappe.db.sql(''' update `tabSales Order Item` set stop_status = "Yes" where item_code = "%s" and parent="%s"'''%(item_code,parent))
	frappe.db.sql(''' update `tabDelivery Note Item` set stop_status = "Yes" where item_code = "%s" and against_sales_order="%s" and docstatus<>2'''%(item_code,parent))
	frappe.db.sql(''' update `tabSales Invoice Item` set stop_status = "Yes" where item_code = "%s" and sales_order="%s" and docstatus<>2'''%(item_code,parent))

def create_StockAssignment_AgainstSTopSO(data, sales_order, qty):
	for so_data in sales_order:
		if flt(so_data.qty) > 0.0 and qty > 0.0:
			stock_assigned_qty = so_data.qty if flt(qty) >= flt(so_data.qty) else flt(qty)
			qty = (flt(qty) - flt(so_data.qty)) if flt(qty) >= flt(so_data.qty) else 0.0
			if flt(stock_assigned_qty) > 0.0:
				sal = frappe.db.get_value('Stock Assignment Log', {'sales_order': so_data.parent, 'item_code':data.item_code}, 'name')
				if not sal:
					sal = create_stock_assignment_document(data, so_data.parent, stock_assigned_qty)
				make_history_of_assignment(sal, nowdate(), "Stock In Hand", "", stock_assigned_qty)

def update_sal(item_code, sales_order, delivered_qty, assigned_qty):
	sal = frappe.db.get_value('Stock Assignment Log', {'item_code': item_code, 'sales_order': sales_order}, '*', as_dict=1)
	if sal:
		obj = frappe.get_doc('Stock Assignment Log', sal.name)
		if flt(assigned_qty) > 0.0 and delivered_qty > 0.0:
			obj.assign_qty = delivered_qty
			to_remove_obj = []
			for d in obj.get('document_stock_assignment'):
				if flt(assigned_qty) > 0:
					assigned_qty = flt(assigned_qty) - flt(d.qty)
					if flt(assigned_qty) <= 0.0:
						d.qty = assigned_qty * -1
					else:
						to_remove_obj.append(d)
			[obj.remove(d) for d in to_remove_obj]
			obj.save(ignore_permissions=True)
		else:
			frappe.db.sql(''' update `tabSales Order Item` set assigned_qty=0 where item_code ="%s"
				and parent ="%s"'''%(item_code, sales_order))
			obj.delete()

def make_csv():
	import csv
	present_list = []
	with open('/home/indictrance/Desktop/finaltryitem2.csv', 'rb') as f:
		reader = csv.reader(f)
		for item in reader:
			item_name=frappe.db.get_value('Item', item[0], 'name')
			if item_name:
				present_list.append([item_name])

def validate_sales_invoice(doc, method):
	set_terms_and_condition(doc)
	set_sales_order_details(doc)
	set_contract_details(doc)

def set_terms_and_condition(si_obj):
	si_obj.tc_name = 'Net 30' if not si_obj.tc_name else si_obj.tc_name
	if si_obj.tc_name:
		si_obj.terms = frappe.db.get_value('Terms and Conditions', si_obj.tc_name, 'terms')

def set_sales_order_details(doc):
	if doc.entries and doc.entries[0].sales_order:
		so = frappe.get_doc("Sales Order", doc.entries[0].sales_order)

		doc.po_no = so.po_no if not doc.po_no else doc.po_no
		doc.new_order_type = so.new_order_type if not doc.new_order_type else doc.new_order_type
		budget = so.budget if not doc.budget else doc.budget

def set_contract_details(doc):
	from erpnext.selling.doctype.customer.customer import get_contract_details

	contract_details = get_contract_details(doc.customer)
	doc.contract_number = contract_details.get("contract_no") if not doc.contract_number else doc.contract_number
	doc.tender_group = contract_details.get("tender_group") if not doc.tender_group else doc.tender_group

def change_assigned_qty(item_code,parent,qty):
	# frappe.db.sql(''' update `tabSales Order Item` set assigned_qty = assigned_qty - %s where item_code = "%s" and parent="%s"'''%(qty,item_code,parent))
	frappe.db.sql(''' update `tabSales Order Item` set assigned_qty = 0 where item_code = "%s" and parent="%s"'''%(item_code,parent))

@frappe.whitelist()
def get_artist(item_code):
	return frappe.db.get_value('Item', {'name':item_code}, 'artist') or ''

def set_artist(doc, method):
	for i in doc.item_details:
		art = frappe.db.get_value('Item', {'name':i.item_code}, 'artist') or ''
		i.artist=art
		
def fetch_barcode_supplier(doc, method):
	items = []

	if doc.doctype == "Sales Order":
		items = doc.sales_order_details
		if doc.budget and not doc.po_no:
			doc.po_no = frappe.db.get_value("Budget Details", {
							"parent": doc.customer,
							"budget": doc.budget
						}, "po_number") or ""

	elif doc.doctype == "Purchase Order":
		items = doc.po_details

	for item in items:
		item_details = frappe.db.get_value(
							"Item", item.item_code, 
							["barcode", "default_supplier", "product_release_date"],
							as_dict=True
						)
		item.release_date_of_item = item_details.get("product_release_date") or ""
		if doc.doctype == "Sales Order":
			item.barcode = item_details.get("barcode") or ""
			item.default_supplier = item_details.get("default_supplier") or ""

def check_and_update_status(doc, method):
	if doc.docstatus == 0 and doc.status != "Draft":
		doc.status = "Draft"

def fetch_and_set_address_display(doc, method):
	from erpnext.utilities.doctype.address.address import get_address_display

	if doc.customer_address and not doc.bill_to_address:
		doc.bill_to_address = get_address_display(doc.customer_address)

	if doc.shipping_address_name and not doc.shipping_address:
		doc.bill_to_address = get_address_display(doc.shipping_address_name)