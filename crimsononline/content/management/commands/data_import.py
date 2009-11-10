from time import strptime, strftime
from random import randrange
import datetime
import urllib2
import webbrowser
import os
import re

from django.core.management.base import BaseCommand
from crimsononline.content.models import *
from crimsononline.settings import *

TAGS = re.compile(r'<[^>]*>')
def extract_teaser(text):
    # jack html tags, return first 20 words of text
    text = text[:300]
    text = TAGS.sub(' ', text)
    return ' '.join(text.split()[:20])

def sqldec(str):
    if str:
        return str.decode("cp1252", "replace")
    else:
        return None

def get_issue(dt):
    if dt is None:
        dt = datetime.now()
    try:
        issue = Issue.objects.get(issue_date = dt)
    except:
        issue = Issue.objects.create(issue_date = dt)
    return issue

def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

def get_save_path_new(instance, filename):
    ext = splitext(filename)[1]
    filtered_capt = make_file_friendly(instance.kicker)
    if filtered_capt is None or filtered_capt == "":
        filtered_capt = str(randrange(1,10000000))
    return instance.issue.issue_date.strftime("photos/%Y/%m/%d/") + \
        filtered_capt + ext
    

    
    
def fix_images():
    import urllib
    import os
    
    do_delete = True
    
    # CHANGE ME!!!!
    f = open('image_paths.csv','r')
    
    # Dictionary mapping PKs to old urls
    old_urls = {}
    
    for line in f:
        pk, month, day, year, filename = line.split(',') 
        # Ignore /media links
        if filename[:3] != "pic":
            continue
       
        datefolder = "%s-%s-%s" % (month,day,year)
        old_location = "http://media.thecrimson.com/" + datefolder + "/" + filename
        old_urls[int(pk)] = old_location     
        
    old_images = Image.objects.filter(old_pk__isnull=False)
    
    for image in old_images:
        if image.old_pk not in old_urls:
            continue
        
        try:
            # Replace old file with new file
            print "Downloading",old_location
            print "Deleting",image.pic.path
            
            if do_delete:
                new_path, message = urllib.urlretrieve(old_location,image.pic.path)
            else:
                new_path = image.pic.path
            
            # Length of ".jpg" or ".gif" or ".png"
            base_filename = os.path.basename(new_path)
            prefix = base_filename.split(".")[0]
            img_dir = os.path.dirname(new_path)
            
            # Get all the images starting with the same thing as this one
            matches = lambda filename: filename[:len(prefix)] == prefix and filename != base_filename
            thumbs = filter(matches,os.listdir(img_dir))
            
            print img_dir
            print prefix
            # Delete thumbnails
            for thumb in thumbs:
                print "Deleting",thumb
                try:
                    if do_delete: os.remove(os.path.join(img_dir,thumb))
                    print "removed"
                except WindowsError:
                    print "Windows Error on",thumb
                    continue
                
           
            print "Success!"
        except IOError:
            print "FAILURE!"
            continue
    
    
def fix_tags():
    """A lot of the subsections were mapped incorrectly in the old db."""
    wrong_tags = ['News', 'Breaking News', 'Editorials', 'Comments',
                    'Op Eds', 'Columns', 'Letters', 'Sports', 'Columns',
                    'Features', 'Theater']
    wrong_tags = [None] + [Tag.objects.get(text=t) for t in wrong_tags]
    
    mapp = {
        'FM': {
            'Scrutiny': 1,
            'In The Meantime': 2,
            'For The Moment': 3,
            'Endpaper': 4,
            'Gadfly': 5,
            'Food and Drink': 6,
        },
        'Opinion': {
            'Focus': 5,
            'Comments': 1,
            'Op Eds': 2,
            'Columns': 3,
            'Letters': 4,
        },
        'Sports': {
            'Columns': 2,
            'Game Recaps': 3,
            'Notebooks': 4,
            'Sidebars': 5,
            'Previews': 6,
            'Features': 7,
            'Supplement Stories': 9,
            'Sports Briefs': 10,
            'Commencement Stories': 11,
        },
        'Arts': {
            'Theater': 1,
            'Film': 2,
            'Books': 3,
            'Music': 4,
            'Visual Arts': 5,
        },
    }
    
    right_tags = {}
    for key, value in mapp.iteritems():
        right_tags[key] = {}
        for k, v in value.iteritems():
            right_tags[key][wrong_tags[v]] = Tag.objects.get(text=k)
    
    for section_name, mappings in right_tags.iteritems():
        s = Section.objects.get(name=section_name)
        content = Content.objects.filter(section=s)
        print mappings
        for wrong, right in mappings.iteritems():
            print wrong, right
            for c in content.filter(tags=wrong):
                c.tags.remove(wrong)
                s = set(c.tags.all())
                s.add(right)
                c.tags = list(s)

