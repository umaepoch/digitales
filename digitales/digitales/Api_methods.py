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
	check_ispurchase_item(doc,method)

def check_ispurchase_item(doc,method):
	for d in doc.get('sales_order_details'):
		if frappe.db.get_value("Item",{'is_purchase_item':'Yes','name':d.item_code},'name'):
			if frappe.db.get_value("Item",{'is_stock_item':'Yes','name':d.item_code},'name'):
				check_stock_availability(doc,d)
			else:
				create_purchase_order_record(doc,d,d.qty)


def check_stock_availability(doc,d):
	Quantities=frappe.db.sql("""select actual_qty,ordered_qty,reserved_qty from `tabBin` 
								where item_code='%s' and warehouse='%s'"""%(d.item_code,d.warehouse),as_list=1)
	draft_po_qty=frappe.db.sql("""select ifnull(sum(p.qty),0) as qty 
									from `tabPurchase Order Item` p inner join `tabPurchase Order` po 
										on p.parent=po.name where p.item_code='%s' and p.warehouse='%s' and po.docstatus=0"""
										%(d.item_code,d.warehouse),as_list=1)
	if Quantities and draft_po_qty:
		available_qty=(Quantities[0][0]+Quantities[0][1]-Quantities[0][2]+draft_po_qty[0][0])
		actual_qty = Quantities[0][0] or 0.0

		if available_qty>0:
			if d.qty==available_qty:		# que?should be less than equal to
				create_stock_assignment_document(d,doc.name,d.qty,d.qty)
				update_assigned_qty(d.qty,doc.name,d.item_code)
			elif d.qty>available_qty:
				qty_ordered=d.qty-available_qty
				create_stock_assignment_document(d,doc.name,d.qty,available_qty)
				update_assigned_qty(available_qty,doc.name,d.item_code)
				create_purchase_order_record(doc,d,qty_ordered)
			elif d.qty<available_qty:
				# if actual quantity is zero or less than orderd qty then create purchase order
				if d.qty > actual_qty:
					qty_order = d.qty - actual_qty
					create_purchase_order_record(doc,d,qty_order)
					# assign the actual qty
					create_stock_assignment_document(d,doc.name,d.qty, actual_qty)
					update_assigned_qty(d.qty,doc.name,d.item_code)

				# else create stock assignment
				else:
					create_stock_assignment_document(d,doc.name,d.qty,d.qty)
					update_assigned_qty(d.qty,doc.name,d.item_code)
				

		elif available_qty==0:
			create_purchase_order_record(doc,d,d.qty)
		elif available_qty<0:
			# if actual quantity is zero or less than orderd qty then create purchase order
			if d.qty > actual_qty:
				qty_order = d.qty - actual_qty
				create_purchase_order_record(doc,d,qty_order)
				# assign the actual qty
				create_stock_assignment_document(d,doc.name,d.qty, actual_qty)
				update_assigned_qty(d.qty,doc.name,d.item_code)

			# else create stock assignment
			else:
				create_stock_assignment_document(d,doc.name,d.qty,d.qty)
				update_assigned_qty(d.qty,doc.name,d.item_code)


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

						qty_new=qty+purchase_order_qty[0][0]
				 		update_qty(doc,d,item[0],purchase_order[0][0],qty_new,purchase_order_qty[0][1])			 		
					else:
						child_entry=update_child_entry(doc,d,purchase_order[0][0],qty)
			else:
				child_entry=update_child_entry(doc,d,purchase_order[0][0],qty)
		else:
			create_new_po(doc,d,supplier[0][0],qty)
	else:
		frappe.throw("Supplier must be specify for items in Item Master Form.")


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
	e.schedule_date=nowdate()
	po.save(ignore_permissions=True)
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
							%(qty,amount,purchase_order,item),debug=1)

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
	for d in doc.get('purchase_receipt_details'):
		if frappe.db.get_value("Item",{'is_stock_item':'Yes','name':d.item_code},'name'):
			sales_order=frappe.db.sql("""select s.parent,s.qty-s.assigned_qty as qty from `tabSales Order Item` s 
										inner join `tabSales Order` so on s.parent=so.name 
										 where s.item_code='%s' and so.docstatus=1 and 
										 s.qty!=s.assigned_qty and so.delivery_status='Not Delivered' 
										 or so.delivery_status='Partly Delivered' order by 
										 so.priority,so.creation"""%d.item_code,as_list=1)
			qty=d.qty
			if sales_order:
				for i in sales_order:
					assigned_qty=frappe.db.sql(""" select ifnull(assigned_qty,0) from `tabSales Order Item` 
													where parent='%s' and item_code='%s'"""
														%(i[0],d.item_code),as_list=1)
					if assigned_qty:
						
						if qty>0 and i[1]>0:
							if qty>=i[1]:
								qty=qty-i[1]
								
								assigned_qty=(assigned_qty[0][0]+i[1])
								update_assigned_qty(assigned_qty,i[0],d.item_code)				
								create_stock_assignment(d,i[0],i[1],i[1])
							else:
								assigned_qty=flt(assigned_qty[0][0]+qty)
								update_assigned_qty(assigned_qty,i[0],d.item_code)
								create_stock_assignment(d,i[0],i[1],qty)
								qty=0.0
		else:
			pass

