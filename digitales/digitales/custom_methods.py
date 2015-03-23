
from __future__ import unicode_literals
import frappe
from frappe.widgets.reportview import get_match_cond
from frappe.utils import add_days, cint, cstr, date_diff, rounded, flt, getdate, nowdate, \
	get_first_day, get_last_day,money_in_words, now, nowtime
#from frappe.utils import add_days, cint, cstr, flt, getdate, nowdate, rounded
from frappe import _
from frappe.model.db_query import DatabaseQuery
from requests_oauthlib import OAuth1 as OAuth
import requests
import json
#import datetime
import time
import datetime
#import time
from datetime import datetime
from time import sleep

# On submission of sales order---------------------------------------------------------------------------------------------------------------------------------------------------------------------
def create_purchase_order(doc,method):

	for d in doc.get('sales_order_details'):
		so_ordered_qty=frappe.db.sql("""select ifnull(sum(s.qty),0) as qty  
									from `tabSales Order Item` s inner join `tabSales Order` so 
										on s.parent=so.name where s.item_code='%s' and so.docstatus=1 """
										%d.item_code,as_list=1)
		#frappe.errprint(so_ordered_qty)
		
		po_ordered_qty=frappe.db.sql("""select ifnull(sum(p.qty),0) as qty 
									from `tabPurchase Order Item` p inner join `tabPurchase Order` po 
										on p.parent=po.name where p.item_code='%s' and po.docstatus=1 """
										%d.item_code,as_list=1)
		#frappe.errprint(po_ordered_qty)

		qty=flt(so_ordered_qty[0][0]-po_ordered_qty[0][0])
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
	e.schedule_date=d.transaction_date or nowdate()
	#po.taxes_and_charges=doc.taxes_and_charges
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
	# qty11=frappe.db.sql("""select qty from `tabPurchase Order Item` where 
	# 						item_code='%s' and parent='%s'"""
	# 							%(item,purchase_order),as_list=1)
	# qty1=flt(qty11[0][0]+flt(qty))
	frappe.db.sql("""update `tabPurchase Order Item` set qty='%s' 
						where parent='%s' and item_code='%s'"""
							%(qty,purchase_order,item))
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
	stock_assignment=frappe.db.sql("""select name from `tabStock Assignment Log` where 
									sales_order='%s' and item_code='%s'"""
									%(sales_order,d.item_code))
	#frappe.errprint(stock_assignment)
	if stock_assignment:
		ass_qty= frappe.db.sql(""" select assigned_qty from `tabStock Assignment Log`
			     where name='%s'"""%stock_assignment[0][0])
		frappe.errprint(ass_qty)
		qty=assigned_qty+ass_qty[0][0]
		frappe.db.sql("""update `tabStock Assignment Log` set purchase_receipt='%s',
					    sales_order='%s',assigned_qty='%s'
						where name='%s'"""
						%(purchase_receipt,sales_order,qty,stock_assignment[0][0]))
		frappe.db.commit()

	else:

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

