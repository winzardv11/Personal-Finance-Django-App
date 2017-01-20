from django.shortcuts import render
from django.views.generic import View, CreateView, UpdateView
from django.db.models import Sum
import datetime

from .models import Account
from .forms import TransferForm
from transactions.forms import FilterForm
from transactions.models import Transaction, Category, TransferTransaction
from budget.models import Budget

class AccountsOverview(View):

    def get_context(self, *args, **kwargs):
        transfer_form = TransferForm(prefix='transfer_form')
        filter_form = FilterForm(prefix='filter_form')
        accounts = Account.objects.all()

        ## CODE FOR CHART DATA ##
        categories = Category.objects.all() #Categories for drill down
        budgets = Budget.objects.all() #Budgets for primary chart

        if 'startdate' and 'enddate' in kwargs:
            start_date = kwargs['startdate']
            end_date = kwargs['enddate']
        else:
            start_date = datetime.datetime.today() + datetime.timedelta(-30)
            end_date = datetime.datetime.today()

        chart_header = start_date.strftime('%b %d %Y') + " - " + end_date.strftime('%b %d %Y')
        budget_data = {} # budget data for primary chart
        cat_data = {}  # category data for drill down

        for budget in budgets:
            subcat = {} #This will hold the drill down data for each budget
            if Transaction.objects.filter(PaymentTransaction___budget__budget=budget.id, #If transactions for budget exist
                                          PaymentTransaction___debit=True,
                                          date__range=[start_date, end_date]).count():
                amount = Transaction.objects.filter(PaymentTransaction___budget__budget=budget.id,
                                                    PaymentTransaction___debit=True,
                                                    date__range=[start_date, end_date]).aggregate(Sum('amount')) #Get the sum of amount for the budget
                budget_data[budget.name] = amount['amount__sum'] #Add to budget data
                # FOR THE DRILL DOWN #
                for category in categories:
                    if Transaction.objects.filter(PaymentTransaction___budget__budget=budget.id, #If the category exists in the given budget
                                                  PaymentTransaction___category=category.id,
                                                  PaymentTransaction___debit=True,
                                                  date__range=[start_date, end_date]).count():
                        category_amount = Transaction.objects.filter(PaymentTransaction___budget__budget=budget.id,
                                                                     PaymentTransaction___category=category.id, ).aggregate(
                            Sum('amount')) #Get the sum of the amount for the category
                        subcat[category.name] = category_amount['amount__sum']
                    if Transaction.objects.filter(PaymentTransaction___budget__budget=budget.id, #If there are uncategorized transactions in the budget
                                                  PaymentTransaction___category__isnull=True,
                                                  PaymentTransaction___debit=True,
                                                  date__range=[start_date, end_date]).count():
                        category_amount = Transaction.objects.filter(PaymentTransaction___budget__budget=budget.id,
                                                                     PaymentTransaction___category__isnull=True, ).aggregate(
                            Sum('amount'))
                        subcat['Uncatorgorized'] = category_amount['amount__sum']
                cat_data[budget.name] = subcat
                # END DRILL DOWN #
        ## END CHART CODE ##

        context = {'accounts': accounts, 'transfer_form': transfer_form, 'chart_header': chart_header, 'budget_data': budget_data,
         'cat_data': cat_data, 'filter_form': filter_form}
        return context


    def get(self, request):
        return render(request, 'accounts/overview.html', self.get_context(request))

    def post(self, request):
        transfer_form = TransferForm(request.POST, prefix='transfer_form')
        action = self.request.POST['action']

        if (action == 'transfer'):
            if transfer_form.is_valid():
                transfer_data = {}
                for key, value in transfer_form.cleaned_data.items():
                    transfer_data[key] = value
                from_acct_new_bal = transfer_data['from_acct'].balance - transfer_data['amount']
                transfer_data['from_acct'].balance = from_acct_new_bal
                transfer_data['from_acct'].save()
                to_acct_new_bal = transfer_data['to_acct'].balance + transfer_data['amount']
                transfer_data['to_acct'].balance = to_acct_new_bal
                transfer_data['to_acct'].save()
                TransferTransaction.objects.create(date=transfer_data['date'], account=transfer_data['to_acct'],
                                                   amount=transfer_data['amount'], from_account=transfer_data['from_acct'], balance=to_acct_new_bal)
                TransferTransaction.objects.create(date=transfer_data['date'], account=transfer_data['from_acct'],
                                                   amount=transfer_data['amount'], to_account=transfer_data['to_acct'], balance=from_acct_new_bal)
                start_date = datetime.datetime.today() + datetime.timedelta(-30)
                end_date = datetime.datetime.today()
        elif (action == 'date_filter'):
            filter_form = FilterForm(request.POST, prefix='filter_form')
            if filter_form.is_valid():
                start_date = filter_form.cleaned_data['start_date']
                end_date = filter_form.cleaned_data['end_date']

        return render(request, 'accounts/overview.html', self.get_context(request, startdate= start_date, enddate = end_date))