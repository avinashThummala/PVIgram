import bottle
import os
import boto
import StringIO
import urllib2
from bottle import route, run, request
from instagram import client

bottle.debug(True)

CONFIG = {
    'client_id': client_id,
    'client_secret': client_secret,
    'redirect_uri': 'http://pvigram.herokuapp.com/gallery'
}

unauthenticated_api = client.InstagramAPI(**CONFIG)

@route('/')
def home():

    try:
        url = unauthenticated_api.get_authorize_url()

	page='''<style type="text/css"> 
	div.container {top: 0; left: 0; width: 100%; height: 100%; position: absolute; display: table}
  	p {display: table-cell; vertical-align: middle}
  	p {text-align: center}
	img.displayed {display: block; margin: 1em auto}
	</style>''' 

	page+='<div class="container"><p><img class=displayed src="http://tinyurl.com/bwv8eh6"><br/><br/>'
	page+='Instagram Selective Photo Backer<br/><br/>'
	page+='<a href="%s">Connect with Instagram</a></div>' % url

        return page

    except Exception, e:
        print e

@route('/gallery')
def on_callback():

    code = request.GET.get("code")

    if not code:
        return 'Missing code'
    try:
        access_token = unauthenticated_api.exchange_code_for_access_token(code)

        if not access_token:
            return 'Could not get access token'

        api = client.InstagramAPI(access_token=access_token[0])
        all_media, next = api.user_media_feed()

        page='<center><h2>Your Instagram Image Gallery</h2><br/>'

        for media in all_media:
            page+='<a href="/displayImage?at=%s&mid=%s"><img src="%s"/>' % (access_token[0],media.id,media.images['thumbnail'].url)

	page+='</center>'

        return page

    except Exception, e:
        print e

@route('/displayImage')
def on_request():

    at = request.GET.get("at")
    if not at:
        return 'Missing AccessToken'

    mediaId = request.GET.get("mid")
    if not mediaId:
        return 'Missing mediaId'

    try:
        api = client.InstagramAPI(access_token=at)
	media=api.media(mediaId)

        conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        bucket = conn.get_bucket("picovico")
	url = media.get_standard_resolution_url()

        k = boto.s3.key.Key(bucket)

        k.key = url.split('/')[::-1][0]

        file_object = urllib2.urlopen(url)          
        fp = StringIO.StringIO(file_object.read())

        k.set_contents_from_file(fp)
	k.make_public()

	page='<center>'

	if media.caption:
		page+='<h2>%s</h2><br/>' % media.caption.text

	page+='<img src="%s"/><br/><br/>' % media.get_standard_resolution_url()
	page+='<b>This photo has %s \"likes\" and %s \"comments\"<br/><br/>' % (media.like_count, media.comment_count)
	page+='<a href=%s>Instagram ImageLink</a><br/><br/>' % media.get_standard_resolution_url()
	page+='<a href=https://s3.amazonaws.com/picovico/%s>Local Permanent ImageLink</b></center>' % k.key

        return page

    except Exception, e:
        print e

run(host="0.0.0.0", port=int(os.environ.get("PORT", 8515)))
