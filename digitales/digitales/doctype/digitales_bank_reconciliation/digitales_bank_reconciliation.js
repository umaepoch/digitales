// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function(doc, cdt, cdn){
	cur_frm.set_intro('<i class="icon-question" /> ' +
		__("Update clearance date of Journal Entries marked as 'Bank Vouchers'"));

	cur_frm.add_fetch("bank_account", "company", "company");

	cur_frm.set_query("bank_account", function() {
		return {
			"filters": {
				// "account_type": "Bank",
				"report_type": "Balance Sheet",
				"group_or_ledger": "Ledger"
			}
		};
	});
}

cur_frm.cscript.update_clearance_date = function(doc, cdt,cdn){
	if(!doc.bank_statement_balance &&  !doc.opening_balance)
		frappe.throw("Bank Statement Balance and Opening Balance is Mandatory");
	if(doc.entries.length == 0)
		msgprint("No journal entries to update")
	else{
		pop_up = new frappe.ReconcileJournalVouchers();
	}
}

cur_frm.cscript.bank_account  = function(doc){
	doc.bank_statement_balance = 0;
	doc.opening_balance = 0;
	doc.out_of_balance = 0
	doc.total_debit = 0;
	doc.total_credit = 0

	cur_frm.refresh_fields();
}

cur_frm.cscript.opening_balance  = function(doc){
	doc.out_of_balance = calculate_out_of_balance(doc.is_assets_account, doc.bank_statement_balance, doc.opening_balance, doc.total_debit, doc.total_credit);
	cur_frm.refresh_field("out_of_balance")
}

cur_frm.cscript.bank_statement_balance = function(doc){
	doc.out_of_balance = calculate_out_of_balance(doc.is_assets_account, doc.bank_statement_balance, doc.opening_balance, doc.total_debit, doc.total_credit);
	cur_frm.refresh_field("out_of_balance")
}

calculate_out_of_balance = function(is_assets_account, bank_statement_balance, opening_balance, total_debit, total_credit){
	if(is_assets_account)
		return flt(bank_statement_balance - (opening_balance + total_debit - total_credit))
	else
		return flt(bank_statement_balance - (opening_balance - total_debit + total_credit))
}

var jvs_to_reconcile = []

