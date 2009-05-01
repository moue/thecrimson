# TODO: rename this file shortcuts
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import Http404

def paginate(queryset, page_num, items_per_page, four_oh_four=True):
    """
    Takes a possibly bad page_num and paginates.
    Returns a tuple: (page object, paginator object)
    @queryset => paginates across this queryset
    @page_num => the number of the page (first page?, second page?)
    @items_per_page => duh
    @four_oh_four => if True, throws a 404 when page is invalid, otherwise
        throws the real error
    """
    p = Paginator(queryset, items_per_page)
    try:
        page = int(page_num)
        page = p.page(page)
    except (ValueError, EmptyPage, InvalidPage):
        if four_oh_four:
            raise Http404
        raise
    return (page, p)