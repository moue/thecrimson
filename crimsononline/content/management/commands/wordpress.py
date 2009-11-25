import string, os, sys, getopt
import re
from xml.dom import minidom
from content.models import *
from django.core.management.base import NoArgsCommand
from django.template.defaultfilters import slugify
from datetime import *
import urllib2
import urllib
from django.core.files import File

try:    
    flyby_contrib = Contributor.objects.get(first_name="",middle_name="",last_name="FlyByBlog")
except:
    flyby_contrib = Contributor(first_name="",middle_name="",last_name="FlyByBlog")
    flyby_contrib.save()
                    
AUTHORS_DICT = {
'loisbeckett' : 1202052,
'samueljacobs' : 1202069,
'pchesnut' : 1202090,
'amcleese' : 1202142,
'emmalind' : 1202230,
'cliffmarks' : 1203016,
'cflow' : 1203017,
'jahill' : 1203018,
'jkearney' : 1203023,
'LuisUrbina' : 1203030,
'lamor' : 1203050,
'abashir' : 1203100,
'abalakrishna' : 1203109,
'aditibalakrishna' : 1203109,
'loganury' : 1203119,
'asidman' : 1203135,
'nathanstrauss' : 1203244,
'adphill' : 1203409,
'mlchild' : 1203425,
'ecyu' : 1203538,
'junli' : 1203574,
'petertilton' : 1203593,
'chelseashover' : 1203759,
'ajdavis' : 1203774,
'michellequach' : 1203779,
'ajiang' : 1203791,
'laurenkiel' : 1203799,
'bonniekavoussi' : 1203800,
'coracurrier' : 1203808,
'kateleist' : 1203812,
'amdgama' : 1203813,
'pknoth' : 1203821,
'shanwang' : 1203911,
'junewu' : 1203916,
'mstrauss' : 1203968,
'mollystrauss' : 1203968,
'maxbrondfield' : 1204060,
'estheryi' : 1204069,
'estheriyi' : 1204069,
'ahmedmabruk' : 1204085,
'lvargas' : 1204091,
'sjoselow' : 1204192,
'peterzhu' : 1204212,
'charletonlamb' : 1204221,
'aleelockman' : 1204235,
'zwruble' : 1204244,
'bitaassad' : 1204291,
'cwells' : 1204303,
'tlawless' : 1204371,
'kpetti' : 1204392,
'dzheng' : 1204411,
'lmirviss' : 1204413,
'emdussom' : 1204420,
'dkolin' : 1204428,
'wendyhchang' : 1204433,
'jilliankushner' : 1204434,
'cfahey' : 1204442,
'enewcomer' : 1204459,
'liyunjin' : 1204461,
'egroll' : 1204462,
'ahofschneider' : 1204470,
'noahrayman' : 1204492,
'erosenman' : 1204493,
'sofiagroopman' : 1204511,
'mlyons' : 1204515,
'jchen' : 1204550,
'ashah' : 1204557,
'espitzer' : 1204575,
'mding' : 1204588,
'llian' : 1204743,
'jjiang' : 1204762,
'naveensrivatsa' : 1204798,
'jmcauley' : 1204942,
'amysun' : 1204993,
'janietankard' : 1205016,
'zoeweinberg' : 1205027,
'juliezauzmer' : 1205066,
'xiyu' : 1205070,
'jbarzilay' : 1205108,
'joannewong' : 1205111,
'siddarthch' : 1205113,
'garynorris' : 1205199,
'jnoronha' : 1205203,
'samnovey' : 1205205  
}


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
        convert(infile="wordpress.2009-11-07.xml")

def get_issue(dt):
    if dt is None:
        dt = datetime.now()
    try:
        issue = Issue.objects.get(issue_date = dt)
    except:
        issue = Issue.objects.create(issue_date = dt)
    return issue


