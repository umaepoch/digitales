// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt



cur_frm.add_fetch('get_sales_order','customer','customer_id');

cur_frm.add_fetch('get_sales_order','customer_name','customer_name');

//cur_frm.add_fetch('get_sales_order','"+doc.name+"','order_no');

cur_frm.add_fetch('get_sales_order','transaction_date','order_date');

cur_frm.add_fetch('item_code','item_name','item_name');

cur_frm.add_fetch('item_code','description','description');

cur_frm.add_fetch('process','process_type','process_type');

cur_frm.add_fetch('process','charge','charge');