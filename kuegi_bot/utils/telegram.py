import requests

class TelegramBot:
	def __init__(self,logger,settings):
		self.token= settings.token
		self.chatId= settings.chatId
		self.logger= logger

	def send(self,bot_message):
		if self.token is None or self.chatId is None:
			self.logger.warn("missing telegram token or chatId")
			return

		url = 'https://api.telegram.org/bot' + self.token + '/sendMessage?chat_id=' + self.chatId + '&text=' + bot_message

		result= requests.get(url).json()
		if not result["ok"]:
			self.logger.warning("error sending telegram messages "+str(result))