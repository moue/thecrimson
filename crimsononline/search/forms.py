from django import forms

from haystack.forms import SearchForm


class DateRangeSearchForm(SearchForm):
    start_date = forms.DateField(required=False)
    end_date = forms.DateField(required=False)
    order_by = forms.ChoiceField(choices=(("relevance", "Relevance"),("date", "Date")))

    section_choices = (("All","All"),
        ("News","News"),("Arts","Arts"),("Sports","Sports"),("FM","Magazine"))
    content_sections = forms.ChoiceField(choices=section_choices)    
    
    def search(self):
        # First, store the SearchQuerySet received from other processing.
        sqs = super(DateRangeSearchForm, self).search()
    
        # Check to see if a start_date was chosen.
        if self.cleaned_data['start_date']:
            sqs = sqs.filter(pub_date__gte=self.cleaned_data['start_date'])

        # Check to see if an end_date was chosen.
        if self.cleaned_data['end_date']:
            sqs = sqs.filter(pub_date__lte=self.cleaned_data['end_date'])
        
        if self.cleaned_data['order_by'] == 'date':
            sqs = sqs.order_by('pub_date')
        
        print self.cleaned_data['content_sections']
        if self.cleaned_data['content_sections'] != 'All':
            sc = self.cleaned_data['content_sections']
            sqs = sqs.filter(section=Section.objects.get(name=sc).pk)

        return sqs