def update_assigned_qty(assigned_qty,sales_order,item_code):
	frappe.db.sql("""update `tabSales Order Item` 
						set assigned_qty='%s' where parent='%s' 
							and item_code='%s'"""%
								(assigned_qty,sales_order,item_code))
	frappe.db.commit()

def create_stock_assignment(d,sales_order,ordered_qty,assigned_qty):
	stock_assignment=frappe.db.sql("""select name from `tabStock Assignment Log` where 
									sales_order='%s' and item_code='%s'"""
									%(sales_order,d.item_code))
	if stock_assignment:
		ass_qty= frappe.db.sql(""" select assigned_qty from `tabStock Assignment Log`
			     where name='%s'"""%stock_assignment[0][0])
		qty=assigned_qty+ass_qty[0][0]
		frappe.db.sql("""update `tabStock Assignment Log` set
					    sales_order='%s',assigned_qty='%s'
						where name='%s'"""
						%(sales_order,qty,stock_assignment[0][0]))
		frappe.db.commit()

	else:
		create_stock_assignment_document(d,sales_order,ordered_qty,assigned_qty)

def create_stock_assignment_document(d,sales_order,ordered_qty,assigned_qty):
	sa = frappe.new_doc('Stock Assignment Log')
	#sa.purchase_receipt=purchase_receipt
	sa.item_name=d.item_name
	sa.sales_order=sales_order
	sa.ordered_qty=ordered_qty
	sa.assign_qty=assigned_qty
	sa.item_code=d.item_code
	sa.save(ignore_permissions=True)

	
def stock_cancellation(doc,method):
	delivered_note=frappe.db.sql("""select delivery_note from `tabStock Assignment Log`
										where purchase_receipt='%s' and delivery_note is not null"""
										%doc.name,as_list=1)
	if not delivered_note:
		pass
	else:
		frappe.throw("Delivery Note is already generated against this purchase receipt,so first you have to delete delivery note='"+cstr(delivered_note[0][0])+"'")


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
				delivery_note = delivery_note_name[0][0] + ', ' + doc.name
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
	for d in doc.get('delivery_note_details'):
		if not d.assigned_qty>=d.qty:
			frappe.throw("Delivered Quantity must be less than or equal to assigned_qty for item_code='"+d.item_code+"'")





#For calling API through Poster---------------------------------------------------------------------------------------
def check_APItime():
	#GetItem()
	#GetCustomer()
	#GetOrders()
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

def get_Data_count(max_date, document_key):
	h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
	oauth = GetOauthDetails()
	r = requests.get(url='http://digitales.com.au/api/rest/mcount?start_date='+cstr(max_date)+'', headers=h, auth=oauth)
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
	status = get_products_from_magento(1, max_item_date, h, oauth)		
	
def get_missed_items(count, max_date, header, oauth_data):
	if count > 0:
		for index in range(1, count+1):
			get_products_from_magento(index, max_date,header, oauth_data, 'missed')

