import hashlib
import urllib
from datetime import datetime
from django.core.management.base import NoArgsCommand
from django.template.defaultfilters import slugify
from crimsononline.content.models import *

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list
    help = "Fixes broken Content Generics due to content types having new pks"

    requires_model_validation = False

    def handle_noargs(self, **options):
        from random import shuffle, randrange, choice
        
        # grab some data for random seeding of attributes
        contributors = list(Contributor.objects.all())
        cur_issue = Issue.get_current()
        issues = list(Issue.objects.all())
        tags = list(Tag.objects.all())
        sections = list(Section.all())
        news_section = Section.objects.get(name="News")
        content_groups = list(ContentGroup.objects.all())
        
        # unlinks all generics and generates new ones
        models = [Article, Image, Gallery]
        
        # make some new articles
        try:
            u = urllib.urlopen('http://www.gutenberg.org/files/61/61.txt')
            text = u.readlines()
            text = [t for t in text if t]
            n = len(text)
            for i in range(0, 100):
                h = ''
                while len(h) < 6:
                    h = text[randrange(0,n)]
                r = randrange(0,n-100)
                t = ''.join(text[r:r+100])
                a = Article(headline=h, text=t, sne_id=1, proofer_id=1, 
                    teaser=t[:140])
                a.save()
        except:
            print "couldn't download new articles from project gutenburg"
        
        images = list(Image.all_objects.all())
        # make some new image galleries
        for i in range(0, 10):
            ig = Gallery(title=hashlib.md5(str(datetime.now())).hexdigest()[:10],
                description=hashlib.md5(str(datetime.now())).hexdigest())
            ig.save()
            
            shuffle(images)
            
            for n, img in enumerate(images[:randrange(2,6)]):
                GalleryMembership.objects.create(gallery=ig, image=img, order=n)
        
        for model in models:
            for a in model.all_objects.all():
                # trigger generation of a generic object
                a.save()
                
                shuffle(contributors)
                shuffle(tags)
                shuffle(sections)
                if model == Article:
                    wrds = a.text.split()
                elif model == Image:
                    wrds = a.kicker.split()
                else:
                    wrds = a.title.split()
                shuffle(wrds)
                
                # generate some random seed attributes
                
                a.slug = slugify('-'.join(wrds[:5]))
                a.priority = randrange(0, 20)
                if randrange(0,2):
                    a.issue = cur_issue
                else:
                    a.issue = choice(issues)
                if randrange(0,3):
                    a.contributors = contributors[:randrange(1,4)]
                else:
                    a.contributors = contributors[:1]
                a.tags = tags[:randrange(1,8)]
                a.group = choice(content_groups)
                a.pub_status = 1
                
                if randrange(0, 2):
                    a.section = news_section
                else:
                    a.section = sections[0]
                
                try:
                    a.save()
                except:
                    a.slug = hashlib.md5(str(datetime.now())).hexdigest()
                    a.save()
        
        images = list(Image.all_objects.all())
        
        # generate some random Image - Article associations
        
        for a in Article.all_objects.all():
            shuffle(images)
            imgs = images[:randrange(0,4)]
            for i, img in enumerate(imgs):
                rel = ArticleContentRelation(order=i, article=a, related_content=img.generic)
                rel.save()
    
    