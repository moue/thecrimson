import datetime
from django import forms
from django.forms.widgets import RadioSelect
from haystack.forms import SearchForm
from crimsononline.common.forms import CalendarWidget
from crimsononline.content.models import Article

class DateRangeSearchForm(SearchForm):
    
    start_date = forms.DateField(required=False, widget=CalendarWidget, 
        initial=lambda : datetime.date.today() - datetime.timedelta(years=10))
    end_date = forms.DateField(required=False, widget=CalendarWidget,
        initial=datetime.date.today)
    order_res = forms.ChoiceField(required=False,
        choices=[['relevance','Relevance'],['date','Date']],
        widget=RadioSelect())
    
    def search(self):
        # First, store the SearchQuerySet received from other processing.
        sqs = super(DateRangeSearchForm, self).search().models(Article)
        
        # Check to see if a start_date was chosen.
        if self.cleaned_data['start_date']:
            sqs = sqs.filter(pub_date__gte=self.cleaned_data['start_date'])
        else:
            sqs = sqs.filter(pub_date__gte=datetime.date(1990,1,1))
        # Check to see if an end_date was chosen.
        if self.cleaned_data['end_date']:
            sqs = sqs.filter(pub_date__lte=self.cleaned_data['end_date'])

        #if self.cleaned_data['order_res'] and self.cleaned_data['order_res'] == 'date':
        #    sqs = sqs.order_by('-pub_date')
        
        return sqs