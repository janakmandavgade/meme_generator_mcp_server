import argparse
# import httplib
import http.client as httplib
import httplib2
import os
import random
import time
import ssl

import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request 
from dotenv import load_dotenv

load_dotenv()

# ssl._create_default_https_context = ssl._create_unverified_context

# # Explicitly tell the underlying HTTP transport library not to retry, since
# # we are handling retry logic ourselves.
# httplib2.RETRIES = 1

# # Create an httplib2.Http that skips SSL certificate verification
# insecure_http = httplib2.Http(disable_ssl_certificate_validation=True)

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
  httplib.IncompleteRead, httplib.ImproperConnectionState,
  httplib.CannotSendRequest, httplib.CannotSendHeader,
  httplib.ResponseNotReady, httplib.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the {{ Google Cloud Console }} at
# {{ https://cloud.google.com/console }}.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, '..', 'client_secret.json')

CLIENT_ID = os.environ.get('YOUTUBE_CLIENT_ID')
PROJECT_ID = os.environ.get('YOUTUBE_PROJECT_ID')
AUTH_URI = os.environ.get('YOUTUBE_AUTH_URI')
TOKEN_URI  = os.environ.get('YOUTUBE_TOKEN_URI')
AUTH_PROVIDER_X509_CERT_URL = os.environ.get('YOUTUBE_AUTH_PROVIDER_X509_CERT_URL')
CLIENT_SECRET = os.environ.get('YOUTUBE_CLIENT_SECRET')
REDIRECT_URIS  = ["http://localhost"]

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

VALID_PRIVACY_STATUSES = ('public', 'private', 'unlisted')
TOKEN_FILE = os.path.join(BASE_DIR, "..","token.json")

# Authorize the request and store authorization credentials.
# def get_authenticated_service():
#   flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
#   credentials = flow.run_local_server(port=0)
#   # return build(API_SERVICE_NAME, API_VERSION, credentials = credentials, http=insecure_http)
#   return build(API_SERVICE_NAME, API_VERSION, credentials = credentials)

# def get_authenticated_service(access_token=None, refresh_token=None):
#     creds = None
#     # 1) Load existing credentials if they exist
#     if os.path.exists(TOKEN_FILE):
#         creds = Credentials.from_authorized_user_info(str(TOKEN_FILE), SCOPES)

#     # 2) If no valid creds, run the flow once and save them
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_config(
#                 {
#                   "installed": {
#                     "client_id": CLIENT_ID,
#                     "project_id": PROJECT_ID,
#                     "auth_uri": AUTH_URI,
#                     "token_uri": TOKEN_URI,
#                     "auth_provider_x509_cert_url": AUTH_PROVIDER_X509_CERT_URL,
#                     "client_secret": CLIENT_SECRET,
#                     "redirect_uris": REDIRECT_URIS
#                   }
#                 }, 
#                 SCOPES
#             )
#             creds = flow.run_local_server(port=0)
#         # Save the credentials for the next run
#         with open(TOKEN_FILE, 'w') as token:
#             token.write(creds.to_json())

#     # 3) Build the YouTube service
#     return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

def get_authenticated_service(access_token: str, refresh_token: str):
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES
    )

    # Refresh token if needed
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # Build the YouTube API service
    return build("youtube", "v3", credentials=creds)

def initialize_upload(youtube, options):
  tags = None
  if options.keywords:
    tags = options.keywords.split(',')

  body=dict(
    snippet=dict(
      title=options.title,
      description=options.description,
      tags=tags,
      categoryId=options.category
    ),
    status=dict(
      privacyStatus=options.privacyStatus
    )
  )

  # Call the API's videos.insert method to create and upload the video.
  insert_request = youtube.videos().insert(
    part=','.join(body.keys()),
    body=body,
    # The chunksize parameter specifies the size of each chunk of data, in
    # bytes, that will be uploaded at a time. Set a higher value for
    # reliable connections as fewer chunks lead to faster uploads. Set a lower
    # value for better recovery on less reliable connections.
    #
    # Setting 'chunksize' equal to -1 in the code below means that the entire
    # file will be uploaded in a single HTTP request. (If the upload fails,
    # it will still be retried where it left off.) This is usually a best
    # practice, but if you're using Python older than 2.6 or if you're
    # running on App Engine, you should set the chunksize to something like
    # 1024 * 1024 (1 megabyte).
    media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
  )

  resumable_upload(insert_request)

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(request):
  response = None
  error = None
  retry = 0
  while response is None:
    try:
      print('Uploading file...')
      status, response = request.next_chunk()
      if response is not None:
        if 'id' in response:
          print('Video id "%s" was successfully uploaded.' % response['id'])
        else:
          exit('The upload failed with an unexpected response: %s' % response)
    except HttpError as e:
      if e.resp.status in RETRIABLE_STATUS_CODES:
        error = 'A retriable HTTP error %d occurred:\n%s' % (e.resp.status,
                                                             e.content)
      else:
        raise
    except RETRIABLE_EXCEPTIONS as e:
      error = 'A retriable error occurred: %s' % e

    if error is not None:
      print(error)
      retry += 1
      if retry > MAX_RETRIES:
        exit('No longer attempting to retry.')

      max_sleep = 2 ** retry
      sleep_seconds = random.random() * max_sleep
      print('Sleeping %f seconds and then retrying...' % sleep_seconds)
      time.sleep(sleep_seconds)

# if __name__ == '__main__':
#   parser = argparse.ArgumentParser()
#   parser.add_argument('--file', required=True, help='Video file to upload')
#   parser.add_argument('--title', help='Video title', default='Test Title')
#   parser.add_argument('--description', help='Video description',
#     default='Test Description')
#   parser.add_argument('--category', default='22',
#     help='Numeric video category. ' +
#       'See https://developers.google.com/youtube/v3/docs/videoCategories/list')
#   parser.add_argument('--keywords', help='Video keywords, comma separated',
#     default='')
#   parser.add_argument('--privacyStatus', choices=VALID_PRIVACY_STATUSES,
#     default='private', help='Video privacy status.')
#   args = parser.parse_args()

#   youtube = get_authenticated_service()

#   try:
#     initialize_upload(youtube, args)
#   except HttpError as e:
#     print('An HTTP error %d occurred:\n%s' % (e.resp.status, e.content))
    





import argparse

def my_custom_uploader(file_path, title, description, category, keywords, privacy_status, access_token, refresh_token ):
    
    # 1) get an authenticated service
    youtube = get_authenticated_service(        
        access_token=access_token,
        refresh_token=refresh_token
    )

    # 2) build an argparse.Namespace just like argparse would
    options = argparse.Namespace(
        file=file_path,
        title=title,
        description=description,
        category=category,
        keywords=keywords,
        privacyStatus=privacy_status,
    )

    # 3) call the existing function
    initialize_upload(youtube, options)


# example call
# if __name__ == "__main__":
#     my_custom_uploader(
#         file_path="../data/generated_video/out.mp4",
#         title="Test Video",
#         description="Test automated upload",
#         category="23",
#         keywords="meme,funny,dank,geeks,",
#         privacy_status="private"
#     )
