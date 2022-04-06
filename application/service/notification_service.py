from utils.sns import SnsService
from utils.sqs import SqsService


class NotificationService:

    def __init__(self):
        pass

    @staticmethod
    def publish_message(topic, message):
        SnsService.publish_message(topic=topic, message=message)

    @staticmethod
    def send_message_to_queue(queue, message, message_group_id):
        SqsService.send_message_to_queue(queue=queue, message=message, message_group_id=message_group_id)
