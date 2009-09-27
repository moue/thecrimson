from time import strptime, strftime
from random import randrange
import datetime
import urllib2
import webbrowser
import os
from django.core.management.base import NoArgsCommand
from crimsononline.content.models import *
from crimsononline.settings import *

def clean_teaser(self):
    """Add a teaser if one does not exist."""
    if self.cleaned_data['teaser']:
        return self.cleaned_data['teaser']
    else:
        # split article by paragraphs, return first 20 words of first para
        teaser = para_list(self.cleaned_data['text'])[0]
        teaser = TEASER_RE.sub("",teaser)
        return truncatewords(teaser, 20)

def sqldec(str):
    return str.decode("cp1252", "replace")

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
    return instance.issue.issue_date.strftime("photos/%Y/%m/%d/%H%M%S_") + \
        filtered_capt + ext

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list
    help = "Imports data from the old website, hosted on crimson-sql1. Requires pymssql 1.0.2"

    def handle_noargs(self, **options):
        try:
            import pymssql
        except:
            print "Could not import pymssql"

        conn = pymssql.connect(as_dict=True, host='crimson-sql1', user='sa',password='131Cr!mIt131', database='CrimsonWebsite')
        cur = conn.cursor()
        
        # link SectionIDs to Section objects in the new database
        sections = {}
        cur.execute("SELECT ID, Name FROM Sections")
        for row in cur.fetchall():
            try:
                if row["Name"] == "Magazine":
                    sections[str(row["ID"])] = Section.objects.get(name="FM")
                else:
                    sections[str(row["ID"])] = Section.objects.get(name=row["Name"])
            except:
                sections[str(row["ID"])] = Section.objects.get(name="News")
        print sections
		
		
        # link SubCategories to Tag objects in the new database
        subcategories = {}
        cur.execute("SELECT id, Name FROM SubCategories")
        for row in cur.fetchall():
            try:
                subcategories[str(row["id"])] = Tag.objects.get(text=row["Name"])
            except:
                newtag = Tag(text=row["Name"])
                newtag.save()
                subcategories[str(row["id"])] = newtag
        
        # link Subsections to Tag objects in the new database
        subsections = {}
        cur.execute("SELECT id, SubSectionName FROM Subsections")
        for row in cur.fetchall():
            try:
                subsections[str(row["id"])] = Tag.objects.get(text=row["SubSectionName"])
            except:
                newtag = Tag(text=row["SubSectionName"])
                newtag.save()
                subsections[str(row["id"])] = newtag
                
        # link Sports to Tag objects in the new database
        sports = {}
        cur.execute("SELECT ID, SportName FROM Sports")
        for row in cur.fetchall():
            try:
                sports[str(row["ID"])] = Tag.objects.get(text=row["SportName"])
            except:
                newtag = Tag(text=row["SportName"])
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
        cur.execute("SELECT ID, FirstName, MiddleName, LastName, CreatedOn FROM Contributors")
        rows = cur.fetchall()
        print "Importing " + str(len(rows)) + " Contributors"
        for row in rows:
            c = Contributor()
            c.first_name = sqldec(row["FirstName"]).capitalize()
            c.middle_name = sqldec(row["MiddleName"]) if row["MiddleName"]  not in [None," "] else ""
            c.last_name = sqldec(row["LastName"]).capitalize()
            c.id = row["ID"]
            
            c.created_on = row["CreatedOn"] if row["CreatedOn"] is not None else datetime.now()
            c.save()
			
        # import articles
        cur.execute("SELECT ID, Headline, PublishedOn, Subheadline, Byline, SectionID, SubsectionID, SubCategory, Text, CreatedOn, ModifiedOn, Proofer, SNE FROM Articles WHERE SectionID = 4")
        rows = cur.fetchmany(size=1000)
        print "Importing " + str(len(rows)) + " Articles"
        for row in rows:
            a = Article()
            
            a.headline = sqldec(row["Headline"])
            a.subheadline = sqldec(row["Subheadline"])
            a.byline_type = row["Byline"]
            a.section = sections[str(row["SectionID"])]
            a.text = sqldec(row["Text"])
            a.teaser = clean_teaser(a.text)
            
            #!!!!!
            a.created_on = row["CreatedOn"] if row["CreatedOn"] not in ["", None] else datetime.now()
            a.modified_on = row["ModifiedOn"] if row["ModifiedOn"] not in ["", None] else datetime.now()
            slugtext = a.headline + " " + a.text
            a.slug = slugify("-".join(slugtext.split()[:6]))
            
            a.issue = get_issue(row["PublishedOn"])
            # TODO: Ehhhhh
            a.proofer_id = row["Proofer"] if row["Proofer"] not in ["", None] else 1
            a.sne_id = row["SNE"] if row["SNE"] not in ["", None] else 1
            a.pub_status = 1
            a.id = row["ID"]
            try:
                a.save()
            except Exception as e:
                print "Couldn't save article with id: " + str(a.id)
                print e.args
                print e
                continue
            
            # subsections and subcategories -> tags
            if row["SubsectionID"] > 0:
                a.tags.add(subsections[str(row["SubsectionID"])])
            
            if row["SubCategory"] > 0:
                # the old site is ghetto... sports use the sports table instead of subcategories
                if row["SectionID"] == 3:
                    a.tags.add(sports[str(row["SubCategory"])])
                else:
                    a.tags.add(subcategories[str(row["SubCategory"])])
        
        # link contributors and articles
        cur.execute("SELECT ArticleID, ContributorID FROM ArticleWriters")
        rows = cur.fetchall()
        print "Importing " + str(len(rows)) + " Article-Contributor Relations"
        for row in rows:
            try:
                a = Article.objects.get(pk=row["ArticleID"])
                a.contributors.add(Contributor.objects.get(pk=row["ContributorID"]))
            except:
                pass
				
		# handle articles with no contributors
		articles_no_contribs = Article.objects.filter(contributors=None)
		for a in articles_no_contribs:
			a.contributors.add(Contributor.objects.get(last_name="WRITER ATTRIBUTED"))
        
        # Photos ... this is so ghetto
        cur.execute("SELECT ID, createdOn, modifiedOn, Caption, articleID, file500px, webwidth, webheight, kicker, issueDate, ContributorID, Section FROM Pictures")
        rows = cur.fetchmany(size=1000)
        print "Importing " + str(len(rows)) + " Images"
        for row in rows:
            i = Image()

            i.section = sections[str(row["Section"])]
            i.kicker = sqldec(row["kicker"]) if row["kicker"] not in ["", None] else "Unnamed photo"
            i.caption = sqldec(row["Caption"]) if row["Caption"] not in ["", None] else "Uncaptioned photo"
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
            mo = int(row["issueDate"].strftime("%m"))
            da = int(row["issueDate"].strftime("%d"))
            datefolder = row["issueDate"].strftime(str(mo) + "-" + str(da) + "-%Y")
            old_location = "http://media.thecrimson.com/" + datefolder + "/" + row["file500px"]
            
            # make sure pic is on the server
            try:
                pic = urllib2.build_opener().open(old_location).read()
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
            except:
                print "Couldn't save image with kicker " + i.kicker + " and description " + i.caption + " from date " + str(i.issue.issue_date)
            # dead contributor ids
            try:
                i.contributors.add(Contributor.objects.get(pk=row["ContributorID"]))
            except:
                print "Couldn't find contributor " + str(row["ContributorID"])
            # try to link photo and article, if article exists
            try:
                a = Article.objects.get(pk=row["articleID"])
                a.rel_content.add(i)
            except:
                print "couldn't find linked article"
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
        cur.execute("SELECT ID, Title, Text, PublishedOn, CreatedOn, ModifiedOn, SectionID, BlogID, ContributorID FROM BlogEntries")
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

