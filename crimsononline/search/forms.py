import datetime
from django import forms
from haystack.forms import SearchForm
from crimsononline.common.forms import CalendarWidget


class DateRangeSearchForm(SearchForm):

    def __init__(self, *args, **kwargs):
        super(DateRangeSearchForm, self).__init__(*args, **kwargs)
        #self.fields['models'].widget = forms.RadioSelect()

    start_date = forms.DateField(required=False, widget=CalendarWidget)
    end_date = forms.DateField(required=False, widget=CalendarWidget)
    order_by = forms.ChoiceField(choices=(('relevance','Relevance'),('date','Date')),widget=forms.RadioSelect)


    def search(self):
        # First, store the SearchQuerySet received from other processing.
        sqs = super(DateRangeSearchForm, self).search()
        
        # Check to see if a start_date was chosen.
        if self.cleaned_data['start_date']:
            sqs = sqs.filter(pub_date__gte=self.cleaned_data['start_date'])
        else:
            sqs = sqs.filter(pub_date__gte=datetime.date(1990,1,1))
        # Check to see if an end_date was chosen.
        if self.cleaned_data['end_date']:
            sqs = sqs.filter(pub_date__lte=self.cleaned_data['end_date'])

        if self.cleaned_data['order_by'] and self.cleaned_data['order_by'] == 'date':
            sqs = sqs.order_by('-pub_date')
            
        return sqs