ATTACHMENTS = re.compile(r'\[caption([^\[]+)\[/caption\]')
IMAGES = re.compile(r'<img([^>]*)>')
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

    for node in dom.getElementsByTagName('item'):
        # skip drafts, pending posts, and attachments
        if node.getElementsByTagName('wp:status')[0].firstChild.data != 'publish':
            continue

        tempslug = slugify(node.getElementsByTagName('wp:post_name')[0].firstChild.data)
    	dt = node.getElementsByTagName('wp:post_date')[0].firstChild.data
        dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        tempissue = get_issue(dt)
        
        try:
            a = Article.objects.get(slug=tempslug, issue=tempissue)
        except:
            a = Article()
            
            a.headline = node.getElementsByTagName('title')[0].firstChild.data
            a.issue = tempissue
            a.section = Section.cached("flyby")
            a.slug = tempslug
            a.pub_status = 1

            try:
                a.save()
            except:
                print "couldn't save article with headline '%s' (probably because of an IntegrityError)" % a.headline
                continue

            # contributors
            for author in node.getElementsByTagName('dc:creator')[0].firstChild.data.split("and"):
                author = author.replace(" ","")
                try:
                    c = Contributor.objects.get(pk=AUTHORS_DICT[author])
                    a.contributors.add(c)
                except:
                    a.contributors.add(flyby_contrib)
                    pass
            
            # text
    	    a.text = node.getElementsByTagName('content:encoded')[0].firstChild.data
            a.text = IMAGES.sub("",a.text)
            a.text = ATTACHMENTS.sub("",a.text)
            a.teaser = extract_teaser(a.text.split("<!--more-->")[0])
            a.text = '<p>' + a.text.replace("\n","</p><p>") + '</p>'
            a.text = a.text.replace("<p></p>","")
                    
        # delete related content
        a.rel_content.all().delete()

        opener = urllib2.build_opener()
        if node.getElementsByTagName('content:encoded')[0].firstChild != None:
            temptext = node.getElementsByTagName('content:encoded')[0].firstChild.data
            images = IMAGES.findall(temptext)

            for order, image in enumerate(images):
                SRC = re.compile(r'src="([^"]*)"')
                CAPTION = re.compile(r'alt="([^"]*)"')
                old_location = SRC.search(image).group(1)

                cur_caption = CAPTION.search(image).group(1)

                i = Image()
                i.caption = cur_caption
                i.slug = slugify("-".join(cur_caption.split()[:6]))[:65]
                i.section = Section.cached('flyby')
                i.issue = a.issue
                
                try:
                    #print old_location
                    old_location = old_location.replace("www.flybyblog.com","oldflyby.thecrimson.com")
                    req = urllib2.Request(old_location);
                    req.add_header('User-agent', 'Mozilla/5.0 (compatible; Konqueror/4.2; Linux) KHTML/4.2.2 (like Gecko)')                    

                    old_filename = old_location.split("/")[len(old_location.split("/"))-1]
                    new_location = image_get_save_path(i, old_filename)
                    ensure_dir("static/" + new_location)
                    
                    f = urllib2.urlopen(req)
                    local = open("static/" + new_location, 'wb')
                    local.write(f.read())
                    local.close()
                except:
                    print "couldn't read image at url %s" % old_location
                    continue
                
            
                i.pic = new_location
                i.caption = cur_caption
                i.pub_status = 1
                i.kicker = 'FlyBy Image'
                
                try:
                    i.save()
                except IOError:
                    print "couldn't save because of encoding issues with the image"
                    continue
                except:
                    print "couldn't save %s of some other issue..." % old_location
                    try:
                        i = Image.objects.get(slug=i.slug, issue=i.issue)
                    except:
                        continue

                
                i.contributors.add(flyby_contrib)
                acr = ArticleContentRelation(article=a, related_content=i, order=order)
                acr.save()
                
            


        """
    	# Get the categories
    	tempCategories = []
    	for subnode in node.getElementsByTagName('category'):
    		 tempCategories.append(subnode.getAttribute('nicename'))
        for cat in tempCategories:
            try:
                t = Tag.objects.get(text=cat)
            except:
                t = Tag(text=cat)
                t.save()
            a.tags.add(t)
    	categories = [x for x in tempCategories if x]
    	#post["categories"] = categories 
        """
        
        # Add post to the list of all posts
        try:
            a.save()
        except:
            pass
            
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