# On sibmission of delivery Note---------------------------------------------------------------------------------------------------------------------------------
def update_stock_assignment_log_on_submit(doc,method):
	#frappe.errprint("in update stock assignment log")
	for d in doc.get('delivery_note_details'):
		sales_order_name=frappe.db.sql("""select s.against_sales_order from 
										`tabDelivery Note Item` s inner join `tabDelivery Note` so 
											on s.parent=so.name where s.item_code='%s' 
												and so.docstatus=1 and s.parent='%s' 
													order by so.creation"""
														%(d.item_code,doc.name),as_list=1)
		#frappe.errprint(sales_order_name[0][0])
		if sales_order_name:
			delivery_note_name=frappe.db.sql(""" select delivery_note  from `tabStock Assignment Log` where
							sales_order='%s' and item_code='%s'"""%(sales_order_name[0][0],d.item_code))
			#frappe.errprint(delivery_note_name)
			#frappe.errprint(len(delivery_note_name))
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
				#frappe.errprint(["delivery_note",delivery_note])
				if delivery_note_details:
					qty=cint(delivery_note_details[0][0])+d.qty
					#frappe.errprint(["qty",qty])
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
			#frappe.errprint(delivery_note[0][0])

			delivery_note_name=cstr(delivery_note[0][0]).split(", ")
		#frappe.errprint(delivery_note_name)
		#frappe.errprint(d.parent)
			if d.parent in delivery_note_name:
			#frappe.errprint("in if loop")
				delivery_note_name.remove(d.parent)
			
			#frappe.errprint(delivery_note_name)
				qty=cint(name[0][1])-d.qty
			#frappe.errprint(qty)
				if name:

					frappe.db.sql("""update `tabStock Assignment Log` 
								set delivered_qty='%s',delivery_note='%s' where item_code='%s'"""%(qty,','.join(delivery_note_name),d.item_code))
					frappe.db.commit()


def validate_qty_on_submit(doc,method):
	for d in doc.get('delivery_note_details'):
		if d.assigned_qty>=d.qty:
			pass
		else:
			frappe.msgprint("Delivered Quantity must be less than assigned_qty for item_code='"+d.item_code+"'",raise_exception=1)





#For calling API through Poster--------------------------------------------------------------------------------------------


#Get Item from magento------------------------------------------------------------------------------------------------------------------------------------
def GetItem():
	import datetime
	import time
	from datetime import datetime
	from time import sleep
	frappe.errprint("in get item")
	max_item_date=frappe.db.sql("""select max(modified_date) from `tabItem`""",as_list=1)
	if not max_item_date:
		content=GetCount()
		frappe.errprint(content)
		oauth = GetOauthDetails()
		h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
		for i in range(1,content['product_pages_per_100_count']+1):
			r = requests.get(url='http://staging.digitales.com.au.tmp.anchor.net.au/api/rest/products?page='+cstr(i)+'&limit=100', headers=h, auth=oauth)
			content=json.loads(r.content)
			frappe.errprint(len(content))
			try:
				get_item_data(content)
			except Exception,e:
				print e	
	else:
		pass
		#same as above written code
		# here we can call diffrent count method to get modified records according to the page number
		# try:
		# 	get_item_data(content)
		# except Exception,e:
		# 		print e

def get_item_data(content):
	for i in content:
		item=frappe.db.sql("""select name from `tabItem` where name='%s'"""%content[i].get('sku'),as_list=1)
		frappe.errprint(item)
		if item:
			update_item(item[0][0],i,content)
		else:
			frappe.errprint("in else part")
			create_item(i,content)

	# delete_item()
	# update_item_status()

def update_item_status():
	frappe.db.sql("""update `tabItem` set item_status='Non Existing'""" )
	frappe.db.commit()

def delete_item():
	frappe.db.sql("""delete from `tabItem` where item_status='Non Existing'""")
	frappe.db.commit()

def create_item(i,content):
	frappe.errprint("in create new item")
	item = frappe.new_doc('Item')
	create_new_product(item,i,content)
	#status=check_uom_conversion(item,i,content)
	item.save(ignore_permissions=True)	

def update_item(name,i,content):
	#frappe.errprint("in update item")
	item = frappe.get_doc("Item", name)
	create_new_product(item,i,content)
	item.save(ignore_permissions=True)

def create_new_product(item,i,content):
	frappe.errprint("in cretae new product")
	#print content[i]
	item.item_code=content[i].get('sku')
	item.item_name=content[i].get('name') or content[i].get('sku')
	item.item_group = 'Products'
	if content[i].get('media'):
		item_group=frappe.db.sql("""select name from `tabItem Group`""",as_list=1)
		frappe.errprint(item_group)
		if [content[i].get('media')] in item_group:
			item.item_group=content[i].get('media') or 'Products'
		else:
			item_group=create_new_itemgroup(i,content)
			item.item_group=item_group
	item.description=content[i].get('short_description') or content[i].get('description') or content[i].get('sku')
	item.event_id=i
	item.item_status='Existing'
	warehouse=get_own_warehouse()
	item.default_warehouse=warehouse
	item.modified_date=content[i].get('updated_at')
	item.distributor=content[i].get('distributor')
	item.product_release_date=content[i].get('release_date')
	return True

