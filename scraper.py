import re
import urllib
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dateutil.parser import parse
from collections import Counter
from string import punctuation

visited_links = set()
icsSubDomain = {}
uniqueUrlCounter = 0
topCount = 0
topUrl = " "
totalCounter = Counter()

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

#helper function used to filter empty URL's
def filterFunction(variable):
    if variable is not None:
        return False
    return True

#checks whether passed in string is a date
def is_date(string, fuzzy=False):
    try:
        parse(string, fuzzy=fuzzy)
        return True
    except:
        return False

#helper function to find word stuff for report
def wordHelper(soup, url):

    for script in soup(["script", "style"]):
        script.extract()

    text = soup.p.get_text()
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)
    text_p = text.lower().split(" ")
    c_p = Counter()
    for i in text_p:
        c_p[i] += 1

    # We sum the two countesr and get a list with words count from most to less common
    total = c_p
    tempCount = 0
    global topCount
    global topUrl
    global totalCounter
    for word in total:
        tempNum = total[word]
        tempCount += tempNum

    if tempCount > topCount:
        topCount = tempCount
        topUrl = url

    print("The top word count is " + str(topCount) + " at the webpage " + topUrl)
    
    stop_words = set(["a","about","above","after","again","against","all","am","an",
                  "and","any","are","aren't","as","at","be","because","been",
                  "before","being","below","between","both","but","by","can't",
                  "cannot","could","couldn't","did","didn't","do","does",
                  "doesn't","doing","don't","down","during","each","few",
                  "for","from","further","had","hadn't","has","hasn't","have",
                  "haven't","having","he","he'd","he'll","he's","her","here",
                  "here's","hers","herself","him","himself","his","how","how's",
                  "i","i'd","i'll","i'm","i've","if","in","into","is","isn't",
                  "it","it's","its","itself","let's","me","more","most",
                  "mustn't","my","myself","no","nor","not","of",
                  "off","on","once","only","or","other","ought","our","ours",
                  "ourselves","out","over","own","same","shan't","she",
                  "she'd","she'll","she's","should","shouldn't","so","some",
                  "such","than","that","that's","the","their","theirs","them",
                  "themselves","then","there","there's","these","they","they'd",
                  "they'll","they're","they've","this","those","through","to",
                  "too","under","until","up","very","was","wasn't","we","we'd",
                  "we'll","we're","we've","were","weren't","what","what's","when",
                  "when's","where","where's","which","while","who","who's",
                  "whom","why","why's","with","won't","would","wouldn't",
                  "you","you'd","you'll","you're","you've","your","yours",
                  "yourself","yourselves", "\n", "", "©", "-"])
    new_total = Counter()
    for word in total:
        if word.lower() not in stop_words:
            new_total[word] = total[word]
            
    totalCounter = totalCounter + new_total
    
def extract_next_links(url, resp):
    global uniqueUrlCounter
    global icsSubDomain
    returnList = []

    # count number of subdomains in ics.uci.edu
    parsed = urlparse(url)
    uniqueUrlCounter += 1
    if "ics.uci.edu" in parsed.netloc:
        if parsed.netloc not in icsSubDomain:
            icsSubDomain[parsed.netloc] = 1
        else:
            icsSubDomain[parsed.netloc] = icsSubDomain.get(parsed.netloc) + 1

        subdomains = open(os.getcwd() + "/urls/subdomains.txt", "w")
        listOfSubDomains = [[k,v] for k, v in icsSubDomain.items()]
        listOfSubDomains.sort(key = lambda x:x[0])
        for subDomain in listOfSubDomains:
            subdomains.write(subDomain[0] + "," + str(subDomain[1]) + "\n")
        subdomains.close() 
    
    
    #cannot download page, return...
    if resp.status != 200:
        e = open("errors.txt", "a+")
        e.write("\n" + url + "\n" + str(resp.status) + ": " + str(resp.error))
        e.close()
        return returnList

    # check for different path in redirection...
    if len(resp.raw_response.history) != 0 and not is_valid(resp.raw_response.url):
        return returnList

    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')

    try:
        wordHelper(soup, url)
    except:
        pass
    
    #add all hyperlinks
    for link in soup.find_all('a'):
        returnList.append(link.get('href'))

    #filter
    filteredReturnlist = filter(filterFunction, returnList)

    #remove fragments and fix to absolute url
    for i in range(len(returnList)):
        returnList[i] = urllib.parse.urljoin(url, returnList[i], False)
        returnList[i], throwaway = urllib.parse.urldefrag(returnList[i])
    return returnList    

    
def is_valid(url):
    global visited_links
    global uniqueUrlCounter
    global topCount
    global topUrl
    try:
        parsed = urlparse(url)
        domains = [".ics.uci.edu", ".cs.uci.edu",
                    ".informatics.uci.edu", ".stat.uci.edu",
                    "today.uci.edu/department/information_computer_sciences"]
        uninterestingDomains = [ "archive.ics.uci.edu" ]
        #check for scheme misuse
        if parsed.scheme not in set(["http", "https"]):
            return False

        # repeats in path
        splitPath = parsed.path.split("/")
        alreadyVisitedPath = {}
        for i in splitPath:
            if i in alreadyVisitedPath:
                return False
            else:
                alreadyVisitedPath[i] = 1
            
        # checks if any portion of url is a date
            if is_date(splitPath[len(splitPath) - 1]):
                return False
        
        #check we are only looking into correct domains
        foundDomain = False
        for domain in domains:
            if domain in parsed.netloc:
                foundDomain = True
                break
        if not foundDomain:
            return False

        #check duplicate pages
        fullpath = url.split("://")
        if fullpath[1] in visited_links:
            return False
        else:
            visited_links.add(fullpath[1])

        #check uninteresting domains
        for domain in uninterestingDomains:
            if domain in parsed.netloc:
                return False
        
        if not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico|ppsx"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()):
            f = open(os.getcwd() + "/urls/url.txt", "a+")
            f.write(url + "\n")
            f.close()
            uniqueUrlCounter += 1
            uniqueUrlCount = open(os.getcwd() + "/urls/uniqueUrlCount.txt", "w")
            uniqueUrlCount.write(str(uniqueUrlCounter))
            uniqueUrlCount.close()

            list_most_common_words = totalCounter.most_common(50)
            
            maxCounter = open(os.getcwd() + "/urls/maxCount.txt", "w")
            maxCounter.write(str(topCount) + "," + topUrl + "\n")
            maxCounter.write(str(list_most_common_words))
            maxCounter.close()
            return True
        else:
            return False
    except TypeError:
        print ("TypeError for ", parsed)
        raise
