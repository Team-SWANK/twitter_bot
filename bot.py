import logging, os, io, base64, requests
import urllib.request
import tweepy
import numpy as np
from PIL import Image
from config import create_api
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

segment_url = os.getenv("SEGMENT_URL")
censor_url = os.getenv("CENSOR_URL")


class MentionsListener(tweepy.StreamListener):
    def __init__(self, api):
        self.api = api
        self.me = api.me()

    def on_status(self, tweet):
        logger.info(f"Processing tweet id {tweet.id}")
        is_reply = tweet.in_reply_to_status_id

        # Check if tweet is a reply to another tweet containing media
        if is_reply is not None and self.api.get_status(is_reply).entities is not None:
            target_tweet = self.api.get_status(is_reply)
            i = 1
            file_names = []
            for media in target_tweet.extended_entities['media']:
                media_url = media['media_url']

                # Call Segmentation API for each image
                with urllib.request.urlopen(media_url) as url:
                    with open('temp.jpg', 'wb') as f:
                        f.write(url.read())
                files = {'image': open('temp.jpg', 'rb')}
                res = requests.post(segment_url, files=files).json()

                # Convert each segmentation to image file & call censoring API
                mask_to_image(res["predictions"]).save('mask.jpg')
                files = {'image': open('temp.jpg', 'rb'), 'mask': open('mask.jpg', 'rb')}
                res = requests.post(censor_url, files=files)

                # Convert base64 response to image file
                if res.status_code == 200:
                    fn = "censored" + str(i) + ".jpg"
                    img_bytes = res.json()["ImageBytes"].encode()
                    with open(fn, "wb") as f:
                        f.write(base64.decodebytes(img_bytes))
                    i += 1
                    file_names.append(fn)

            # Upload images to Twitter and get their media ids
            media_ids = []
            for fn in file_names:
                res = self.api.media_upload(fn)
                media_ids.append(res.media_id)

            # Tweet the results
            try:
                self.api.update_status(
                    status="Successfully censored " + str(len(media_ids)) + " photos to protect anonymity.",
                    in_reply_to_status_id=tweet.id,
                    auto_populate_reply_metadata=True,
                    media_ids=media_ids
                )
                logger.info("Success")
            except Exception as e:
                logger.error("Error on reply", exc_info=True)

    def on_error(self, status):
        logger.error(status)


def mask_to_image(pixels):
    arr = np.zeros([len(pixels), len(pixels[0]), 3], dtype=np.uint8)
    for i in range(len(pixels)):
        for j in range(len(pixels[0])):
            if pixels[i][j] == 0:
                arr[i, j] = [0, 0, 0]
            else:
                arr[i, j] = [255, 255, 255]
    return Image.fromarray(arr)


def main(keywords):
    api = create_api()
    mentions_listener = MentionsListener(api)
    stream = tweepy.Stream(
        auth=api.auth,
        listener=mentions_listener
    )
    stream.filter(track=keywords)


if __name__ == "__main__":
    main(['@photosense_bot'])
