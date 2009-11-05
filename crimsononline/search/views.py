from haystack.views import SearchView
from django.shortcuts import render_to_response

class AjaxSearchView(SearchView):
    
    def create_response(self):
        """
        Generates the actual HttpResponse to send back to the user.
        """

        (paginator, page) = self.build_page()
        
        context = {
            'query': self.query,
            'form': self.form,
            'page': page,
            'paginator': paginator,
        }
        context.update(self.extra_context())

        if self.request.GET.has_key('ajax'):
            t = 'ajax/search_results_page.html'
        else:
            t = self.template
        return render_to_response(t, context, context_instance=self.context_class(self.request))