def get_products_from_magento(page, max_date, header, oauth_data, type_of_data=None):
	if page:
		r = requests.get(url='http://digitales.com.au/api/rest/products?filter[1][attribute]=updated_at&filter[1][gt]=%s&page=%s&limit=100&order=updated_at&dir=asc'%(max_date, page), headers=header, auth=oauth_data)
		product_data = json.loads(r.content)
		count = 0
		if len(product_data) > 0:
			for index in product_data:
				name = frappe.db.get_value('Item', product_data[index].get('sku'), 'name')
				if name:
					update_item(name, index, product_data)
					check_item_price(name,index,product_data)
				else:
					count = count + 1
					create_item(index, product_data)
			if count == 0 and type_of_data != 'missed':
				tot_count = get_Data_count(max_date, 'product_pages_per_100_mcount')
				if cint(tot_count)>0 :
					get_missed_items(6, max_date, header, oauth_data)
	return True

def create_item(i,content):
	item = frappe.new_doc('Item')
	item.item_code = content[i].get('sku')
	create_new_product(item,i,content)
	item.save(ignore_permissions=True)	
	check_item_price(item.name,i,content)

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
	item_price = frappe.get_doc("Item Price", price_list_name)
	create_new_item_price(item_price,i,content,price_list)
	item_price.save(ignore_permissions=True)

def create_price_list(item,i,content,price_list):
	item_price=frappe.new_doc("Item Price")
	create_new_item_price(item_price,i,content,price_list)
	item_price.save(ignore_permissions=True)

def create_new_item_price(item_price,i,content,price_list):
	item_price.price_list=price_list
	item_price.item_code=content[i].get('sku')
	item_price.price_list_rate=content[i].get('price')
	return True
	
def update_item(name,i,content):
	item = frappe.get_doc("Item", name)
	create_new_product(item,i,content)
	item.save(ignore_permissions=True)
	#check_item_price(item.name,i,content)

def create_new_product(item,i,content):
	item.item_name=content[i].get('name') or content[i].get('sku')
	item.item_group = 'Products'
	if content[i].get('media'):
		if frappe.db.get_value('Item Group', content[i].get('media'), 'name'):
			item.item_group=content[i].get('media') or 'Products'
		elif frappe.db.get_value('Item', content[i].get('media'), 'name'):
			item.item_group = 'Products'
		else:
			item_group=create_new_itemgroup(i,content)
			item.item_group=item_group
	item.description = 'Desc: ' + content[i].get('short_description') if content[i].get('short_description') else content[i].get('sku')
	item.event_id=i
	#item.item_status='Existing'
	warehouse=get_own_warehouse()
	item.default_warehouse=warehouse
	if content[i].get('barcode') and not frappe.db.get_value('Item', {'barcode':content[i].get('barcode')}, 'name'):	
		item.barcode=content[i].get('barcode')
	item.modified_date=content[i].get('updated_at')
	item.distributor=content[i].get('distributor')
	item.product_release_date=content[i].get('release_date')
	item.default_supplier = get_supplier(content[i].get('distributor'))
	return True

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
	obj = frappe.get_doc('Supplier', supplier)
	obj.supplier_name = supplier.replace('(s)', '')
	obj.save(ignore_permissions=True)
	return True

def create_supplier(supplier):
	sl = frappe.new_doc('Supplier')
	sl.supplier_name = supplier
	sl.supplier_type = 'Stock supplier' if frappe.db.get_value('Supplier Type', 'Stock supplier', 'name') else create_supplier_type()
	sl.save(ignore_permissions=True)
	return sl.name

def create_supplier_type():
	st = frappe.new_doc('Supplier Type')
	st.supplier_type = 'Stock supplier'
	st.save(ignore_permissions=True)
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

def create_new_itemgroup(i,content):
	itemgroup=frappe.new_doc('Item Group')
	itemgroup.parent_item_group='All Item Groups'
	itemgroup.item_group_name=content[i].get('media')
	itemgroup.is_group='No'
	itemgroup.save()
	return itemgroup.name or 'Products'

def get_own_warehouse():
	warehouse=frappe.db.sql("""select value from `tabSingles` where doctype='Configuration Page'
				and field='own_warehouse'""",as_list=1)
	if warehouse:
		return warehouse[0][0]
	else:
		frappe.msgprint("Please specify default own warehouse in Configuration Page",raise_exception=1)

