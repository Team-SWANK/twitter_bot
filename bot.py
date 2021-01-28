import logging
import tweepy
from config import create_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

class MentionsListener(tweepy.StreamListener):
    def __init__(self, api):
        self.api = api
        self.me = api.me()

    def on_status(self, tweet):
        logger.info(f"Processing tweet id {tweet.id}")
        if tweet.in_reply_to_status_id is not None:
            try:
                self.api.update_status(
                    status="Hi",
                    in_reply_to_status_id=tweet.id,
                    auto_populate_reply_metadata=True
                )
                logger.info("Success")
            except Exception as e:
                logger.error("Error on reply", exc_info=True)

    def on_error(self, status):
        logger.error(status)

def main(keywords):
    api = create_api()
    mentions_listener = MentionsListener(api)
    stream = tweepy.Stream(
        auth = api.auth,
        listener = mentions_listener
    )
    stream.filter(track=keywords, languages=["en"])

if __name__ == "__main__":
    main(["@photosense_bot"])