frappe.ReconcileJournalVouchers = Class.extend({
	init: function() {
		this.make();
	},
	make: function() {
		jvs_to_reconcile = []

		var me = this;
		me.pop_up = this.render_pop_up_dialog(cur_frm.doc,me);

		this.append_pop_up_dialog_body(me.pop_up);
		this.append_journal_entries(cur_frm.doc);

		me.pop_up.show()
		$(".modal-dialog").css("width","800px");
		$(".modal-content").css("max-height","600px");
		$(".modal-footer").css("text-align","center");
	},
	render_pop_up_dialog: function(doc, me){
		return new frappe.ui.Dialog({
			title: "Select Voucher's To Reconcile",
			no_submit_on_enter: true,
			fields: [
				{label:__("Digitales Bank Reconciliation"), fieldtype:"HTML", fieldname:"reconcile"},
			],

			primary_action_label: "Reconcile & Submit",
			primary_action: function() {
				// Update Clearance Date of the checked vouchers
				_me = this;
				if(!jvs_to_reconcile.length)
					msgprint("Please first select the journal entries to reconcile");
				else if(parseFloat($("[name='out_of_balance']").val()) != 0){
					me.pop_up.hide();
					frappe.throw("Out Of Balance Amount Should be 0");
				}
				else{
					return cur_frm.call({
						doc: cur_frm.doc,
						args: {
							"jvs":jvs_to_reconcile
						},
						method: "update_details",
						callback: function(r) {
							if(!r.exc) {
								$(".modal-dialog").css("width","600px");
								me.pop_up.hide();
								frappe.model.set_default_values(cur_frm.doc);
								// get_server_fields('get_details', '' ,'', cur_frm.doc, cur_frm.doctype, cur_frm.docname, 1);
								msgprint("Clearance Date updated in: "+r.message.join());
								cur_frm.refresh_field("entries");
							}
						}
					});
				}
			}
		});
	},
	append_pop_up_dialog_body: function(pop_up){
		this.fd = pop_up.fields_dict;
		this.pop_up_body = $("<div class='row'><div class='col-xs-3'>From Date <input class='input-with-feedback form-control' type='text' name='from' readonly></div>\
		<div class='col-xs-3'>To BS Date <input class='input-with-feedback form-control' type='text' name='to' readonly></div>\
		<div class='col-xs-3'>Account <input class='input-with-feedback form-control' type='text' name='account' readonly></div>\
		<div class='col-xs-3'>BS Balance <input class='input-with-feedback form-control' type='text' name='bs_balance' readonly></div>\
		</div><br><div class='row'><div class='col-xs-3'>Opening Balance <input class='input-with-feedback form-control' type='text' name='opening_balance' readonly></div>\
		<div class='col-xs-3'>Out Of Balance <input class='input-with-feedback form-control' type='text' name='out_of_balance' value='0.0' readonly></div>\
		<div class='col-xs-3'>Total Debit <input class='input-with-feedback form-control' type='text' name='total_debit' value='0.0' readonly></div>\
		<div class='col-xs-3'>Total Credit <input class='input-with-feedback form-control' type='text' name='total_credit' value='0.0' readonly></div>\
		</div><br><div id='container' style='overflow: auto;max-height: 300px;'><table class='table table-bordered table-hover' id='entries'><thead>\
		<th><input type='checkbox' id='check_all' /></th><th><b>Posting Date</b></th><th><b>Voucher ID</b></th><th><b>Clearance Date</b></th>\
		<th><b>Against Account</b></th><th><b>Credit</b></th><th><b>Debit</b></th></thead><tbody></tbody></table></div>").appendTo($(this.fd.reconcile.wrapper));
	},
	append_journal_entries: function(doc){
		// appending from, to, account information, BS balance, opening_balance
		$("[name='from']").val(doc.from_date);
		$("[name='to']").val(doc.to_date);
		$("[name='account']").val(doc.bank_account);
		$("[name='bs_balance']").val(parseFloat(doc.bank_statement_balance).toFixed(2));
		$("[name='opening_balance']").val(parseFloat(doc.opening_balance).toFixed(2));
		$("[name='out_of_balance']").val(parseFloat(doc.bank_statement_balance-doc.opening_balance).toFixed(2));
		$("[name='total_debit']").val(0.0);
		$("[name='total_credit']").val(0.0);
		// appending journal voucher entries
		var je = doc.entries;
		var total_credit = parseFloat($("[name='total_credit']").val());
		var total_debit = parseFloat($("[name='total_debit']").val());
		var out_of_balance = parseFloat($("[name='out_of_balance']").val());

		if(doc.check_all)
			$("input#check_all").prop("checked",true);
		else
			$("input#check_all").prop("checked",false);

		for (var i = je.length - 1; i >= 0; i--) {
			if(je[i].voucher_id){
				// calculating the total credit, total debit and out of balance if entries are previously selected but not reconcile
				is_selected = locals["Digitales Bank Reconciliation Detail"][je[i].name].is_reconcile;

				checked = is_selected == 1? "checked": "";
				if(is_selected){
					total_debit += je[i].debit?je[i].debit:0;
					total_credit += je[i].credit?je[i].credit:0;

					$("[name='total_debit']").val(total_debit);
					$("[name='total_credit']").val(total_credit);

					// added Journal Voucher name to jvs_to_reconcile
					jvs_to_reconcile.push(je[i].voucher_id);
				}

				// setting up the against account and tooltip value
				var against_account = "";
				var tip = "";
				if(je[i].against_account){
					accounts = je[i].against_account.split(",");
					against_account = accounts[0];
					tip = "Against Account(s) : \n"
					for (var j = 0; j < accounts.length; j++) {
						tip += accounts[j].trim() + "\n";
					}
				}

				$("<tr><td><input type='checkbox' class='select' id='_select' "+checked+"><input type='hidden' id='cdn' value='"+ je[i].name +"'></td>\
					<td align='center'>"+ je[i].posting_date +"</td>\
					<td align='center' id='voucher_id'>"+ je[i].voucher_id +"</td>\
					<td align='center'>"+ (typeof(je[i].clearance_date) == "undefined"? "-": je[i].clearance_date) +"</td>\
					<td align='center' title='"+tip+"'>"+ against_account +"</td>\
					<td align='center' id='credit'>"+ (typeof(je[i].credit) == "undefined"? 0.0: je[i].credit) +"</td>\
					<td align='center' id='debit'>"+ (typeof(je[i].debit) == "undefined"? 0.0: je[i].debit) +"</td></tr>").appendTo($("#entries tbody"));
			}
		};

		if(doc.is_assets_account)
			$("[name='out_of_balance']").val(flt(doc.bank_statement_balance-(doc.opening_balance + total_debit - total_credit)));
		else
			$("[name='out_of_balance']").val(flt(doc.bank_statement_balance-(doc.opening_balance - total_debit + total_credit)));

		var me = this

		$(this.pop_up_body).find(".select").click(function(){
			$('input#check_all').prop('checked', false);
			cur_frm.doc.check_all = 0;

			row = $(this).parent().parent();

			var total_credit = parseFloat($("[name='total_credit']").val());
			var total_debit = parseFloat($("[name='total_debit']").val());
			var out_of_balance = parseFloat($("[name='out_of_balance']").val());
			var bs_balance = parseFloat($("[name='bs_balance']").val());
			var opening_balance = parseFloat($("[name='opening_balance']").val());
			var credit = parseFloat(row.find("td#credit").html());
			var debit = parseFloat(row.find("td#debit").html());

			var cdn = row.find("input#cdn").val();
			cdoc = locals["Digitales Bank Reconciliation Detail"][cdn]
			// check if check box is checked or Not
			if(row.find('input#_select').is(':checked')){
				total_credit += credit
				total_debit += debit

				// append voucher_id to reconcile
				jvs_to_reconcile.push(row.find("td#voucher_id").html())
				cdoc.is_reconcile = 1;
			}
			else{
				total_credit -= credit
				total_debit -= debit

				// remove the voucher_id from list
				jvs_to_reconcile.pop(row.find("td#voucher_id").html())
				cdoc.is_reconcile = 0;
			}

			bal = calculate_out_of_balance(doc.is_assets_account, bs_balance, opening_balance,total_debit,total_credit);
			// Set values to pop-up box
			$("[name='total_credit']").val((parseFloat(total_credit).toFixed(2)));
			$("[name='total_debit']").val((parseFloat(total_debit).toFixed(2)));
			// $("[name='out_of_balance']").val((parseFloat(out_of_balance).toFixed(2)))
			$("[name='out_of_balance']").val((parseFloat(bal).toFixed(2)))
			// set values to form
			doc.out_of_balance = parseFloat(bal).toFixed(2);
			doc.total_debit = parseFloat(total_debit).toFixed(2);
			doc.total_credit = parseFloat(total_credit).toFixed(2);
			doc.total_amount = flt(total_debit) - flt(total_credit);

			cur_frm.refresh_fields(["total_debit","total_credit","out_of_balance","total_amount","entries"]);
		});

		$("input#check_all").click(function(){
			me.check_all_jvs();
		});
	},
	check_all_jvs: function(){
		var credit = 0.0;
		var debit = 0.0;
		var bal = 0.0;
		jvs_to_reconcile = [];

		if($(this.pop_up_body).find("input#check_all").is(":checked")){
			$("input#_select").prop("checked",true)
			credit = cur_frm.doc.ttl_credit;
			debit = cur_frm.doc.ttl_debit;
			bal = calculate_out_of_balance(cur_frm.doc.is_assets_account, cur_frm.doc.bank_statement_balance, cur_frm.doc.opening_balance,cur_frm.doc.ttl_debit, cur_frm.doc.ttl_credit);
			bal = parseFloat(bal).toFixed(2);

			// setting entries records as is_selected to 1
			for (var i = 0; i < cur_frm.doc.entries.length; i++){
				cur_frm.doc.entries[i].is_reconcile = 1;
				jvs_to_reconcile.push(cur_frm.doc.entries[i].voucher_id);
			}
			cur_frm.doc.check_all = 1;
		}
		else{
			// setting entries records as is_selected to 0
			credit = 0.0;
			debit = 0.0;
			bal = 0.0;

			$("input#_select").prop("checked",false)
			for (var i = 0; i < cur_frm.doc.entries.length; i++){
				cur_frm.doc.entries[i].is_reconcile = 0;
			}
			cur_frm.doc.check_all = 0;
			jvs_to_reconcile = [];
		}

		$("[name='total_credit']").val(parseFloat(credit).toFixed(2));
		$("[name='total_debit']").val(parseFloat(debit).toFixed(2));
		$("[name='out_of_balance']").val(parseFloat(bal).toFixed(2));

		cur_frm.doc.total_debit = debit;
		cur_frm.doc.total_credit = credit;
		cur_frm.doc.out_of_balance = bal;
		cur_frm.doc.total_amount = flt(debit) - flt(credit);
		cur_frm.refresh_fields(["out_of_balance","entries","total_debit","total_credit","total_amount"]);
	}
})