def GetOauthDetails():
	oauth=OAuth(client_key='5a3bc10d3ba1615f5466de92e7cae501', client_secret='3a03ffff8d9a5b203eb4cad26ffa5b16', resource_owner_key='3d695c38d659411c8ca0d90ff0ac0c0c', resource_owner_secret='ef332ab23c09df818426909db9639351')	
	return oauth

#update configuration
def update_execution_date(document):
	now_plus_10 = datetime.datetime.now() + datetime.timedelta(minutes = 10)
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
	status=get_customers_from_magento(1, max_customer_date, h, oauth)	

def get_missed_customers(count, max_date, header, oauth_data):
	if count > 0:
		for index in range(1, count+1):
			get_customers_from_magento(index, max_date,header, oauth_data, 'missed')

def get_customers_from_magento(page, max_date, header, oauth_data,type_of_data=None):
	if page:
		r = requests.get(url='http://digitales.com.au/api/rest/customers?filter[1][attribute]=updated_at&filter[1][gt]=%s&page=%s&limit=100&order=updated_at&dir=asc'%(max_date, page), headers=header, auth=oauth_data)
		customer_data = json.loads(r.content)
		count = 0
		if len(customer_data) > 0:
			for index in customer_data:
				name = frappe.db.get_value('Customer', customer_data[index].get('organisation').replace("'",""), 'name')
				if name:
					update_customer(name, index, customer_data)
					# GetAddress(index,customer_data)
				else:
					count = count + 1
					create_customer(index, customer_data)
					# GetAddress(index,customer_data)
			if count == 0 and type_of_data != 'missed':
				tot_count = get_Data_count(max_date, 'customer_pages_per_100_mcount')
				if cint(tot_count)>0 :
					get_missed_customers(6, max_date, header, oauth_data)

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
	customer = frappe.get_doc("Customer", customer_name)
	customer.customer_name= customer_name.replace("(C)","")
	customer.save(ignore_permissions=True)

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
	
def create_customer_contact(customer,i,content,contact):
	if content[i].get('firstname'):
		contact.first_name=content[i].get('firstname')
		contact.last_name=content[i].get('lastname')
		contact.customer= customer.name
		contact.customer_name=customer.customer_name
		contact.entity_id = content[i].get('entity_id')
		contact.email_id=content[i].get('email')
		contact.save(ignore_permissions=True)
	else:
		pass

def create_new_contact(customer,i,content):
	contact=frappe.new_doc('Contact')
	if content[i].get('firstname'):
		contact.first_name=content[i].get('firstname')
		contact.last_name=content[i].get('lastname')
		contact.customer= customer
		contact.customer_name=customer
		contact.entity_id = content[i].get('entity_id')
		contact.email_id=content[i].get('email')
		contact.save(ignore_permissions=True)
	else:
		pass

def create_customer_group(i):
	cg=frappe.new_doc('Customer Group')
	cg.customer_group_name = i
	cg.parent_customer_group='All Customer Groups'
	cg.is_group='No'
	cg.save(ignore_permissions=True)
	return cg.name or 'All Customer Group'


def GetAddress(index,customer_data):
	h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
	oauth = GetOauthDetails()
	customer=frappe.db.get_value('Customer',{'entity_id':customer_data[index].get('entity_id')},'name')
	if customer:
		r = requests.get(url='http://digitales.com.au/api/rest/customers/'+cstr(customer_data[index].get('entity_id'))+'/addresses', headers=h, auth=oauth)
		content=json.loads(r.content)
		if content:
			for i in content:
				print cstr(i.get('entity_id')), customer_data[index].get('entity_id'), i.get('street'), i.get('firstname'), i.get('lastname')
				if not frappe.db.get_value('Address',{'entity_id': cstr(i.get('entity_id')),'address_title':cstr(i.get('firstname'))+' '+cstr(i.get('lastname')) +' '+cstr(i.get('street')[0])},'name'):
					create_onother_address_forCustomer(i, customer)
				else:
					print "hh"
					cust_address=frappe.db.get_value('Address',{'entity_id': cstr(i.get('entity_id')),'address_title':cstr(i.get('firstname'))+' '+cstr(i.get('lastname')) +' '+cstr(i.get('street')[0])},'name')
					update_onother_address_forCustomer(cust_address,i,customer)


