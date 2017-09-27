import json
import datetime
import csv
import time

import pymongo
from pymongo import MongoClient

client = MongoClient("140.120.13.242",27017)
print(client)

# db= client["fb_analysis_v2"]
# col=db["person_info"]

db= client["fb_analysis_ver2"]
col=db["person_info"]

try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request

app_id = "1764350177196516"
app_secret = "6de3392d9c717bb93d3d0a1bb3619b5a"  # DO NOT SHARE WITH ANYONE!
# file_id = ["tsaiingwen","MaYingjeou","starbuckstaiwan","duncanlindesign","jay","ashin555","YahooTWNews","ETtoday","news.ebc","appledaily.tw"]
# file_name=["蔡英文","馬英九","統一星巴克咖啡同好會","Duncan","周杰倫_Jay_Chou","五月天_阿信","Yahoo_奇摩新聞","ETNEWS新聞雲","東森新聞","台灣蘋果日報"]
# col_names=["tsaiingwen","MaYingjeou","starbuckstaiwan","duncanlindesign","jay","ashin555","YahooTWNews","ETtoday","news_ebc","appledaily_tw"]
file_id = ["YahooTWNews"]
file_name=["Yahoo_奇摩新聞"]
col_names=["YahooTWNews"]

col_dict=dict() # collection名稱
dic=dict() # 粉專名稱
for i in range(len(file_id)):
    dic[file_id[i]]=file_name[i]
    col_dict[file_id[i]]=col_names[i]

access_token = app_id + "|" + app_secret


def request_until_succeed(url):
    req = Request(url)
    success = False
    count=0
    while success is False:
        try:
            response = urlopen(req)
            if response.getcode() == 200:
                success = True
        except Exception as e:
            print(e)
            time.sleep(1)

            print("Error for URL {}: {}".format(url, datetime.datetime.now()))
            print("Retrying.")
            if count==1:
                return None
            else:
                count+=1


    return response.read().decode('utf8')

# Needed to write tricky unicode correctly to csv


def unicode_decode(text):
    try:
        return text.encode('utf-8').decode()
    except UnicodeDecodeError:
        return text.encode('utf-8')


def getFacebookCommentFeedUrl(base_url):

    # Construct the URL string
    fields = "&fields=id,message,reactions.limit(0).summary(true)" + \
        ",created_time,comments,from,attachment"
    url = base_url + fields

    return url


def getReactionsForComments(base_url):

    reaction_types = ['like', 'love', 'wow', 'haha', 'sad', 'angry']
    reactions_dict = {}   # dict of {status_id: tuple<6>}

    for reaction_type in reaction_types:
        fields = "&fields=reactions.type({}).limit(0).summary(total_count)".format(
            reaction_type.upper())

        url = base_url + fields

        data = json.loads(request_until_succeed(url))['data']

        data_processed = set()  # set() removes rare duplicates in statuses
        for status in data:
            id = status['id']
            count = status['reactions']['summary']['total_count']
            data_processed.add((id, count))

        for id, count in data_processed:
            if id in reactions_dict:
                reactions_dict[id] = reactions_dict[id] + (count,)
            else:
                reactions_dict[id] = (count,)

    return reactions_dict


def processFacebookComment(comment, status_id, parent_id=''):

    # The status is now a Python dictionary, so for top-level items,
    # we can simply call the key.

    # Additionally, some items may not always exist,
    # so must check for existence first

    comment_id = comment['id']
    comment_message = '' if 'message' not in comment or comment['message'] \
        is '' else unicode_decode(comment['message'])
    comment_author = unicode_decode(comment['from']['name'])
    num_reactions = 0 if 'reactions' not in comment else \
        comment['reactions']['summary']['total_count']

    if 'attachment' in comment:
        attachment_type = comment['attachment']['type']
        attachment_type = 'gif' if attachment_type == 'animated_image_share' \
            else attachment_type
        attach_tag = "[[{}]]".format(attachment_type.upper())
        comment_message = attach_tag if comment_message is '' else \
            comment_message + " " + attach_tag

    # Time needs special care since a) it's in UTC and
    # b) it's not easy to use in statistical programs.

    comment_published = datetime.datetime.strptime(
        comment['created_time'], '%Y-%m-%dT%H:%M:%S+0000')
    comment_published = comment_published + datetime.timedelta(hours=-5)  # EST
    comment_published = comment_published.strftime(
        '%Y-%m-%d %H:%M:%S')  # best time format for spreadsheet programs

    # Return a tuple of all processed data

    return (comment_id, status_id, parent_id, comment_message, comment_author,
            comment_published, num_reactions)