def check_uom_conversion(item):
	frappe.errprint("in chcek uom conversion")
	stock_uom=frappe.db.sql(""" select stock_uom from `tabItem` where name='%s'"""%item,as_list=1)
	frappe.errprint(stock_uom)
	if stock_uom:
		uom_details= frappe.db.sql("""select ifnull(count(idx),0) from `tabUOM Conversion Detail` where uom='%s' and parent='%s'
		"""%(stock_uom[0][0],item),as_list=1)
		frappe.errprint(uom_details)
		if uom_details:
			if uom_details[0][0]!=1:
				return False
			else:
				return True
	else:
		return False


def create_new_itemgroup(i,content):
	frappe.errprint("in item_group")
	itemgroup=frappe.new_doc('Item Group')
	frappe.errprint(itemgroup)
	itemgroup.parent_item_group='All Item Groups'
	itemgroup.item_group_name=content[i].get('media')
	itemgroup.is_group='No'
	itemgroup.save()
	# frappe.errprint(content[i]['media'])
	# frappe.errprint(item_group.name)
	return itemgroup.name or 'Products'

def get_own_warehouse():
		frappe.errprint("get_own_warehouse")
		warehouse=frappe.db.sql("""select value from `tabSingles` where doctype='Configuration Page'
					and field='own_warehouse'""",as_list=1)
		if warehouse:
			return warehouse[0][0]

		else:
			
			frappe.msgprint("Please specify default own warehouse in Configuration Page",raise_exception=1)


def GetOauthDetails():
	frappe.errprint("in get oauth details")
	oauth = OAuth(client_key='c069f82639779dba424a19da7bb3946e', client_secret='2586f31b9c69084ac431def208f055d1', resource_owner_key='f296cbe24a82dec20dd8878a43e4e2fd', resource_owner_secret='aa9625f1580a21d2d6d3c51d063f2456')
	return oauth


def GetCount():
	frappe.errprint("in get count details")
	oauth = OAuth(client_key='c069f82639779dba424a19da7bb3946e', client_secret='2586f31b9c69084ac431def208f055d1', resource_owner_key='f296cbe24a82dec20dd8878a43e4e2fd', resource_owner_secret='aa9625f1580a21d2d6d3c51d063f2456')
	h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
	r = requests.get(url='http://staging.digitales.com.au.tmp.anchor.net.au/api/rest/count', headers=h, auth=oauth)
	d = json.loads(r.content)
	return d




# Get Customer from magento---------------------------------------------------------------------------------------------------------------------------------
def GetCustomer():
	frappe.errprint("in get customer")
	content=GetCount()
	oauth = GetOauthDetails()
	h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
	max_date= frappe.db.sql("""select max(modified_date) from `tabCustomer`""",as_list=1)
	if max_date:
		try:
			#frappe.errprint(max_date[0][0])
			#frappe.errprint("max date is available")
			r = requests.get(url='http://staging.digitales.com.au.tmp.anchor.net.au/api/rest/customers?filter[1][attribute]=updated_at&filter[1][gt]='+cstr(max_date[0][0])+'', headers=h, auth=oauth)
			content=json.loads(r.content)
			get_cutomer_data(content)
		except Exception,e:
			print e,'Error'
	else:
		#frappe.errprint("max date is not available")
		r = requests.get(url='http://staging.digitales.com.au.tmp.anchor.net.au/api/rest/customers', headers=h, auth=oauth)
		content=json.loads(r.content)
		get_cutomer_data(content)

