from django.db import models
from crimsononline.content.models import Content

class SuperCrisis(models.Model):
	content = models.ForeignKey(Content)
	
	def __unicode__(self):
		return content.__unicode__()