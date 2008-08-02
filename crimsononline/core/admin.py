from django.contrib import admin
from crimsononline.core.models import *

class ContributorAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name',)
    search_fields = ('first_name', 'last_name',)
    fields = ('first_name', 
                'middle_initial', 
                'last_name',
                'type',
                'email',
                'phone',
                'board',
                'class_of',
                'is_active',)
admin.site.register(Contributor, ContributorAdmin)

class IssueAdmin(admin.ModelAdmin):
    list_display = ('issue_date',)
    search_fields = ('issue_date',)
admin.site.register(Issue, IssueAdmin)
    
class TagAdmin(admin.ModelAdmin):
    list_display = ('text',)
    search_fields = ('text',)
admin.site.register(Tag, TagAdmin)
    
admin.site.register(Image)

admin.site.register(ImageGallery)
    
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('headline', 'section', 'issue')
    search_fields = ('headline', 'contributors', 'text', 'tags')
    filter_horizontal = ('contributors', 'tags')
admin.site.register(Article, ArticleAdmin)