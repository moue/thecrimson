from django import forms
from django.forms import ModelForm
from django.contrib import admin
from crimsononline.mware.models import SuperCrisis
from django.shortcuts import render_to_response
from django.core.cache import cache

class SuperCrisisAdmin(admin.ModelAdmin):
    #form = SuperCrisisForm
    model = SuperCrisis
    
    def save_model(self, request, obj, form, change):
        c = obj.content
        response = c._render(request.GET.get('render','page'), request=request)
        url = c.get_absolute_url()
        cache_tuple = url, response
        cache.set('crimsononline.supercrisismode', cache_tuple)
        print 'Got here! ' + url
        obj.save()

admin.site.register(SuperCrisis, SuperCrisisAdmin)