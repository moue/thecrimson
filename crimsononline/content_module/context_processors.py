from crimsononline.content_module.models import ContentModule

def cm_processor(request):
    cms = {}
    content_modules = ContentModule.objects.filter(url=request.get_full_path())
    for cm in content_modules:
        cms[str(cm.zone)] = cm
    return {'cms': cms}