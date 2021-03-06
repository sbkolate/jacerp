# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, getdate, get_url
from frappe import _,msgprint
from datetime import date
from frappe.model.document import Document

class Project(Document):
	def get_feed(self):
		return '{0}: {1}'.format(_(self.status), self.project_name)

	def onload(self):
		"""Load project tasks for quick view"""
		if not self.get('__unsaved') and not self.get("tasks"):
			self.load_tasks()			

		self.set_onload('activity_summary', frappe.db.sql('''select activity_type,
			sum(hours) as total_hours
			from `tabTimesheet Detail` where project=%s and docstatus < 2 group by activity_type
			order by total_hours desc''', self.name, as_dict=True))
			
		self.load_purchase_invoices()
		self.load_expense_claim()

	def __setup__(self):
		self.onload()
		
		
		
	def load_purchase_invoices(self):  #Amitha
		self.purchase_invoices=[]
		for invoice in self.get_purchase_invoices():
			self.append("purchase_invoices", {
				"supplier": invoice.supplier,
				"grand_total":invoice.grand_total,
				"pi_id":invoice.name,
				"doc_status": "Draft" if invoice.docstatus == 0 else "Submitted" if invoice.docstatus == 1 else "Cancelled"
				})
		
	def load_expense_claim(self):  #Amitha
		self.expenses=[]
		for exp in self.get_expenses_claimed():
			self.append("expenses", {
				"person":exp.employee,
				"posting_date":exp.posting_date,
				"sanctioned_amount":exp.total_sanctioned_amount,
				"person_name":exp.employee_name,
				"task":exp.task,
				"approval_status":exp.approval_status,
				"doc_status": "Draft" if exp.docstatus == 0 else "Submitted" if exp.docstatus == 1 else "Cancelled"
				})
		
	
	def get_expenses_claimed(self):   # Amitha
		return frappe.get_all("Expense Claim", "*", {"project": self.name})	
	
		
	def on_trash(self):
		#checks Purchase Orders ( ie. Check Any Subcontractors for this Project)
		
		any_subcontractor = frappe.db.sql_list("""select name from `tabPurchase Invoice` 
			where project = %s""", (self.name))		
		if any_subcontractor:
			frappe.throw(_("Purchase Invoice {0} must be deleted/cancelled before deleting this Project").format(any_subcontractor))
	

	def load_tasks(self):
		"""Load `tasks` from the database"""
		self.tasks = []
		for task in self.get_tasks():
#			frappe.msgprint(_(task.item_name))
			self.append("tasks", {
				"title": task.subject,
				"status": task.status,
				"start_date": task.exp_start_date,
				"end_date": task.exp_end_date,
				"description": task.description,
				"supplier":task.supplier,
				
				"service_name":task.item_name,
				"deck_color":task.deck_color,
				"rail_color":task.rail_color,
				"board_replacement":task.board_replacement,
				"custom":task.custom,
				"deck_sft":task.deck_sft,
				"rail_sft":task.rail_sft,
				"total_sft":task.total_sft,
				
				"task_id": task.name,
				"pi_id":task.pi_id,
				"purchase_cost":frappe.db.get_value("Purchase Invoice",{"Project":self.name,"supplier":task.supplier},"total")
			})

	def get_tasks(self):		
		return frappe.get_all("Task", "*", {"project": self.name}, order_by="exp_start_date asc")
		
	def get_purchase_orders(self):		
		return frappe.get_all("Purchase Order", "*", {"project": self.name})
	
	def get_purchase_invoices(self):		
		return frappe.get_all("Purchase Invoice", "*", {"project": self.name})	

	def validate(self):
		self.validate_dates()	
		
#		self.create_purchase_invoice_if_supplier_exists()				
		self.sync_tasks()
		self.tasks = []	


	#	self.create_po_if_supplier_exists()
	#	self.make_pi()
	
	
	def make_pi(self):
		for t in self.project_subcontractors:	
			pi_item = []
			if t.pi_id:
				new_pi= frappe.get_doc("Purchase Invoive", {"name":t.pi_id})
			else:
				new_pi = frappe.new_doc("Purchase Invoice")
				new_pi.name = self.name	
			pi_item.append({
				"item_code": t.service_code,
				"item_name":t.service_name,
				"deck_color":t.deck_color,
				"rail_color":t.rail_color,
				"board_replacement":t.board_replacement,
				"custom":t.custom,
				"deck_sft":t.deck_sft,
				"rail_sft":t.rail_sft,
				"qty":t.total_sft,
				"schedule_date":date.today(),
				"description":t.service_name,
		#		"qty":1,
				"uom": "SFT",
				"project":self.name,
				"pi_id":t.pi_id,
				"conversion_factor":1 })
			new_pi.update({
				"company":self.company,				
				"supplier":t.supplier,
		#		"customer":self.customer,
				"transaction_date":date.today(),
				"project":self.name,
				"items":pi_item,
				"ignore_pricing_rule": "Yes"
			})	
