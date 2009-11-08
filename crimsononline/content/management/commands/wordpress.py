import string, os, sys, getopt
import re
from xml.dom import minidom
from content.models import *
from django.core.management.base import NoArgsCommand
from datetime import *
import urllib2
from django.core.files import File

def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

TAGS = re.compile(r'<[^>]*>')
def extract_teaser(text):
    # jack html tags, return first 20 words of text
    text = text[:300]
    text = TAGS.sub(' ', text)
    return ' '.join(text.split()[:20])
    
    
class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list
    help = "Sets the right content type on Content objects"
    
    def handle_noargs(self, **options):
        Article.objects.all_objects().filter(section=Section.cached(flyby)).delete()
        convert(infile="wordpress.2009-11-07.xml")

def get_issue(dt):
    if dt is None:
        dt = datetime.now()
    try:
        issue = Issue.objects.get(issue_date = dt)
    except:
        issue = Issue.objects.create(issue_date = dt)
    return issue

def convert(infile):
    """Convert Wordpress Export File to multiple html files.
    
    Keyword arguments:
    infile -- the location of the Wordpress Export File
    outdir -- the directory where the files will be created
    authorDirs -- if true, create different directories for each author
    categoryDirs -- if true, create directories for each category
    
    """
    
    
    # First we parse the XML file into a list of posts.
    # Each post is a dictionary
    
    dom = minidom.parse(infile)
    missing_authors = []

    for node in dom.getElementsByTagName('item'):
        a = Article()
        if node.getElementsByTagName('wp:status')[0].firstChild.data == 'draft':
            continue
        if node.getElementsByTagName('wp:post_type')[0].firstChild.data == 'attachment':
            continue
            
    	a.headline = node.getElementsByTagName('title')[0].firstChild.data
        
    	dt = node.getElementsByTagName('pubDate')[0].firstChild.data
        dt = datetime.strptime(dt, '%a, %d %b %Y %H:%M:%S +0000')
        a.issue = get_issue(dt)
        a.section = Section.cached("flyby")
        slugtext = a.headline + " " + a.text
        

            

        
    	# wp:attachment_url could be use to download attachments
        a.slug = slugify("-".join(slugtext.split()[:6]))[:65]
        
    	# Get the categories
    	tempCategories = []
    	for subnode in node.getElementsByTagName('category'):
    		 tempCategories.append(subnode.getAttribute('nicename'))
    	categories = [x for x in tempCategories if x != '']
    	#post["categories"] = categories 

        
    	# Add post to the list of all posts
        try:
            a.save()
        except:
            continue

    	if node.getElementsByTagName('content:encoded')[0].firstChild != None:
            ATTACHMENTS = re.compile(r'\[caption([^\[]+)\[/caption\]')
    	    a.text = node.getElementsByTagName('content:encoded')[0].firstChild.data
            images = ATTACHMENTS.findall(a.text)
            for image in images:
                SRC = re.compile(r'src="([^"]*)"')
                CAPTION = re.compile(r'caption="([^"]*)"')
                old_location = SRC.search(image).group(1)
                cur_caption = CAPTION.search(image).group(1)

                i = Image(caption=cur_caption)
                i.section = Section.objects.get(name="Flyby")

                i.issue = a.issue
                
                opener = urllib2.build_opener()
                try:
                    pic = opener.open(old_location).read()
                except:
                    continue
                
                old_filename = old_location.split("/")[len(old_location.split("/"))-1]
                new_location = image_get_save_path(i, old_filename)
            
                ensure_dir("static/" + new_location)
                try:
                    fout = open("static/" + new_location, "wb")
                except:
                    continue
                    
                fout.write(pic)
                fout.close()
                i.pic = new_location
                i.slug = slugify("-".join(cur_caption.split()[:6]))[:65]
                i.caption = cur_caption
                i.pub_status = 1
                i.kicker = 'FlyBy Image'
                
                try:
                    i.save()
                except:
                    continue
                    
                try:    
                    flyby_contrib = Contributor.objects.get(last_name="FlyByBlog")
                except:
                    flyby_contrib = Contributor(last_name="FlyByBlog")
                    flyby_contrib.save()
                    
                i.contributors.add(flyby_contrib)
                acr = ArticleContentRelation(article=a, related_content=i)
                acr.save()
                
            a.text = ATTACHMENTS.sub("",a.text)
            a.text = '<p>' + a.text.replace("\n","</p><p>") + '</p>'
            a.text = a.text.replace("<p></p>","")
            a.teaser = a.text.split("<!--more-->")[0]
            a.teaser = TAGS.sub(' ', a.teaser)
            if len(a.teaser) == 0:
                a.teaser = TAGS.sub(' ',a.text)

        AUTHORS_DICT = {
            'ajdavis':1203774,
        
        }
        for author in node.getElementsByTagName('dc:creator')[0].firstChild.data.split("and"):
            author = author.replace(" ","")
            try:
                c = Contributor.objects.get(pk=AUTHORS_DICT[author])
                a.contributors.add(c)
            except:
                missing_authors.append(author)
                pass
        a.pub_status = 1
        
        # Add post to the list of all posts
        try:
            a.save()
        except:
            pass
        
        print a.headline[0]
    for i in set(missing_authors):
        print i     
    
def usage(pname):
    """Displays usage information
    
    keyword arguments:
    pname -- program name (e.g. obtained as argv[0])
    
    """
    
    
    print """python %s [-hac] [-o outdir] infile
    Converts a Wordpress Export File to multiple html files.
    
    Options:
        -h,--help\tDisplays this information.
        -a,--authors\tCreate different directories for each author.
        -c,--categories\tCreate directory structure from post categories.
        -o,--outdir\tSpecify a directory for the output.
        
    Example:
    python %s -c -o ~/TEMP ~/wordpress.2008-03-20.xml
        """ % (pname, pname)


def main(argv):
    outdir = ""
    authors = False
    categories = False
	
    try:
		opts, args = getopt.getopt(
		    argv[1:], "ha:o:c", ["help", "authors", "outdir", "categories"])	
    except getopt.GetoptError, err:
		print str(err)
		usage(argv[0])
		sys.exit(2)
	
    for opt, arg in opts:
		if opt in ("-h", "--help"):
			usage(argv[0])
			sys.exit()
		elif opt in ("-a", "--authors"):
			authors = True
		elif opt in ("-c", "--categories"):
		    categories = True
		elif opt in ("-o", "--outdir"):
		    outdir = arg
		
    infile = "".join(args)
	
    if infile == "":
	    print "Error: Missing Argument: missing wordpress export file."
	    usage(argv[0])
	    sys.exit(3)
	
    if outdir == "":
	    # Use the current directory
	    outdir = os.getcwd()
	
    convert(infile, outdir, authors, categories)
	

if __name__ == "__main__":
	main(sys.argv)
