from django.conf import settings

def static_content(link):
    """ 
    returns a url to a piece of static content relative to the static folder
    """
    return settings.MEDIA_URL + link