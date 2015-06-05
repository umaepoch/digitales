from __future__ import unicode_literals
import frappe
from frappe.widgets.reportview import get_match_cond
from frappe.utils import add_days, cint, cstr, date_diff, rounded, flt, getdate, nowdate, \
	get_first_day, get_last_day,money_in_words, now, nowtime
#from frappe.utils import add_days, cint, cstr, flt, getdate, nowdate, rounded
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


# On submission of sales order---------------------------------------------------------------------------------------------------------------------------------------------------------------------
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
			else:
				bin_details = frappe.db.sql('''select sum(qty) from `tabSales Order Item` where docstatus = 1 and item_code ="%s"
					and warehouse = "%s"'''%(d.item_code, d.warehouse), as_list=1)
				so_qty = flt(bin_details[0][0]) if bin_details else 0.0
				po_qty = get_po_qty(d.item_code, d.warehouse) - so_qty # if negative then make po
				if po_qty < 0:
					create_purchase_order_record(doc,d, flt(po_qty*-1))

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
		and warehouse ="%s" and docstatus=1 and qty>=assigned_qty'''%(item_code, warehouse), as_list = 1)
	if assign_qty:
		return assign_qty[0][0] or 0.0
	return 0.0

def get_po_qty(item_code, warehouse=None):
	cond = 'warehouse ="%s"'%(warehouse) if warehouse else '1=1'
	qty = frappe.db.sql(''' select sum(ifnull(qty,0)-ifnull(received_qty,0)) from `tabPurchase Order Item` 
		where docstatus <> 2 and item_code = "%s" and %s'''%(item_code, cond), as_list=1)
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
			frappe.db.sql(''' update `tabSales Order Item` set po_data = "%s", po_qty="%s" where name = "%s"	'''%(purchase_order, qty, d.name), auto_commit=1)
	else:
		frappe.throw("Supplier must be specify for items in Item Master Form.")

def create_stock_assignment_document(args, sales_order, assigned_qty):
	sa = frappe.new_doc('Stock Assignment Log')
	sa.item_name = args.item_name
	sa.sales_order = sales_order
	sa.ordered_qty = frappe.db.get_value('Sales Order Item', {'item_code': args.item_code, 'parent': sales_order}, 'qty') if args.doctype == 'Purchase Receipt Item' else args.qty
	sa.assign_qty = assigned_qty
	sa.purchase_receipt_no = args.parent if args.doctype == 'Purchase Receipt Item' else ''
	sa.item_code = args.item_code
	sa.customer_name = frappe.db.get_value('Sales Order',sa.sales_order,'customer_name')

	# # creating Document Stock Assignment entry
	# bin_details = frappe.db.get_value('Bin', {'item_code': child_args.item_code, 'warehouse': child_args.warehouse}, '*', as_dict=1)
	# if bin_details:
	# 	bin_qty = flt(bin_details.actual_qty) - flt(bin_details.reserved_qty)
	# 	if flt(bin_qty) > 0.0 and flt(bin_details.actual_qty) >= flt(child_args.qty):
	# 		# make_history_of_assignment
	# 		sal_child = sa.append('document_stock_assignment', {})
	# 		sal_child.created_date = frappe.get_value("Sales Order",sales_order,"transcation_date")
	# 		sal_child.document_type = "Stock In Hand"
	# 		sal_child.document_no = ""
	# 		sal_child.qty = assigned_qty

	sa.save(ignore_permissions=True)
	return sa.name

def delete_stock_assignment(doc, method):
	stl = frappe.db.sql(""" select name from `tabStock Assignment Log` where sales_order = '%s'"""%(doc.name), as_dict=1) 
	if stl:
		for data in stl:
			delete_stl(data.name)
	reduce_po(doc)
	update_stock_assigned_qty_to_zero(doc)

def delete_stl(stl_name):
	frappe.db.sql(''' delete from `tabStock Assignment Log` where name="%s"	'''%(stl_name))

def update_stock_assigned_qty_to_zero(doc):
	for data in doc.get('sales_order_details'):
		frappe.db.sql(''' update `tabSales Order Item` set po_data = (select true from dual where 1=2), po_qty=0.0, assigned_qty=0.0 where name = "%s"	'''%(data.name), auto_commit=1)
		data.assigned_qty = 0.0
		data.po_data = ''
		data.po_qty = 0.0

def reduce_po(doc):
	for data in doc.get('sales_order_details'):
		if data.po_data:
			po_details = frappe.db.get_value('Purchase Order Item', {'parent': data.po_data, 'item_code': data.item_code, 'docstatus': 0}, '*', as_dict=1)
			update_child_table(po_details, data)
			update_parent_table(po_details)

def update_child_table(po_details, data):
	if po_details:
		po_qty = flt(data.po_qty) or flt(data.qty)
		qty = flt(po_details.qty) - po_qty
		if flt(qty) >= 1.0:
			frappe.db.sql(""" update `tabPurchase Order Item` set qty = '%s' where name ='%s'"""%(qty, po_details.name), auto_commit=1)
		elif flt(qty)==0.0:
			delete_document('Purchase Order Item', po_details.name)

def update_parent_table(po_details):
	if po_details:
		count = frappe.db.sql(''' select ifnull(count(*),0) from `tabPurchase Order Item` where parent = "%s"	'''%(po_details.parent), as_list=1)
		if count:
			if count[0][0] == 0:
				obj = frappe.get_doc('Purchase Order', po_details.parent)
				obj.delete()

# On submission of Purchase Receipt--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def stock_assignment(doc,method):
	for pr_details in doc.get('purchase_receipt_details'):
		if frappe.db.get_value("Item",{'is_stock_item':'Yes','name':pr_details.item_code},'name'):
			qty = flt(pr_details.qty)
			sales_order = get_SODetails(pr_details.item_code)
			if sales_order:
				check_stock_assignment(qty, sales_order, pr_details)

# So list which has stock not assign or partially assign
def get_SODetails(item_code):
	return frappe.db.sql('''select s.parent as parent,ifnull(s.qty,0)-ifnull(s.assigned_qty,0) AS qty, 
				s.assigned_qty as assigned_qty from `tabSales Order Item` s inner join `tabSales Order` so 
				on s.parent=so.name where s.item_code="%s" and so.docstatus=1 and so.status <> 'Stopped' and
				ifnull(s.qty,0)<>ifnull(s.assigned_qty,0) order by so.priority,so.creation'''%(item_code),as_dict=1)

def check_stock_assignment(qty, sales_order, pr_details):
	for so_details in sales_order:
		if flt(qty) > 0.0 and flt(so_details.qty)>0:
			stock_assigned_qty = so_details.qty if flt(qty) >= flt(so_details.qty) else flt(qty)
			qty = (flt(qty) - flt(so_details.qty)) if flt(qty) >= flt(so_details.qty) else 0.0
			create_stock_assignment(stock_assigned_qty , so_details, pr_details)

def create_stock_assignment(stock_assigned_qty, sales_order_data, pr_details):
	sal = frappe.db.get_value('Stock Assignment Log', {'sales_order': sales_order_data.parent, 'item_code': pr_details.item_code},'*', as_dict=1)
	stock_assigned_qty = sales_order_data.qty if sales_order_data.qty < stock_assigned_qty else stock_assigned_qty
	sal_name = create_stock_assignment_document(pr_details, sales_order_data.parent, stock_assigned_qty) if not sal else update_stock_assigned_qty(sal, stock_assigned_qty)

	date = frappe.db.get_value("Purchase Receipt",pr_details.parent,"posting_date")

	make_history_of_assignment(sal_name,date,"Purchase Receipt", pr_details.parent, stock_assigned_qty)

def update_stock_assigned_qty(stock_assignment_details, assigned_qty):
	frappe.db.sql(""" update `tabStock Assignment Log` set assign_qty = assign_qty + %s 
		where name = '%s' """%(flt(assigned_qty), stock_assignment_details.name), auto_commit=1)
	return stock_assignment_details.name

# def make_history_of_assignment(sal, pr_name, qty):
# 	sal= frappe.get_doc('Stock Assignment Log', sal)
# 	sal_child = sal.append('document_stock_assignment', {})
# 	sal_child.document_no = pr_name
# 	sal_child.qty = qty
# 	sal.save(ignore_permissions=True)

def make_history_of_assignment(sal, date, doc_type, pr_name, qty):
	sal= frappe.get_doc('Stock Assignment Log', sal)
	sal_child = sal.append('document_stock_assignment', {})
	sal_child.created_date = nowdate();
	sal_child.document_type = doc_type
	sal_child.document_no = pr_name
	sal_child.qty = qty
	sal.save(ignore_permissions=True)

def stock_cancellation(doc,method):
	sal_details = frappe.db.sql(''' select * from `tabDocument Stock Assignment` 
		where document_no = "%s"'''%(doc.name), as_dict=1)
	if sal_details:
		for sal in sal_details:
			obj = frappe.get_doc('Stock Assignment Log', sal.parent)
			obj.assign_qty = flt(obj.assign_qty) - flt(sal.qty)
			for d in obj.get('document_stock_assignment'):
				if d.name == sal.name:
					obj.remove(d)
			obj.save(ignore_permissions=True)

def delete_document(table, name):
	frappe.db.sql(''' delete from `tab%s` where name = "%s" '''%(table, name))

def update_so_assign_qty(args):
	so_details = frappe.db.get_value('Sales Order Item', {'parent': args.sales_order, 'item_code': args.item_code}, 'assigned_qty') or 0.0
	qty = (flt(so_details) - flt(args.qty)) if flt(so_details) >= flt(args.qty) else 0.0
	frappe.db.sql(''' update `tabSales Order Item` set assigned_qty = "%s" where parent = "%s" and 
		item_code = "%s" '''%(qty, args.sales_order, args.item_code), auto_commit=1)
			
def create_new_po(doc,d,supplier,qty):
	po = frappe.new_doc('Purchase Order')
	po.supplier= supplier
	po.currency = frappe.db.get_value('Supplier', supplier, 'default_currency')
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
	e.schedule_date=nowdate()
	po.save(ignore_permissions=True)
	return po.name
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
	poi.schedule_date=nowdate()
	doc1.save(ignore_permissions=True)
	#update_so_details(doc,d,d.item_code,doc1.name)
	
def update_qty(doc,d,item,purchase_order,qty,rate):
	amount=rate*qty
	frappe.db.sql("""update `tabPurchase Order Item` set qty='%s', amount='%s'
						where parent='%s' and item_code='%s'"""
							%(qty,amount,purchase_order,item))

	frappe.db.commit()
	#update_so_details(doc,d,item,purchase_order)

def update_so_details(doc,d,item,purchase_order):
	doc2 = frappe.get_doc("Purchase Order", purchase_order)
	so = doc2.append('so_item_detail', {})
	so.item_code=item
	so.qty=d.qty
	so.sales_order_name=doc.name
	doc2.save(ignore_permissions=True)
	

# On sibmission of delivery Note---------------------------------------------------------------------------------------------------------------------------------
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
				frappe.db.commit()
			else:
				# delivery_note = delivery_note_name[0][0] + ', ' + doc.name
				delivery_note = doc.name
				delivery_note_details=frappe.db.sql("""select delivered_qty from `tabStock Assignment Log`
												where sales_order='%s' and item_code='%s'"""%(sales_order_name[0][0],d.item_code))
				if delivery_note_details:
					qty=cint(delivery_note_details[0][0])+d.qty
					frappe.db.sql("""update `tabStock Assignment Log` 
								set delivered_qty='%s', delivery_note='%s'
									where sales_order='%s' and item_code='%s'"""
										%(qty,delivery_note,sales_order_name[0][0],d.item_code))
					frappe.db.commit()


def update_stock_assignment_log_on_cancel(doc,method):
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
					frappe.db.commit()


def validate_qty_on_submit(doc,method):
	qty_count = 0
	for d in doc.get('delivery_note_details'):
		qty_count += d.qty
		if not d.assigned_qty>=d.qty:
			frappe.throw("Delivered Quantity must be less than or equal to assigned_qty for item_code='"+d.item_code+"'")
	doc.total_qty = qty_count


#For calling API through Poster---------------------------------------------------------------------------------------
def check_APItime():
	# sync_existing_customers_address()
	time = frappe.db.sql("""select value from `tabSingles` where doctype='API Configuration Page' and field in ('date','api_type')""",as_list=1)
	if time:
		dates= list(itertools.chain.from_iterable(time))
		api_configured_date = dates[1].split('.')[0] if '.' in dates[1] else dates[1]
		api_date=datetime.datetime.strptime(api_configured_date , '%Y-%m-%d %H:%M:%S')
		if datetime.datetime.now() > api_date and dates[0] =='Product':
			GetItem()
		elif datetime.datetime.now() > api_date and dates[0]=='Customer':
			GetCustomer()
		elif datetime.datetime.now() > api_date and dates[0]=='Order':
			GetOrders()

def get_Data_count(max_date, document_key, headers, oauth_data):
	r = requests.get(url='http://digitales.com.au/api/rest/mcount?start_date='+cstr(max_date)+'', headers=headers, auth=oauth_data)
	total_page_count = json.loads(r.content)
	if total_page_count.get(document_key) > 0:
		return total_page_count.get(document_key)
	return 0

#Get Item from magento------------------------------------------------------------------------------------------------------------------------------------
def GetItem():
	update_execution_date('Customer')
	h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
	oauth = GetOauthDetails()
	max_item_date = '1991-09-07 05:43:13'
	max_date = frappe.db.sql(""" select max(modified_date) as max_date from `tabItem` """,as_list=1)
	if max_date[0][0]!=None:
		max_item_date = max_date[0][0]
	max_item_date = max_item_date.split('.')[0] if '.' in max_item_date else max_item_date
	max_item_date = (datetime.datetime.strptime(max_item_date, '%Y-%m-%d %H:%M:%S') - datetime.timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')
	status = get_SyncItemsCount(max_item_date, h, oauth)		
	
def get_SyncItemsCount(max_date, header, oauth_data):
	count = get_Data_count(max_date, 'product_pages_per_100_mcount', header, oauth_data)
	count = 25 if count > 30 else count 
	if count > 0:
		for index in range(1, count+1):
			get_products_from_magento(index, max_date,header, oauth_data)

def get_products_from_magento(page, max_date, header, oauth_data):
	if page:
		r = requests.get(url='http://digitales.com.au/api/rest/products?filter[1][attribute]=updated_at&filter[1][gt]=%s&page=%s&limit=100&order=updated_at&dir=asc'%(max_date, page), headers=header, auth=oauth_data)
		product_data = json.loads(r.content)
		if len(product_data) > 0:
			for index in product_data:
				name = frappe.db.get_value('Item', product_data[index].get('sku'), 'name')
				if name:
					update_item(name, index, product_data)
					check_item_price(name,index,product_data)
				else:
					create_item(index, product_data)
	return True

def create_item(i,content):
	try:
		item = frappe.new_doc('Item')
		item.item_code = content[i].get('sku')
		create_new_product(item,i,content)
		item.save(ignore_permissions=True)	
		check_item_price(item.name,i,content)
	except Exception, e:
		create_scheduler_exception(e , 'create_item ', content[i])

def update_item(name,i,content):
	try:
		item = frappe.get_doc("Item", name)
		create_new_product(item,i,content)
		item.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e , 'method name update_item: ' ,content[i])		

def check_item_price(name,i,content):
	if content[i].get('price'):
		price_list=get_price_list()
		if price_list:
			item_price_list_name=frappe.db.get_value('Item Price',{'item_code':name,'price_list':price_list},'name')
			if item_price_list_name:
				update_price_list(item_price_list_name,i,content,price_list)
			else:
				create_price_list(name,i,content,price_list)

def get_price_list():
		price_list=frappe.db.sql("""select value from `tabSingles` where doctype='Configuration Page'
					and field='price_list'""",as_list=1)
		if price_list:
			return price_list[0][0]
		else:
			frappe.msgprint("Please specify default price list in Configuration Page",raise_exception=1)

def update_price_list(price_list_name,i,content,price_list):
	try:
		item_price = frappe.get_doc("Item Price", price_list_name)
		create_new_item_price(item_price,i,content,price_list)
		item_price.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e , 'method name update_price_list: ' , content[i])

def create_price_list(item,i,content,price_list):
	try:
		item_price=frappe.new_doc("Item Price")
		create_new_item_price(item_price,i,content,price_list)
		item_price.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e , 'method name create_price_list: ' ,content[i])

def create_new_item_price(item_price,i,content,price_list):
	item_price.price_list=price_list
	item_price.item_code=content[i].get('sku')
	item_price.price_list_rate=content[i].get('price')
	return True

def create_new_product(item,i,content):
	item.event_id=i
	item.item_name=content[i].get('name') or content[i].get('sku')
	item.item_group = media_type(content[i].get('media'))
	item.description = 'Desc: ' + content[i].get('short_description') if content[i].get('short_description') else content[i].get('sku')
	warehouse=get_own_warehouse()
	item.default_warehouse=warehouse
	if content[i].get('barcode') and not frappe.db.get_value('Item', {'barcode':content[i].get('barcode')}, 'name'):	
		item.barcode = content[i].get('barcode')
	item.modified_date = content[i].get('updated_at')
	item.distributor = content[i].get('distributor')
	item.product_release_date = content[i].get('release_date')
	item.default_supplier = get_supplier(content[i].get('distributor'))
	item.expense_account, item.income_account = default_ExpenxeIncomeAccount(item.item_group)
	return True

def media_type(itemgroup):
	media = 'Products'
	if itemgroup:
		media = itemgroup
		media = media.split(',')[0]
		if not frappe.db.get_value('Item Group', media, 'name'):
			create_new_itemgroup(media)
	return media

def default_ExpenxeIncomeAccount(media):
	# Check item group and assign the default expence and income account
	expense_account, income_account = '', ''
	if media in ['DVD', 'CD', 'BLURAY', 'Graphic Novel', 'CDROM', 'Audio Book', 'Manga',
				'Online Resource', 'Blu-Ray', 'PC Games', 'Hardcover', 'Playstation 3',
				'Xbox 360', 'Xbox One', 'Playstation 4', 'Nintendo Wii U', '2CD and DVD',
				'Graphics', '3D', 'UV', 'BLURAY, 3D', 'Nintendo 3DS', 'Nintendo Wii', 'DVD, UV',
				'BLURAY, DVD', 'BLURAY, DVD, UV', 'Playstation Vita', 'Paperback']:
		expense_account = "5-1100 Cost of Goods Sold : COGS Stock"
		income_account = "4-1100 Product Sales"

	return expense_account, income_account

def get_supplier(supplier):
	temp = ''
	if supplier:
		if frappe.db.get_value('Customer', supplier, 'name'):
			supplier = supplier + '(s)'
			temp = supplier
		name = supplier if frappe.db.get_value('Supplier', supplier, 'name') else create_supplier(supplier)
		if temp:
			update_supplier(supplier)
		return name
	return ''

def update_supplier(supplier):
	try:
		obj = frappe.get_doc('Supplier', supplier)
		obj.supplier_name = supplier.replace('(s)', '')
		obj.save(ignore_permissions=True)
	except Exception,e:
		create_scheduler_exception(e , 'method name update_supplier: ' ,supplier)
	return True

def create_supplier(supplier):
	try:
		sl = frappe.new_doc('Supplier')
		sl.supplier_name = supplier
		sl.supplier_type = 'Stock supplier' if frappe.db.get_value('Supplier Type', 'Stock supplier', 'name') else create_supplier_type()
		sl.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e , 'method name create_supplier: ' , supplier)	
	return sl.name

def create_supplier_type():
	try:
		st = frappe.new_doc('Supplier Type')
		st.supplier_type = 'Stock supplier'
		st.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e, 'method name create_supplier_type: ' , 'supplier type')
	return st.name	

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

# def create_new_itemgroup(i,content):
# 	try:
# 		itemgroup=frappe.new_doc('Item Group')
# 		itemgroup.parent_item_group='All Item Groups'
# 		itemgroup.item_group_name=content[i].get('media')
# 		itemgroup.is_group='No'
# 		itemgroup.save()
# 	except Exception, e:
# 		create_scheduler_exception(e , 'method name create_new_itemgroup: ' , content[i])
# 	return itemgroup.name or 'Products'

def create_new_itemgroup(item_group):
	try:
		itemgroup=frappe.new_doc('Item Group')
		itemgroup.parent_item_group='All Item Groups'
		itemgroup.item_group_name=item_group
		itemgroup.is_group='No'
		itemgroup.save()
	except Exception, e:
		create_scheduler_exception(e , 'method name create_new_itemgroup: ' , item_group)
	return itemgroup.name or 'Products'

def get_own_warehouse():
	warehouse=frappe.db.sql("""select value from `tabSingles` where doctype='Configuration Page'
				and field='own_warehouse'""",as_list=1)
	if warehouse:
		return warehouse[0][0]
	else:
		frappe.msgprint("Please specify default own warehouse in Configuration Page",raise_exception=1)

def GetOauthDetails():
	try:
		oauth_details = frappe.db.get_value('API Configuration Page', None, '*', as_dict=1)
		oauth=OAuth(client_key=oauth_details.client_key, client_secret=oauth_details.client_secret, resource_owner_key= oauth_details.owner_key, resource_owner_secret=oauth_details.owner_secret)	
		return oauth
	except Exception, e:
		create_scheduler_exception(e , 'method name GetOauthDetails: ' , 'oauth_details')	

#update configuration
def update_execution_date(document):
	now_plus_10 = datetime.datetime.now() + datetime.timedelta(minutes = 30)
	frappe.db.sql("""update `tabSingles` set value='%s' where doctype='API Configuration Page' and field='date'"""%(now_plus_10.strftime('%Y-%m-%d %H:%M:%S')))
	frappe.db.sql("""update `tabSingles` set value='%s' where doctype='API Configuration Page' and field='api_type'"""%(document))
	frappe.db.commit()

def GetCustomer():
	update_execution_date('Order')
	h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
	oauth = GetOauthDetails()
	max_customer_date = '1988-09-07 05:43:13'
	max_date = frappe.db.sql(""" select max(modified_date) as max_date from `tabCustomer` """,as_list=1)
	if max_date[0][0]!=None:
		max_customer_date = max_date[0][0]
	max_customer_date = max_customer_date.split('.')[0] if '.' in max_customer_date else max_customer_date
	max_customer_date = (datetime.datetime.strptime(max_customer_date, '%Y-%m-%d %H:%M:%S') - datetime.timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')
	status=get_SyncCustomerCount(max_customer_date, h, oauth)	

def get_SyncCustomerCount(max_date, header, oauth_data):
	count = get_Data_count(max_date, 'customer_pages_per_100_mcount', header, oauth_data)
	count = 25 if count > 30 else count 
	if count > 0:
		for index in range(1, count+1):
			get_customers_from_magento(index, max_date,header, oauth_data, 'missed')

def get_customers_from_magento(page, max_date, header, oauth_data,type_of_data=None):
	try:
		if page:
			r = requests.get(url='http://digitales.com.au/api/rest/customers?filter[1][attribute]=updated_at&filter[1][gt]=%s&page=%s&limit=100&order=updated_at&dir=asc'%(max_date, page), headers=header, auth=oauth_data)
			customer_data = json.loads(r.content)
			if len(customer_data) > 0:
				for index in customer_data:
					name = frappe.db.get_value('Customer', customer_data[index].get('organisation').replace("'",""), 'name')
					if name:
						update_customer(name, index, customer_data)
						GetAddress(customer_data[index].get('entity_id'))
					else:
						create_customer(index, customer_data)
						GetAddress(customer_data[index].get('entity_id'))
	except Exception, e:
		create_scheduler_exception(e , 'Method name get_customers_from_magento' , customer_data[index].get('organisation'))

def create_customer(i,content):
	temp_customer = ''
	customer = frappe.new_doc('Customer')
	if frappe.db.get_value('Supplier',content[i].get('organisation').replace("'",""),'name') or frappe.db.get_value('Customer Group',content[i].get('organisation').replace("'",""),'name'):
		temp_customer= customer.customer_name = cstr(content[i].get('organisation')).replace("'","") + '(C)'
	else:
		customer.customer_name=cstr(content[i].get('organisation')).replace("'","") 
	if not frappe.db.get_value('Customer', customer.customer_name, 'name'):
		create_new_customer(customer,i,content)
	create_contact(customer,i,content)
	if temp_customer:
		update_customer_name(temp_customer)

def update_customer_name(customer_name):
	try:
		customer = frappe.get_doc("Customer", customer_name)
		customer.customer_name= customer_name.replace("(C)","")
		customer.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e , 'Method name update_customer_name: ' , customer_name)

def update_customer(customer,i ,content):
	customer = frappe.get_doc("Customer", customer)
	create_new_customer(customer,i,content)
	contact=frappe.db.sql("""select name from `tabContact` where entity_id='%s'"""%content[i].get('entity_id'),as_list=1)
	if contact:
		update_contact(customer,i,content,contact[0][0])
	else:
		create_contact(customer,i,content)

def update_contact(customer,i,content,contact):
	contact = frappe.get_doc("Contact", contact)
	create_customer_contact(customer,i,content,contact)

def create_contact(customer,i,content):
	contact=frappe.new_doc('Contact')
	if not frappe.db.get_value('Contact', {'entity_id':content[i].get('entity_id')}, 'name'):
		create_customer_contact(customer,i,content,contact)

def create_new_customer(customer,i,content):
	import itertools
	try:
		customer.entity_id = content[i].get('entity_id') 
		customer.customer_type = 'Company'
		if content[i].get('group'):
			if content[i].get('group').strip() == 'General':
				customer.customer_group= 'All Customer Groups'
			elif frappe.db.get_value('Customer Group', content[i].get('group').strip(), 'name'):
				customer.customer_group=content[i].get('group').strip() or 'All Customer Groups'
			elif frappe.db.get_value('Customer', content[i].get('group').strip(), 'name'):
				customer.customer_group = 'All Customer Groups'
			else:
				customer_group=create_customer_group(content[i].get('group').strip())
				customer.customer_group=customer_group
		customer.territory = 'Australia'
		customer.customer_status = 'Existing'
		customer.modified_date=content[i].get('updated_at')
		customer.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e , 'Method name create_new_customer: ', content[i])
	
def create_customer_contact(customer,i,content,contact):
	try:
		if content[i].get('firstname'):
			contact.first_name=content[i].get('firstname')
			contact.last_name=content[i].get('lastname')
			contact.customer= customer.name
			contact.customer_name=customer.customer_name
			contact.entity_id = content[i].get('entity_id')
			contact.email_id=content[i].get('email')
			contact.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e , 'Method name create_customer_contact: ', content[i])

def create_new_contact(customer,i,content):
	try:
		contact=frappe.new_doc('Contact')
		if content[i].get('firstname'):
			contact.first_name=content[i].get('firstname')
			contact.last_name=content[i].get('lastname')
			contact.customer= customer
			contact.customer_name=customer
			contact.entity_id = content[i].get('entity_id')
			contact.email_id=content[i].get('email')
			contact.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e , 'Method name create_new_contact: ', content[i])

def create_customer_group(i):
	try:
		cg=frappe.new_doc('Customer Group')
		cg.customer_group_name = i
		cg.parent_customer_group='All Customer Groups'
		cg.is_group='No'
		cg.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e , 'Method name create_customer_group: ', i)
	return cg.name or 'All Customer Group'

def sync_existing_customers_address():
	offset = frappe.db.get_value('API Configuration Page', None, 'offset_limit')
	if offset:
		customer_data = frappe.db.sql(''' Select entity_id from tabContact order by creation limit %s, 100'''%(offset), as_dict=1)
		frappe.db.sql(''' update `tabSingles` set value = "%s" where doctype = "API Configuration Page" and field="offset_limit"'''%(cint(offset)+100), auto_commit =True)
		if customer_data:
			for data in customer_data:
				GetAddress(data.entity_id)

def GetAddress(entity_id):
	try:
		h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
		oauth = GetOauthDetails()
		customer=frappe.db.get_value('Contact',{'entity_id':entity_id},'customer')
		if customer:
			r = requests.get(url='http://digitales.com.au/api/rest/customers/%s/addresses'%(entity_id), headers=h, auth=oauth)
			cust_address_data=json.loads(r.content)
			if cust_address_data:
				for data in cust_address_data:
					address_entity_id = data.get('entity_id')
					address_name = frappe.db.get_value('Address', {'entity_id': address_entity_id}, 'name')
					if not address_name:
						create_new_address(data, customer)
					else:
						update_customer_address(data, address_name, customer)
	except Exception, e:
		create_scheduler_exception(e, 'Get Address', entity_id)

def create_scheduler_exception(msg, method, obj=None):
	se = frappe.new_doc('Scheduler Log')
	se.method = method
	se.error = msg
	se.obj_traceback = cstr(obj)
	se.save(ignore_permissions=True)

def create_new_address(data, customer):
	try:
		obj = frappe.new_doc('Address')
		obj.address_title = cstr(data.get('firstname'))+' '+cstr(data.get('lastname')) +' '+cstr(data.get('entity_id'))
		customer_address(data, obj, customer)
		obj.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e, 'create_new_address', customer)

def update_customer_address(data, address_name, customer):
	try:
		obj = frappe.get_doc('Address', address_name)
		customer_address(data, obj, customer)
		obj.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e ,'Method name update_customer_address: ', customer)

def customer_address(data, obj, customer):
	obj.address_type = get_address_type(data).get('type') # Address Type is Billing or is Shipping??
	obj.entity_id = cstr(data.get('entity_id'))
	obj.address_line1 = cstr(data.get('street')[0])
	obj.address_line2 = cstr(data.get('street')[1]) if len(data.get('street')) > 1 else ""
	obj.city = cstr(data.get('city'))
	obj.country = frappe.db.get_value('Country', {'code': data.get('country_id')}, 'name')
	obj.state = cstr(data.get('region'))
	obj.pincode = cstr(data.get('postcode'))
	obj.phone = cstr(data.get('telephone')) or '00000'
	obj.fax = cstr(data.get('fax'))
	obj.customer = customer
	obj.is_primary_address = get_address_type(data).get('is_primary_address')
	obj.is_shipping_address = get_address_type(data).get('is_shipping_address')

def get_address_type(content):
	if content.get('is_default_billing'):
		return {"type":"Billing", "is_primary_address":1, "is_shipping_address":0}
	elif content.get('is_default_shipping'):
		return {"type":"Shipping", "is_primary_address":0, "is_shipping_address":1}
	else:
		return {"type":"Other", "is_primary_address":0, "is_shipping_address":0}



#Get Order data API
def GetOrders():
	update_execution_date('Product')
	h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
	oauth = GetOauthDetails()
	max_order_date = '2001-09-07 05:43:13'
	max_date = frappe.db.sql(""" select max(modified_date) as max_date from `tabSales Order` """,as_list=1)
	if max_date[0][0]!=None:
		max_order_date = max_date[0][0]
	max_order_date = max_order_date.split('.')[0] if '.' in max_order_date else max_order_date
	max_order_date = (datetime.datetime.strptime(max_order_date, '%Y-%m-%d %H:%M:%S') - datetime.timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')
	status=get_SyncOrdersCount(max_order_date, h, oauth)

def get_SyncOrdersCount(max_date, header, oauth_data):
	count = get_Data_count(max_date, 'orders_pages_per_100_mcount', header, oauth_data)
	count = 25 if count > 30 else count
	if count > 0:
		for index in range(1, count+1):
			get_orders_from_magento(index, max_date,header, oauth_data, 'missed')	


addr_details = {}

def get_orders_from_magento(page, max_date, header, oauth_data,type_of_data=None):
	if page:
		r = requests.get(url='http://digitales.com.au/api/rest/orders?filter[1][attribute]=updated_at&filter[1][gt]=%s&page=%s&limit=100&order=updated_at&dir=asc'%(max_date, page), headers=header, auth=oauth_data)
		order_data = json.loads(r.content)
		if len(order_data) > 0:
			for index in order_data:
				customer = frappe.db.get_value('Contact', {'entity_id': order_data[index].get('customer_id')}, 'customer')
				if customer:
					# create_or_update_customer_address(order_data[index].get('addresses'), customer)
					order = frappe.db.get_value('Sales Order', {'entity_id': order_data[index].get('entity_id')}, 'name')
					if not order:
						create_order(index,order_data,customer)
	return True

def create_or_update_customer_address(address_details, customer):
	address_type_mapper = {'billing': 'Billing', 'shipping': 'Shipping'}
	if address_details:
		for address in address_details:
			address_type = address_type_mapper.get(address.get('address_type'))
			if not frappe.db.get_value('Address',{'address_title': address.get('firstname') +' '+address.get('lastname') +' '+address.get('street'), 'address_type': address_type},'name'):
				create_address_forCustomer(address, customer, address_type)
			else:
				cust_address=frappe.db.get_value('Address',{'address_title': address.get('firstname') +' '+address.get('lastname') +' '+address.get('street'), 'address_type': address_type},'name')
				update_address_forCustomer(cust_address,address,customer,address_type)

def create_address_forCustomer(address_details, customer, address_type):
	try:
		cad = frappe.new_doc('Address')
		cad.address_title = address_details.get('firstname')+' '+address_details.get('lastname') +' '+address_details.get('street')
		cad.address_type = address_type
		cad.address_line1 = address_details.get('street')
		cad.city = address_details.get('city')
		cad.state = address_details.get('region')
		cad.pincode = address_details.get('postcode')
		cad.phone = address_details.get('telephone') or '00000'
		cad.customer = customer
		cad.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e , 'Method name create_address_forCustomer: ' , customer)

def update_address_forCustomer(cust_address,address_details, customer, address_type):
	try:
		cad = frappe.get_doc('Address',cust_address)
		cad.address_type = address_type
		cad.address_line1 = address_details.get('street')
		cad.city = address_details.get('city')
		cad.state = address_details.get('region')
		cad.pincode = address_details.get('postcode')
		cad.phone = address_details.get('telephone') or '00000'
		cad.customer = customer
		cad.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e , 'Method name update_address_forCustomer: ', customer)

def get_missing_customers(header,oauth_data):
	list1=[]
	order=[]
	for i in range(1,4):
		r = requests.get(url='http://digitales.com.au/api/rest/orders?&page='+cstr(i)+'&limit=100',headers=header, auth=oauth_data)
		order_data = json.loads(r.content)
		for index in order_data:
			if not frappe.db.get_value('Contact',{'entity_id':order_data[index].get('customer_id')},'name'):
				list1.append(order_data[index].get('customer_id'))
				order.append(order_data[index].get('entity_id'))

def get_missing_products(header,oauth_data):
	list2=[]
	order1=[]
	for i in range(1,4):
		r = requests.get(url='http://digitales.com.au/api/rest/orders?&page='+cstr(i)+'&limit=100',headers=header, auth=oauth_data)
		order_data = json.loads(r.content)
		for index in order_data:
			if order_data[index].get('order_items'):
				for i in order_data[index].get('order_items'):
					if not frappe.db.get_value('Item',i.get('sku'),'name'):
						list2.append(i.get('sku'))
						order1.append(order_data[index].get('entity_id'))

def update_order(order,i,content,customer):
	try:
		order = frappe.get_doc("Sales Order", order)
		create_new_order(order,i,content,customer)
		order.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e , 'Method name update_order: ', content[i])

def create_order(i,content,customer):
	try:
		if content[i].get('order_items'):
			child_status=check_item_presence(i,content)
			if child_status==True:
				order = frappe.new_doc('Sales Order')
				create_new_order(order,i,content,customer)
				order.save(ignore_permissions=True)
	except Exception, e:
		create_scheduler_exception(e ,'Method name create_order: ', content[i])

# def create_new_order(order,i,content,customer):
# 	from datetime import date
# 	from dateutil.relativedelta import relativedelta
# 	delivery_date = date.today() + relativedelta(days=+6)
# 	order.customer=customer
# 	order.entity_id=content[i].get('entity_id')
# 	order.modified_date=content[i].get('updated_at')
# 	order.delivery_date=delivery_date
# 	order.grand_total_export=content[i].get('grand_total')
# 	#order.discount_amount=content[i].get('discount_amount')
# 	if content[i].get('po_number'):
# 		order.po_no=content[i].get('po_number')
# 	order.order_type=content[i].get('order_type')
# 	for i in content[i].get('order_items'):
#  		create_child_item(i,order)

#  	# # set shipping and billing address
#  	# set_sales_order_address(content[i].get('addresses'))

# Makarand
def create_new_order(order,index,content,customer):
	from datetime import date
	from dateutil.relativedelta import relativedelta
	delivery_date = date.today() + relativedelta(days=+6)
	order.customer=customer
	order.entity_id=content[index].get('entity_id')
	order.modified_date=content[index].get('updated_at')
	order.delivery_date=delivery_date
	order.grand_total_export=content[index].get('grand_total')
	#order.discount_amount=content[i].get('discount_amount')
	if content[index].get('po_number'):
		order.po_no=content[index].get('po_number')
	
	# If Order type is general then set SO order type as Standard Order
	if content[index].get('order_type') == "General" or content[index].get('order_type') == None:
		order.new_order_type="Standard Order"
	else:
		order.new_order_type=content[index].get('order_type')
	for i in content[index].get('order_items'):
 		create_child_item(i,order)

 	# # set shipping and billing address
 	set_sales_order_address(content[index].get('addresses'),order)

def set_sales_order_address(address_details, order):
	# Check if Address is available if it is then set addr id in SO else set None
	address_type_mapper = {'billing': 'Billing', 'shipping': 'Shipping'}
	if address_details:
		for address in address_details:
			addr_filter = {'entity_id': cstr(address.get('customer_address_id'))}
			cust_address = frappe.db.get_value('Address',addr_filter,'name')
			if cust_address:
				# Check the address type if billing the set to billing addr likewise for shipping
				if cstr(address.get('address_type')) == "billing":
					order.customer_address = frappe.db.get_value('Address',{'entity_id':cust_address},'name')
				if cstr(address.get('address_type')) == "shipping":
					order.shipping_address_name = frappe.db.get_value('Address',{'entity_id':cust_address},'name')

def check_item_presence(i,content):
	for i in content[i].get('order_items'):
		if not frappe.db.get_value('Item',i.get('sku'),'name'):
			return False

	return True	
	
def create_child_item(i,order):
	oi = order.append('sales_order_details', {})
	oi.item_code=i['sku']
	if i['sku']:
		item_release_date=frappe.db.sql("""select product_release_date from `tabItem`
								where name='%s'"""%i['sku'],as_list=1)
		if item_release_date:
			oi.release_date_of_item=item_release_date[0][0]
	oi.qty=i['qty_ordered']
	oi.rate=i['price']
	oi.amount=i['row_total_incl_tax']
	return True


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
	else:
		frappe.db.commit()
	return {"messages": ret, "error": error}

@frappe.whitelist()
def assign_stopQty_toOther(doc):
	import json
	self = frappe.get_doc('Sales Order', doc)
	for data in self.get('sales_order_details'):
		qty = flt(data.assigned_qty) - flt(data.delivered_qty)
		if flt(data.assigned_qty) > 0.0:
			update_sal(data.item_code, data.parent, flt(data.delivered_qty), qty)
			sales_order = get_SODetails(data.item_code)
			if sales_order:
				create_StockAssignment_AgainstSTopSO(data, sales_order, qty)
	return "Done"

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
			obj.delete()

def execute():
	missed_so_list = ['276','277','278','279']
	for entity_id in missed_so_list:
		header = {'Content-Type': 'application/json', 'Accept': 'application/json'}
		oauth_data = GetOauthDetails()
		r = requests.get(url='http://digitales.com.au/api/rest/orders?filter[1][attribute]=entity_id&filter[1][in]=%s&page=1&limit=1&order=updated_at&dir=asc'%(entity_id), headers=header, auth=oauth_data)
		order_data = json.loads(r.content)
		if len(order_data) > 0:
			for index in order_data:
				customer = frappe.db.get_value('Contact', {'entity_id': order_data[index].get('customer_id')}, 'customer')
				if customer:
					# create_or_update_customer_address(order_data[index].get('addresses'), customer)
					order = frappe.db.get_value('Sales Order', {'entity_id': order_data[index].get('entity_id')}, 'name')
					if not order:
						create_order(index,order_data,customer)