def get_cutomer_data(content):
	for i in content:
		customer=frappe.db.sql("""select name from `tabCustomer` where name='%s'"""%(cstr(i.get('organisation')).replace("'","")),as_list=1)
		if customer:
			# modified_date=datetime.strptime(customer[0][1], '%Y-%m-%d %H:%M:%S')
			# updated_date=datetime.strptime(i.get('updated_at'), '%Y-%m-%d %H:%M:%S')
			contact=frappe.db.sql("""select name from `tabContact` where entity_id='%s'"""%i.get('entity_id'),as_list=1)
			if contact:
				pass
			else:
				create_new_contact(customer[0][0],i,content)
			update_customer(customer[0][0],i,content)
		else:
			create_customer(i,content)

def create_customer(i,content):
	customer = frappe.new_doc('Customer')
	create_new_customer(customer,i,content)
	create_contact(customer,i,content)

def update_customer(customer,i ,content):
	customer = frappe.get_doc("Customer", customer)
	create_new_customer(customer,i,content)
	contact=frappe.db.sql("""select name from `tabContact` where entity_id='%s'"""%i.get('entity_id'),as_list=1)
	if contact:
		update_contact(customer,i,content,contact[0][0])
	else:
		create_contact(customer,i,content)

def update_contact(customer,i,content,contact):
	contact = frappe.get_doc("Contact", contact)
	create_customer_contact(customer,i,content,contact)

def create_contact(customer,i,content):
	contact=frappe.new_doc('Contact')
	create_customer_contact(customer,i,content,contact)

def create_new_customer(customer,i,content):
	frappe.errprint("in create new customer")
	customer.entity_id = i.get('entity_id')
	#customer.customer_name = (i.get('firstname') +' '+ i.get('lastname'))
	customer.customer_name=cstr(i.get('organisation')).replace("'","")
	customer.customer_type = 'Company'
	#customer.customer_group = create_customer_group(i.get('organisation')) or 'All Customer Groups'
	customer.customer_group='All Customer Groups'
	customer.territory = 'All Territories'
	customer.customer_status = 'Existing'
	customer.modified_date=i.get('updated_at')
	customer.save(ignore_permissions=True)
	
def create_customer_contact(customer,i,content,contact):
	frappe.errprint("create customer contact")
	if i.get('firstname'):
		contact.first_name=i.get('firstname')
		contact.last_name=i.get('lastname')
		contact.customer= customer.name
		contact.customer_name=customer.customer_name
		contact.entity_id = i.get('entity_id')
		contact.email_id=i.get('email')
		contact.save(ignore_permissions=True)
	else:
		pass


def create_new_contact(customer,i,content):
	frappe.errprint("in create new contact")
	contact=frappe.new_doc('Contact')
	if i.get('firstname'):
		contact.first_name=i.get('firstname')
		contact.last_name=i.get('lastname')
		contact.customer= customer
		contact.customer_name=customer
		contact.entity_id = i.get('entity_id')
		contact.email_id=i.get('email')
		#frappe.errprint(contact.entity_id)
		contact.save(ignore_permissions=True)
	else:
		pass


def create_customer_group(i):
	print "in the create_customer_group--------------------------------------------------"
	print i
	organization = cstr(i).replace("'","")
	customer_group=frappe.db.sql("""select name from `tabCustomer Group` where name='%s'"""%(organization))
	if not customer_group:
		cg=frappe.new_doc('Customer Group')
		cg.customer_group_name = organization
		cg.parent_customer_group='All Customer Groups'
		cg.is_group='No'
		cg.save(ignore_permissions=True)

