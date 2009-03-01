from django.db import models

class ContentGroup(models.Model):
    """
    Groupings of content.  This is different from tags because groupings
     have metadata.
    
    Examples:
      * Columns
      * Image Galleries ?
      * Blogs ?
      * Article Series (say, a series on Iraq or the election)
      * 
    """
    TYPE_CHOICES = (
        ('column', 'Column'),
    )
    type = models.CharField(max_length=25, choices=TYPE_CHOICES)