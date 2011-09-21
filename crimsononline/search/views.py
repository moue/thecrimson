from haystack.views import SearchView
from django.shortcuts import render_to_response
from haystack.query import SearchQuerySet
from crimsononline.content.models import Contributor, Tag

MAX_MCONTRIBS = 30

class AjaxSearchView(SearchView):
    def __name__(self):
        return "AjaxSearchView"

    def create_response(self):
        
        """
        Generates the actual HttpResponse to send back to the user.
        """
        
        qu =  self.request.GET.get('q','')
        if qu:
            contributors_qs = SearchQuerySet().models(Contributor)
            tags_qs = SearchQuerySet().models(Tag)
            matching_contributors = (contributors_qs.auto_query(qu))[:MAX_MCONTRIBS]
            matching_tags = tags_qs.auto_query(qu)
        else:
            matching_contributors = None
            matching_tags = None
        
        (paginator, page) = self.build_page()
        
        if len(matching_contributors) > 11 and self.request.GET.has_key('ajax'):
            page.object_list = matching_contributors
        
        context = {
            'query': self.query,
            'form': self.form,
            'page': page,
            'paginator': paginator,
            'mcontributors': matching_contributors,
            'mtags': matching_tags,
            'is_search': qu
        }
        context.update(self.extra_context())

        if self.request.GET.has_key('ajax'):
            t = 'ajax/search_results_page.html'
        else:
            t = self.template
        return render_to_response(t, context, 
            context_instance=self.context_class(self.request))
        
    