def GetOrders():
	import datetime
	import time
	from datetime import datetime
	from time import sleep
	frappe.errprint("in get orders")
	content=GetCount()
	#frappe.errprint(content)
	oauth = GetOauthDetails()
	h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
	#for i in range(1,content['orders_pages_per_100_count']+1):
	#for in range(1,2):
	#r = requests.get(url='http://staging.digitales.com.au.tmp.anchor.net.au/api/rest/orders?page='+cstr(i)+'&limit=100', headers=h, auth=oauth)
	r = requests.get(url='http://staging.digitales.com.au.tmp.anchor.net.au/api/rest/orders?page=2&limit=100', headers=h, auth=oauth)
	content=json.loads(r.content)
	frappe.errprint(len(content))
	# frappe.errprint(i.get('entity_id'))
	#frappe.errprint(content[i].get('updated_at'))
	#try:
	for i in content:
		#frappe.errprint(i)
		# frappe.errprint(["orderid",content[i].get('entity_id')])
		# frappe.errprint(["customerid",content[i].get('customer_id')])
		customer=frappe.db.sql("""select name from `tabCustomer` where entity_id='%s'"""
			%content[i].get('customer_id'),as_list=1,debug=1)
		frappe.errprint(customer)
		if customer:

			order=frappe.db.sql("""select name,modified_date from `tabSales Order` where entity_id='%s'"""%(content[i].get('entity_id')),as_list=1)
			if order:
				modified_date=datetime.strptime(order[0][1], '%Y-%m-%d %H:%M:%S')
				updated_date=datetime.strptime(content[i].get('updated_at'), '%Y-%m-%d %H:%M:%S')
				frappe.errprint(modified_date)
				frappe.errprint(updated_date)
				if modified_date==updated_date:
					frappe.errprint("two order dates are equal")
					pass
				else:
					frappe.errprint("in update customer")
					update_order(order[0][0],i,content,customer[0][0])
			else:
				frappe.errprint("in else part")
				create_order(i,content,customer[0][0])
			
	# except Exception,e:
	# 	print e,'Error'

def update_order(order,i,content,customer):
	frappe.errprint("in update sales order")
	order = frappe.get_doc("Sales Order", order)
	create_order(i,content,customer)


def create_order(i,content,customer):
	frappe.errprint("in create order")
	from datetime import date
	from dateutil.relativedelta import relativedelta
	delivery_date = date.today() + relativedelta(days=+6)
	order = frappe.new_doc('Sales Order')
	order.customer=customer
	# if customer:
	# 	tender_group=frappe.db.sql(""""select tender_group from `tabCustomer` where name='%s'
	# 			"""%customer,as_list=1,debug=1)
	# 	if tender_group:
	# 		if tender_group[0][0]:

	# 			order.tender_group=tender_group[0][0]
	# 	else:
	# 		pass
	order.entity_id=content[i].get('entity_id')
	order.modified_date=content[i].get('updated_at')
	order.delivery_date=delivery_date
	#frappe.errprint(content[i].get('order_items'))
	order.grand_total_export=content[i].get('grand_total')
	if content[i].get('order_items'):
		for i in content[i].get('order_items'):
			frappe.errprint(i['sku'])
			item=frappe.db.sql("""select name from `tabItem` where item_code='%s'"""
				%i['sku'],as_list=1)
			if item:

				create_child_item(i,order)
			else:
				pass
	else:
		pass

	# if content[i].get('order_comments'):
	# 	for j in content[i].get('order_comments'):
	# 		frappe.errprint(i['status'])
	# 		order.status=j['status']

	
	order.save(ignore_permissions=True)

def create_child_item(i,order):
	frappe.errprint("in create child item")
	oi = order.append('sales_order_details', {})
	oi.item_code=i['sku']
	if i['sku']:
		item_release_date=frappe.db.sql("""select product_release_date from `tabItem`
								where name='%s'"""%i['sku'],as_list=1)
		frappe.errprint(item_release_date)
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
			frappe.errprint([attendance_rowdata[r], attendance_dict[r]])
	frappe.errprint(erferf)
	if error:
		frappe.db.rollback()
	else:
		frappe.db.commit()
	return {"messages": ret, "error": error}