def scrapeFacebookPageFeedComments(page_id, access_token):
    with open('{}_facebook_comments.csv'.format(page_id), 'w',encoding='utf-8-sig') as file:
        w = csv.writer(file)
        w.writerow(["comment_id", "status_id", "parent_id", "comment_message",
                    "comment_author", "comment_published", "num_reactions",
                    "num_likes", "num_loves", "num_wows", "num_hahas",
                    "num_sads", "num_angrys", "num_special"])

        num_processed = 0
        scrape_starttime = datetime.datetime.now()
        after = ''
        base = "https://graph.facebook.com/v2.9"
        parameters = "/?limit={}&access_token={}".format(
            100, access_token)

        print("Scraping {} Comments From Posts: {}\n".format(
            dic[page_id], scrape_starttime))

        with open('{}_facebook_statuses.csv'.format(page_id), 'r',encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)

            # Uncomment below line to scrape comments for a specific status_id
            # reader = [dict(status_id='5550296508_10154352768246509')]

            for status in reader:
                has_next_page = True

                while has_next_page:

                    node = "/{}/comments".format(status['status_id'])
                    after = '' if after is '' else "&after={}".format(after)
                    base_url = base + node + parameters + after

                    url = getFacebookCommentFeedUrl(base_url)
                    try:
                        comments = json.loads(request_until_succeed(url))
                        reactions = getReactionsForComments(base_url)
                    except:
                        has_next_page=False
                        print("server 無法回應")
                    # print(url)
                    # print(comments['data'])
                    for comment in comments['data']:
                        cmlist = []
                        cursor = col.find({"id":comment['from']['id']}).limit(1)
                        if cursor.count() > 0:
                            for x in cursor:
                                cmlist = x["comment_list"]
                                if col_dict[page_id] not in cmlist:
                                    cmlist.append(col_dict[page_id])
                                    # print(cmlist)
                                    col.update({"id":comment['from']['id']}, {'$set': {"comment_list":cmlist}}, upsert=True)

                        elif cursor.count() == 0:
                            cmlist.append(col_dict[page_id])
                            col.insert({"id":comment['from']['id'],"name":comment['from']['name'],"comment_list":cmlist})

                        #print('NAME:\n',comment['from']['name'],"\nID:\n",comment['from']['id'])
                        comment_data = processFacebookComment(comment, status['status_id'])
                        
                        reactions_data = reactions[comment_data[0]]
                        # 留言的人 = comment_data[4]
                        # 留言的人說了甚麼話 = comment_data[3]
                        col2 = db[col_dict[page_id]]
                        cursor2 = col2.find({"comment_id":comment_data[0]}).limit(1)
                        if cursor2 <= 0:
                            col2.insert({"id":comment['from']['id'],"comment_id":comment_data[0],"comment":comment_data[3],"status_id":comment_data[1]})
                        elif cursor2 > 0:
                            continue
                        # print(comment['from']['id'])
                        user_name=comment_data[4]
                        user_comments=comment_data[3]
                        # 找有無此留言人，並存入資料庫
                        #col.insert({'name':user_name,'fansPage':dic[page_id],'comment':user_comments})

                        # calculate thankful/pride through algebra
                        num_special = comment_data[6] - sum(reactions_data)
                        w.writerow(comment_data + reactions_data +(num_special, ))

                        if 'comments' in comment:
                            has_next_subpage = True
                            sub_after = ''

                            while has_next_subpage:
                                sub_node = "/{}/comments".format(comment['id'])
                                sub_after = '' if sub_after is '' else "&after={}".format(sub_after)
                                sub_base_url = base + sub_node + parameters + sub_after

                                sub_url = getFacebookCommentFeedUrl(sub_base_url)
                                try:
                                    sub_comments = json.loads(request_until_succeed(sub_url))
                                    sub_reactions = getReactionsForComments(sub_base_url)
                                except:
                                    has_next_subpage = True
                                    print("server 無法回應(sub)")

                                for sub_comment in sub_comments['data']:
                                    sub_comment_data = processFacebookComment(sub_comment, status['status_id'], comment['id'])
                                    sub_reactions_data = sub_reactions[sub_comment_data[0]]
                                    # 留言人底下的留言人 = sub_comment_data[4]
                                    # 留言人底下的留言人之留言 = sub_comment_data[3]

                                    num_sub_special = sub_comment_data[6] - sum(sub_reactions_data)

                                    w.writerow(sub_comment_data +sub_reactions_data + (num_sub_special,))

                                    num_processed += 1
                                    if num_processed % 100 == 0:
                                        print("{} Comments Processed: {}".format(num_processed,datetime.datetime.now()))

                                if 'paging' in sub_comments:
                                    if 'next' in sub_comments['paging']:
                                        sub_after = sub_comments['paging']['cursors']['after']
                                    else:
                                        has_next_subpage = False
                                else:
                                    has_next_subpage = False

                        # output progress occasionally to make sure code is not
                        # stalling
                        num_processed += 1
                        if num_processed % 100 == 0:
                            print("{} Comments Processed: {}".format(num_processed, datetime.datetime.now()))
                    if 'paging' in comments:
                        if 'next' in comments['paging']:
                            after = comments['paging']['cursors']['after']
                        else:
                            has_next_page = False
                    else:
                        has_next_page = False

        print("\nDone!\n{} Comments Processed in {}".format(num_processed, datetime.datetime.now() - scrape_starttime))


if __name__ == '__main__':
    for file_name in file_id:
        scrapeFacebookPageFeedComments(file_name, access_token)


# The CSV can be opened in all major statistical programs. Have fun! :)