def create_onother_address_forCustomer(i, customer):
	cad = frappe.new_doc('Address')
	cad.address_title = cstr(i.get('firstname'))+' '+cstr(i.get('lastname')) +' '+cstr(i.get('street')[0])
	cad.entity_id = cstr(i.get('entity_id'))
	cad.address_line1 = cstr(i.get('street')[0])
	cad.city = cstr(i.get('city'))
	cad.state = cstr(i.get('region'))
	cad.pincode = cstr(i.get('postcode'))
	cad.phone = cstr(i.get('telephone')) or '00000'
	cad.customer = customer
	cad.save(ignore_permissions=True)

def update_onother_address_forCustomer(cust_address,i, customer):
	cad = frappe.get_doc('Address',cust_address)
	#cad.address_title = address_details.get('firstname')+' '+address_details.get('lastname')
	cad.entity_id = cstr(i.get('entity_id'))
	cad.address_line1 = cstr(i.get('street')[0])
	cad.city = cstr(i.get('city'))
	cad.state = cstr(i.get('region'))
	cad.pincode = cstr(i.get('postcode'))
	cad.phone = cstr(i.get('telephone')) or '00000'
	cad.customer = customer
	cad.save(ignore_permissions=True)

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
	status=get_orders_from_magento(1, max_order_date, h, oauth)

def get_missed_orders(count, max_date, header, oauth_data):
	if count > 0:
		for index in range(1, count+1):
			get_orders_from_magento(index, max_date,header, oauth_data, 'missed')	


def get_orders_from_magento(page, max_date, header, oauth_data,type_of_data=None):
	if page:
		r = requests.get(url='http://digitales.com.au/api/rest/orders?filter[1][attribute]=updated_at&filter[1][gt]=%s&page=%s&limit=100&order=updated_at&dir=asc'%(max_date, page), headers=header, auth=oauth_data)
		order_data = json.loads(r.content)
		count = 0
		k=0
		if len(order_data) > 0:
			for index in order_data:
				customer = frappe.db.get_value('Contact', {'entity_id': order_data[index].get('customer_id')}, 'customer')
				if customer:
					create_or_update_customer_address(order_data[index].get('addresses'), customer)
					order = frappe.db.get_value('Sales Order', {'entity_id': order_data[index].get('entity_id')}, 'name')
					if not order:
						count = count + 1
						create_order(index,order_data,customer)
				else:
					k=k+1
					print k
			if count == 0 and type_of_data != 'missed':
				tot_count = get_Data_count(max_date, 'orders_pages_per_100_mcount')
				if cint(tot_count)>0 :
					get_missed_orders(6, max_date, header, oauth_data)
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

def update_address_forCustomer(cust_address,address_details, customer, address_type):
	cad = frappe.get_doc('Address',cust_address)
	#cad.address_title = address_details.get('firstname')+' '+address_details.get('lastname')
	cad.address_type = address_type
	cad.address_line1 = address_details.get('street')
	cad.city = address_details.get('city')
	cad.state = address_details.get('region')
	cad.pincode = address_details.get('postcode')
	cad.phone = address_details.get('telephone') or '00000'
	cad.customer = customer
	cad.save(ignore_permissions=True)

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
	order = frappe.get_doc("Sales Order", order)
	create_new_order(order,i,content,customer)
	order.save(ignore_permissions=True)

def create_order(i,content,customer):
	if content[i].get('order_items'):
		child_status=check_item_presence(i,content)
		if child_status==True:
			order = frappe.new_doc('Sales Order')
			create_new_order(order,i,content,customer)
			order.save(ignore_permissions=True)

def create_new_order(order,i,content,customer):
	from datetime import date
	from dateutil.relativedelta import relativedelta
	delivery_date = date.today() + relativedelta(days=+6)
	order.customer=customer
	order.entity_id=content[i].get('entity_id')
	order.modified_date=content[i].get('updated_at')
	order.delivery_date=delivery_date
	order.grand_total_export=content[i].get('grand_total')
	#order.discount_amount=content[i].get('discount_amount')
	if content[i].get('po_number'):
		order.po_no=content[i].get('po_number')
	order.order_type=content[i].get('order_type')
	for i in content[i].get('order_items'):
 		create_child_item(i,order)

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