#			frappe.throw(_(t.supplier))	
			new_pi.flags.ignore_links = True
			new_pi.flags.from_project = True
			new_pi.flags.ignore_feed = True
			new_pi.save(ignore_permissions = True)
			
	
		
	def create_po_if_supplier_exists(self):
		subcontract_names = []	
		suppliers=[]
		
		for row in self.get("project_subcontractors"):			
			if row.supplier:
				suppliers.append(row.supplier)		
		unique_list_of_suppliers=list(set(suppliers))
		
		for sup in unique_list_of_suppliers:	
			pi_item = []
			t=0
			for t in self.project_subcontractors:	
#				frappe.msgprint(_(t))					
				if(t.supplier and sup == t.supplier):
					if t.pi_id:
#						frappe.throw(_(t.pi_id))
						new_pi= frappe.get_doc("Purchase Invoive", {"name":t.pi_id})
					else:
						new_pi = frappe.new_doc("Purchase Invoice")
						new_pi.name = self.name	
					pi_item.append({
						"item_code": t.service_code,
						"item_name":t.service_name,
						"deck_color":row.deck_color,
						"rail_color":row.rail_color,
						"board_replacement":row.board_replacement,
						"custom":row.custom,
						"deck_sft":row.deck_sft,
						"rail_sft":row.rail_sft,
						"qty":row.total_sft,
						"schedule_date":date.today(),
						"description":t.service_name,
				#		"qty":1,
						"uom": "SFT",
						"project":self.name,
						"pi_id":t.pi_id,
						"conversion_factor":1 })
				else:
					pass
			new_pi.update({
				"company":self.company,				
				"supplier":sup,
			#	"customer":self.customer,
				"transaction_date":date.today(),
				"project":self.name,
				"items":pi_item,
				"ignore_pricing_rule": "Yes"
			})	
	#		frappe.throw(_(t.supplier))	
			new_pi.flags.ignore_links = True
			new_pi.flags.from_project = True
			new_pi.flags.ignore_feed = True
			new_pi.save(ignore_permissions = True)
			subcontract_names.append(new_pi.name)	
			t.pi_id = new_pi.name				
		
		for t in frappe.get_all("Purchase Invoice", "name", {"project": self.name, "name": ("not in", subcontract_names)}):
			if t.docstatus==0:
				frappe.delete_doc("Purchase Invoice", str(t.name).encode('ascii','ignore'))		
			
			
			
	def create_purchase_invoice_if_supplier_exists(self):
		subcontract_names = []	
	
	#	suppliers=[]
		
	#	for row in self.get("tasks"):			
	#		if row.supplier:				
	#			suppliers.append(row.supplier)	
					
	#	unique_list_of_suppliers=list(set(suppliers))
		
	#	for sup in unique_list_of_suppliers:	
	#		pi_item = []
	#		t=0
		for t in self.tasks:				
			pi_item = []
#				frappe.msgprint(_(t))					
#				if(t.supplier and sup == t.supplier):
			
			if t.pi_id:
				new_pi= frappe.get_doc("Purchase Invoive", {"name":t.pi_id})
			else:
				new_pi = frappe.new_doc("Purchase Invoice")
				new_pi.name = self.name	
				frappe.msgprint(_("Inside P IS"))	
			pi_item.append({
				"item_code": t.title,
				"item_name":t.service_name,
				"deck_color":t.deck_color,
				"rail_color":t.rail_color,
				"board_replacement":t.board_replacement,
				"description":t.description,
				"deck_sft":t.deck_sft,
				"rail_sft":t.rail_sft,
				"qty":t.total_sft,
				"schedule_date":date.today(),
				"description":t.service_name,
				#		"qty":1,
				"uom": "SFT",
				"project":self.name,
				"pi_id":t.pi_id,
				"conversion_factor":1 })
	#			else:
	#				pass
			new_pi.update({
				"company":self.company,				
				"supplier":t.supplier,
		#		"customer":self.customer,
				"transaction_date":date.today(),
				"project":self.name,
				"items":pi_item,
				"ignore_pricing_rule": "Yes"
			})	
