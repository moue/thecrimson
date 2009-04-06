from django.core.management.base import NoArgsCommand
from crimsononline.content.models import *

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list
    help = "Fixes broken Content Generics due to content types having new pks"

    requires_model_validation = False

    def handle_noargs(self, **options):
        from random import shuffle, randrange
        
        # grab some data for random seeding of attributes
        contributors = list(Contributor.objects.all())
        issue = Issue.get_current()
        tags = list(Tag.objects.all())
        sections = list(Section.all())
        news_section = Section.objects.get(name="News")
        
        # unlinks all generics and generates new ones
        models = [Article, Image, ImageGallery]
        
        for model in models:
            for a in model.objects.all():
                # erase old generic, if it exists
                a.generic = None
                # trigger generation of a new one
                a.save()
            
                shuffle(contributors)
                shuffle(tags)
                shuffle(sections)
            
                # generate some random seed attributes
                a.priority = randrange(0, 20)
                a.issue = issue
                a.contributors = contributors[:randrange(1,4)]
                a.tags = tags[:randrange(1,8)]
                
                if randrange(0, 2):
                    a.section = news_section
                else:
                    a.section = sections[0]
                
                a.save()
        
        # generate some random Image - Article associations
        images = list(Image.objects.all())
        for a in Article.objects.all():
            shuffle(images)
            imgs = images[:randrange(0,4)]
            for i, img in enumerate(imgs):
                rel = ArticleContentRelation(order=i, article=a, related_content=img.generic)
                rel.save()