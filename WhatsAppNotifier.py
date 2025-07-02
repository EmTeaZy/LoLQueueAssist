from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

def send_notification(to_number, message, twilio_sid, twilio_token, from_number):
    """
    Sends a WhatsApp message using the Twilio API.

    Args:
        to_number (str): The recipient's WhatsApp phone number.
        message (str): The message to be sent.
        twilio_sid (str): The Twilio Account SID.
        twilio_token (str): The Twilio Auth Token.
        from_number (str): The Twilio phone number.
        
    Returns:
        bool: True if the message was sent successfully, False otherwise.
    """
    try:
        client = Client(twilio_sid, twilio_token)
        message = client.messages.create(
            body=message,
            from_=f'whatsapp:{from_number}',
            to=f'whatsapp:{to_number}'
        )
        if message.sid:
            print(f"WhatsApp notification sent to {to_number}")
            return True
        else:
            print(f"Failed to send WhatsApp notification: {message.error_message}")
            return False
    except TwilioRestException as e:
        print(f"Failed to send WhatsApp notification: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False