#			frappe.throw(_(t.supplier))	
			new_pi.flags.ignore_links = True
			new_pi.flags.from_project = True
			new_pi.flags.ignore_feed = True
			new_pi.save(ignore_permissions = True)
			subcontract_names.append(new_pi.name)		
			t.pi_id = frappe.db.get_value("Purchase Invoice",{"name":self.name},"project")	
			frappe.msgprint(_(self.name))	
		
		for t in frappe.get_all("Purchase Invoice", "name", {"project": self.name, "name": ("not in", subcontract_names)}):
	#		frappe.delete_doc("Purchase Invoice",str(t.name).encode('ascii','ignore'))		
			frappe.msgprint(_(t.name))
	
	
	def validate_dates(self):
		if self.expected_start_date and self.expected_end_date:
			if getdate(self.expected_end_date) < getdate(self.expected_start_date):
				frappe.throw(_("Expected End Date can not be less than Expected Start Date"))

	def sync_tasks(self):
		"""sync tasks and remove table"""
		if self.flags.dont_sync_tasks: return

		task_names = []
		for t in self.tasks:
			if t.task_id:
				task = frappe.get_doc("Task", t.task_id)
			else:
				task = frappe.new_doc("Task")
				task.project = self.name

			task.update({
				"subject": t.title,
				"status": t.status,
				"exp_start_date": t.start_date,
				"exp_end_date": t.end_date,
				"description": t.description,
				"supplier":t.supplier,
				"purchase_cost":t.purchase_cost
			})			
		
			task.flags.ignore_links = True
			task.flags.from_project = True
			task.flags.ignore_feed = True
			task.save(ignore_permissions = True)
			task_names.append(task.name)

		# delete
		for t in frappe.get_all("Task", ["name"], {"project": self.name, "name": ("not in", task_names)}):
			frappe.delete_doc("Task", t.name)

		self.update_percent_complete()
		self.update_costing()

	def update_project(self):
		self.update_percent_complete()
		self.update_costing()
		self.flags.dont_sync_tasks = True
		self.save(ignore_permissions = True)

	def update_percent_complete(self):
		total = frappe.db.sql("""select count(*) from tabTask where project=%s""", self.name)[0][0]
		if total:
			completed = frappe.db.sql("""select count(*) from tabTask where
				project=%s and status in ('Closed', 'Cancelled')""", self.name)[0][0]

			self.percent_complete = flt(flt(completed) / total * 100, 2)

	def update_costing(self):
		from_time_sheet = frappe.db.sql("""select
			sum(costing_amount) as costing_amount,
			sum(billing_amount) as billing_amount,
			min(from_time) as start_date,
			max(to_time) as end_date,
			sum(hours) as time
			from `tabTimesheet Detail` where project = %s and docstatus = 1""", self.name, as_dict=1)[0]

		from_expense_claim = frappe.db.sql("""select
			sum(total_sanctioned_amount) as total_sanctioned_amount
			from `tabExpense Claim` where project = %s and approval_status='Approved'
			and docstatus = 1""",
			self.name, as_dict=1)[0]

		self.actual_start_date = from_time_sheet.start_date
		self.actual_end_date = from_time_sheet.end_date

		self.total_costing_amount = from_time_sheet.costing_amount
		self.total_billing_amount = from_time_sheet.billing_amount
		self.actual_time = from_time_sheet.time

		self.total_expense_claim = from_expense_claim.total_sanctioned_amount

		self.gross_margin = flt(self.total_billing_amount) - flt(self.total_costing_amount)

		if self.total_billing_amount:
			self.per_gross_margin = (self.gross_margin / flt(self.total_billing_amount)) *100

	def update_purchase_costing(self):
		total_purchase_cost = frappe.db.sql("""select sum(base_net_amount)
			from `tabPurchase Invoice Item` where project = %s and docstatus=1""", self.name)

		self.total_purchase_cost = total_purchase_cost and total_purchase_cost[0][0] or 0

	def send_welcome_email(self):
		url = get_url("/project/?name={0}".format(self.name))
		messages = (
		_("You have been invited to collaborate on the project: {0}".format(self.name)),
		url,
		_("Join")
		)

		content = """
		<p>{0}.</p>
		<p><a href="{1}">{2}</a></p>
		"""

		for user in self.users:
			if user.welcome_email_sent==0:
				frappe.sendmail(user.user, subject=_("Project Collaboration Invitation"), content=content.format(*messages))
				user.welcome_email_sent=1

	def on_update(self):
		self.load_tasks()
		self.sync_tasks()

def get_timeline_data(doctype, name):
	'''Return timeline for attendance'''
	return dict(frappe.db.sql('''select unix_timestamp(from_time), count(*)
		from `tabTimesheet Detail` where project=%s
			and from_time > date_sub(curdate(), interval 1 year)
			and docstatus < 2
			group by date(from_time)''', name))

def get_project_list(doctype, txt, filters, limit_start, limit_page_length=20):
	return frappe.db.sql('''select distinct project.*
		from tabProject project, `tabProject User` project_user
		where
			(project_user.user = %(user)s
			and project_user.parent = project.name)
			or project.owner = %(user)s
			order by project.modified desc
			limit {0}, {1}
		'''.format(limit_start, limit_page_length),
			{'user':frappe.session.user},
			as_dict=True,
			update={'doctype':'Project'})

def get_list_context(context=None):
	return {
		"show_sidebar": True,
		"show_search": True,
		'no_breadcrumbs': True,
		"title": _("Projects"),
		"get_list": get_project_list,
		"row_template": "templates/includes/projects/project_row.html"
	}

def get_users_for_project(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select name, concat_ws(' ', first_name, middle_name, last_name)
		from `tabUser`
		where enabled=1
		and name not in ("Guest", "Administrator")
		order by
		name asc""")

@frappe.whitelist()
def get_cost_center_name(project):
	return frappe.db.get_value("Project", project, "cost_center")
