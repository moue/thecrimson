from django import forms
from django.forms import ModelForm
from django.contrib import admin
from crimsononline.mware.models import SuperCrisis

class SuperCrisisAdmin(admin.ModelAdmin):
	#form = SuperCrisisForm
	model = SuperCrisis

admin.site.register(SuperCrisis)