class Command(BaseCommand):
    option_list = BaseCommand.option_list
    help = "Imports data from the old website, hosted on crimson-sql1. " \
           "Requires pymssql 1.0.2"

    def handle(self, *args, **options):
        if len(args) > 0 and args[0] == 'fix_tags':
            fix_tags()
            return
        
        try:
            import pymssql
        except:
            print "Could not import pymssql"
        
        # where to pick up importing articles
        if len(args) is 0:
            article_start_id = 0
        else:
            article_start_id = int(args[0])
        
        conn = pymssql.connect(as_dict=True, host='crimson-sql1', user='sa',
            password='131Cr!mIt131', database='CrimsonWebsite')
        cur = conn.cursor()
        
        # link SectionIDs to Section objects in the new database
        sections = {}
        cur.execute("SELECT ID, Name FROM Sections")
        for row in cur.fetchall():
            try:
                name = row["Name"].strip()
                if name == "Magazine":
                    sections[str(row["ID"])] = Section.objects.get(name="FM")
                else:
                    sections[str(row["ID"])] = Section.objects.get(name=name)
            except:
                sections[str(row["ID"])] = Section.objects.get(name="News")
        print sections
        
        # link SubCategories to Tag objects in the new database
        subcategories = {}
        cur.execute("SELECT id, Name FROM SubCategories")
        for row in cur.fetchall():
            name = row["Name"]
            if name == 'September 11th Terrorist Attacks':
                name = 'September 11'
            try:
                subcategories[str(row["id"])] = Tag.objects.get(text=name)
            except:
                if len(name) > 24:
                    print name
                else:
                    newtag = Tag(text=name)
                    newtag.save()
                    subcategories[str(row["id"])] = newtag
        
        # link Subsections to Tag objects in the new database
        subsections = {}
        cur.execute("SELECT id, SubSectionName FROM Subsections")
        for row in cur.fetchall():
            name = row["SubSectionName"]
            if name == 'Faculty of Arts and Sciences':
                name = 'FAS'
            try:
                subsections[str(row["id"])] = Tag.objects.get(text=name)
            except:
                if len(name) > 24:
                    print name
                else:
                    newtag = Tag(text=name)
                    newtag.save()
                    subcategories[str(row["id"])] = newtag
        
        # link Sports to Tag objects in the new database
        sports = {}
        cur.execute("SELECT ID, SportName FROM Sports")
        for row in cur.fetchall():
            name = row["SportName"]
            try:
                sports[str(row["ID"])] = Tag.objects.get(text=name)
            except:
                if len(name) > 24:
                    print name
                    continue
                newtag = Tag(text=name, category='sports')
                newtag.save()
                sports[str(row["ID"])] = newtag

        
        # Create No Contributor if it doesn't exist
        try:
            no_contrib = Contributor.objects.get(last_name="Attributed")
        except:
            no_contrib = Contributor()
            no_contrib.first_name = "No"
            no_contrib.middle_name = "Writer"
            no_contrib.last_name = "Attributed"
            no_contrib.save()
        
        # import contributors -- working nearly perfectly, except for capitalization
        # don't run part (it's slow) if it's already been done
        if Contributor.objects.count() < 10000:
            cur.execute("SELECT ID, FirstName, MiddleName, LastName, CreatedOn FROM Contributors")
            rows = cur.fetchall()
            print "Importing " + str(len(rows)) + " Contributors"
            for row in rows:
                c = Contributor()
                c.first_name = sqldec(row["FirstName"]).capitalize()
                c.middle_name = sqldec(row["MiddleName"]) if row["MiddleName"] not in [None," "] else ""
                c.last_name = sqldec(row["LastName"]).capitalize()
                c.id = row["ID"]
                c.is_active = False
                
                c.created_on = row["CreatedOn"] if row["CreatedOn"] is not None else datetime.now()
                c.save()
        else:
            print "skipped contributors"
        
        # import articles
        
        start_str = ''
        if article_start_id is not 0:
            start_str = " WHERE ID <= %d " % article_start_id
            rows = []
        else:
        # there are tons of duplicate articles, and duplicate headline
        #  articles get discarded, so start out with the articles that 
        #  have photos, since those are probably the important ones
            sqlstr = "SELECT ID, Headline, PublishedOn, Subheadline, Byline, " \
                "SectionID, SubsectionID, SubCategory, Text, CreatedOn, " \
                "ModifiedOn, Proofer, SNE FROM dbo.Articles WHERE ID IN " \
                "(SELECT DISTINCT(dbo.Articles.ID) FROM dbo.Articles, dbo.Pictures " \
                "WHERE dbo.Articles.ID = dbo.Pictures.articleID)"
            cur.execute(sqlstr)
            rows = cur.fetchall()
        
        sqlstr = str("SELECT ID, Headline, PublishedOn, Subheadline, Byline, "
                    "SectionID, SubsectionID, SubCategory, Text, CreatedOn, "
                    "ModifiedOn, Proofer, SNE FROM Articles %s ORDER BY ID "
                    "DESC") % start_str
        cur.execute(sqlstr)
        rows += cur.fetchmany(size=1000)
        while rows:
            print "Importing " + str(len(rows)) + " Articles"
            for row in rows:
                try:
                    a = Article.objects.get(pk=row["ID"])
                    continue
                except:
                    pass
                if row["Text"] is None:
                    print "Article ID %d has no text" % row['ID']
                    continue
                
                a = Article()
                try:
                    a.headline = sqldec(row["Headline"])
                    a.subheadline = sqldec(row["Subheadline"])
                    a.byline_type = row["Byline"]
                    a.section = sections[str(row["SectionID"])]
                    a.text = sqldec(row["Text"])
                    a.teaser = extract_teaser(a.text)
                    
                    #!!!!!
                    a.created_on = row["CreatedOn"] if row["CreatedOn"] not in ["", None] else datetime.now()
                    a.modified_on = row["ModifiedOn"] if row["ModifiedOn"] not in ["", None] else datetime.now()
                    slugtext = a.headline + " " + a.text
                    a.slug = slugify("-".join(slugtext.split()[:6]))[:65]
                    
                    a.issue = get_issue(row["PublishedOn"])
                    # TODO: Ehhhhh
                    a.proofer_id = row["Proofer"] if row["Proofer"] not in ["", None] else 1
                    a.sne_id = row["SNE"] if row["SNE"] not in ["", None] else 1
                    a.pub_status = 1
                    a.old_pk = row["ID"]
                except:
                    print "failed at article id %d" % row['ID']
                    raise
                try:
                    a.save()
                    if row["CreatedOn"] not in ("", None):
                        a.created_on = row["CreatedOn"] 
                        a.save()
                except Exception, e: # should be Exception as e, but server is on Python 2.5
                    print "Couldn't save article with id: " + str(a.id)
                    print "    " + str(e)
                    continue
                
                try:
                    # subsections and subcategories -> tags
                    if row["SubsectionID"] > 0:
                        t = subsections.get(str(row["SubsectionID"]), None)
                        if t is not None:
                            a.tags.add(t)
                    
                    if row["SubCategory"] > 0:
                        # the old site is ghetto... sports use the sports table instead of subcategories
                        if row["SectionID"] == 3:
                            t = sports.get(str(row["SubCategory"]), None)
                        else:
                            t = subcategories.get(str(row["SubsectionID"]), None)
                        if t is not None:
                            a.tags.add(t)
                except:
                    print "failed at article id %d" % row['ID']
                    raise
            rows = cur.fetchmany(size=10000)
        
        # link contributors and articles
        if len(args) > 1:
            ac_relation_start = int(args[1])
        else:
            ac_relation_start = False
        s = "WHERE ID < %d " % ac_relation_start if ac_relation_start else ""
        cur.execute("SELECT ID, ArticleID, ContributorID FROM ArticleWriters "
                    + s + "ORDER BY ID DESC")
        rows = cur.fetchall()
        print "Importing " + str(len(rows)) + " Article-Contributor Relations"
        for row in rows:
            try:
                a = Article.objects.get(old_pk=row["ArticleID"])
                a.contributors.add(Contributor.objects.get(pk=row["ContributorID"]))
            except Exception, e:
                print "Article Content relation %i failed" % row["ID"]
                print e
                continue
        
        if ac_relation_start is not 1:
            # handle articles with no contributors
            print Content.objects.filter(contributors=None).count()
            return 
            articles_no_contribs = Content.objects.filter(contributors=None)
            print "handling %d articles with no contributors" % len(articles_no_contribs)
            for a in articles_no_contribs:
                a.contributors.add(no_contrib)
        
        # Photos ... this is so ghetto
        cur.execute("SELECT ID, createdOn, modifiedOn, Caption, articleID, file500px, webwidth, webheight, kicker, issueDate, " 
            "ContributorID, Section FROM Pictures ORDER BY ID")
        rows = cur.fetchall()
        print "Importing " + str(len(rows)) + " Images"
        opener = urllib2.build_opener()
        for row in rows:
            i = Image()

            i.section = sections[str(row["Section"])]
            i.kicker = sqldec(row["kicker"]) if row["kicker"] not in ["", None] else "Unnamed photo"
            i.caption = sqldec(row["Caption"]) if row["Caption"] not in ["", None] else "1Uncaptioned photo"
            i.created_on = row["createdOn"] if row["createdOn"] is not None else datetime.now()
            i.modified_on = row["modifiedOn"] if row["modifiedOn"] is not None else datetime.now()
            slugtext = i.kicker + i.caption + str(randrange(1,10000))
            i.slug = slugify("-".join((slugtext).split()[:5]))
            i.width = row["webwidth"]
            i.height = row["webheight"]
            i.issue = get_issue(row["issueDate"]) 
            i.pub_status = 1
            i.id = row["ID"]
            
            # no leading zeroes
            try:
                mo = int(row["issueDate"].strftime("%m"))
                da = int(row["issueDate"].strftime("%d"))
                datefolder = row["issueDate"].strftime(str(mo) + "-" + str(da) + "-%Y")
            except:
                print "Date couldn't be parsed!"
                continue
            if datefolder is None or row["file500px"] is None:
                print "Either date or filename was missing. Skipped it."
                continue
            old_location = "http://media.thecrimson.com/" + datefolder + "/" + row["file500px"]
            
            # make sure pic is on the server
            try:
                pic = opener.open(old_location).read()
            except:
                continue
            
            old_filename = old_location.split("/")[len(old_location.split("/"))-1]
            new_location = get_save_path_new(i, old_filename)
            
            ensure_dir("static/" + new_location)
            fout = open("static/" + new_location, "wb")
            fout.write(pic)
            fout.close()
            i.pic = new_location
                
            try:
                i.save()
            except Exception, e:
                print e
                print "Couldn't save image with id " + str(i.id)
            # dead contributor ids
            try:
                if row["ContributorID"] is not None:
                    i.contributors.add(Contributor.objects.get(pk=row["ContributorID"]))
            except:
                print "Couldn't find contributor " + str(row["ContributorID"])
            # try to link photo and article, if article exists
            try:
                if row["articleID"] is not None:
                    a = Article.objects.get(pk=int(row["articleID"]))
                    x = ArticleContentRelation(order=0, article=a, related_content=i)
                    x.save()
            except:
                print row["articleID"]
                continue
        """
                
        # blogs
        cur.execute("SELECT ID, SectionID, BlogName, Description FROM Blogs")
        rows = cur.fetchall()
        print "Importing " + str(len(rows)) + " Blogs"
        for row in rows:
            cg = ContentGroup()
            cg.type = "blog"
            cg.name = sqldec(row["BlogName"])
            cg.blurb = sqldec(row["Description"])
            cg.section = sections[str(row["SectionID"])]
            cg.active = False
            cg.id = row["ID"]
            try:
                cg.save()
            except:
                print "Couldn't save ContentGroup " + cg.name
                print ""
        
        # import blog entries as articles
        cur.execute("SELECT ID, Title, Text, PublishedOn, CreatedOn, ModifiedOn, "
                    "SectionID, BlogID, ContributorID FROM BlogEntries")
        rows = cur.fetchall()
        print "Importing " + str(len(rows)) + " Blog Entries"
        for row in rows:
            a = Article()
            
            a.headline = sqldec(row["Title"])
            # some blog entries have no section?
            try:
                a.section = sections[str(row["SectionID"])]
            except:
                continue
            a.text = sqldec(row["Text"])
            #!!!!!
            a.created_on = row["CreatedOn"] if row["CreatedOn"] not in ["", None] else datetime.now()
            a.modified_on = row["ModifiedOn"] if row["ModifiedOn"] not in ["", None] else datetime.now()
            slugtext = a.headline + " " + a.text
            a.slug = slugify("-".join(slugtext.split()[:6]))
                
            a.issue = get_issue(row["PublishedOn"])
            # TODO: Fix proofer and sne 
            a.proofer_id = row["ContributorID"]
            a.sne_id = row["ContributorID"]
            a.pub_status = 1
            try:
                a.group = ContentGroup.objects.get(pk=row["BlogID"])
            except:
                # sorrento blog... damn hacks
                a.group = ContentGroup.objects.get(pk=54)
            a.id = row["ID"]
            try:
                a.save()
            except:
                print "Couldn't save blog entry with headline: " + a.headline
                #print row
                continue
            
            try:
                a.contributors.add(Contributor.objects.get(pk=row["ContributorID"]))
            except:
                print "Couldn't find contributor for blog entry"
                continue
    
        """

